"""Batch MediaPipe Holistic landmark extraction for SignBridge-TR (Jira SB-50).

Runs legacy MediaPipe Holistic over every selected video and writes one ``.npz``
per video with the SB-15 per-frame layout (``[T, 1662]``), a per-group presence
mask and JSON metadata. A per-video report CSV and a JSON run summary are also
written. Missing groups are zero-filled and flagged 0 in the mask; no
interpolation is done here (the MEDIAPIPE_EVAL.md Section 6 gap rule belongs to
the later preprocessing step).

The pure helpers (selection, label CSV, flatten/mask, meta, report, summary,
npz I/O) need only numpy. mediapipe and OpenCV are imported inside
``process_video`` so tests can run without them.

Usage:
    python ml/eval/extract_landmarks.py --videos DIR [DIR ...] --out OUT_DIR \
        [--glob "*.mp4"] [--labels ground_truth.csv] [--split val] \
        [--limit N] [--report OUT_DIR/report.csv]

Dataset videos, labels and the output files must stay outside the repository
(SB-16, SB-46, SB-47). The script refuses to write inside the repository unless
the target path is gitignored.
"""

import argparse
import csv
import datetime as dt
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from landmark_layout import GROUPS, flatten_frame, group_array

LAYOUT_NAME = "legacy_holistic_543"
VECTOR_SIZE = sum(count * len(fields) for _, _, count, fields in GROUPS)  # 1662
GROUP_NAMES = [g[0] for g in GROUPS]
HOLISTIC_SETTINGS = {
    "static_image_mode": False,
    "model_complexity": 1,
    "smooth_landmarks": True,
    "refine_face_landmarks": False,
}
SPLITS = ("train", "val", "dev")
VIDEO_SUFFIXES = ("_color", "_depth")  # AUTSL: signerX_sampleY_color.mp4

REPORT_COLUMNS = (
    ["video", "sample_id", "class_id", "status", "error", "frames",
     "duration_s", "processing_s", "processing_fps"]
    + [f"missing_pct_{name}" for name in GROUP_NAMES]
)


# --------------------------------------------------------------------------
# Pure helpers (no mediapipe / OpenCV)
# --------------------------------------------------------------------------

def select_videos(video_dirs, pattern="*.mp4", limit=None):
    """Return (selected paths, selection rule text).

    Deterministic: non-recursive glob in each directory, sort by file name
    (Python code-point order, full path as tie-breaker), keep the first N.
    """
    found = []
    for d in video_dirs:
        found.extend(p for p in Path(d).glob(pattern) if p.is_file())
    found.sort(key=lambda p: (p.name, str(p)))
    selected = found if limit is None else found[:limit]
    rule = (
        f"non-recursive glob '{pattern}' in {len(video_dirs)} --videos folder(s); "
        f"sorted by file name (Python code-point order, full path as tie-breaker); "
        + (f"first {limit} of {len(found)} matching files" if limit is not None
           else f"all {len(found)} matching files")
    )
    return selected, rule


def sample_id_from_filename(name):
    """'signer0_sample1_color.mp4' -> 'signer0_sample1'; other names -> stem."""
    stem = Path(name).stem
    for suffix in VIDEO_SUFFIXES:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def read_labels(path):
    """Read a headerless ``sample_id,class_id`` CSV into {sample_id: int class_id}."""
    labels = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for lineno, row in enumerate(csv.reader(fh), start=1):
            if not row or all(not c.strip() for c in row):
                continue
            if len(row) != 2:
                raise ValueError(f"{path}:{lineno}: expected 2 columns, got {len(row)}")
            sample_id, class_id = row[0].strip(), row[1].strip()
            try:
                class_value = int(class_id)
            except ValueError:
                raise ValueError(
                    f"{path}:{lineno}: class_id {class_id!r} is not an integer "
                    "(the file must be headerless)") from None
            if sample_id in labels:
                raise ValueError(f"{path}:{lineno}: duplicate sample_id {sample_id!r}")
            labels[sample_id] = class_value
    return labels


def label_for_video(video_name, labels):
    """Return (sample_id, class_id or None) for a video file name."""
    sample_id = sample_id_from_filename(video_name)
    return sample_id, (labels or {}).get(sample_id)


def presence_mask(arrays):
    """uint8 [4] in GROUPS order: 1 if the group was detected in the frame."""
    return np.array([arrays[name] is not None for name in GROUP_NAMES], dtype=np.uint8)


def stack_frames(frames):
    """List of per-frame group dicts -> (keypoints float32 [T,1662], mask uint8 [T,4])."""
    if not frames:
        return (np.zeros((0, VECTOR_SIZE), dtype=np.float32),
                np.zeros((0, len(GROUPS)), dtype=np.uint8))
    keypoints = np.stack([flatten_frame(f) for f in frames]).astype(np.float32)
    mask = np.stack([presence_mask(f) for f in frames]).astype(np.uint8)
    return keypoints, mask


def layout_description():
    return {
        name: {"landmarks": count, "fields": list(fields), "values": count * len(fields)}
        for name, _, count, fields in GROUPS
    }


def build_meta(*, video, sample_id, class_id, split, source_fps, frame_count,
               frame_count_reported, width, height, versions, created_at=None):
    """Metadata stored as a JSON string in each .npz."""
    return {
        "video": video,
        "sample_id": sample_id,
        "class_id": class_id,
        "split": split,
        "source_fps": source_fps,
        "frame_count": frame_count,
        "frame_count_reported": frame_count_reported,
        "width": width,
        "height": height,
        "layout_name": LAYOUT_NAME,
        "concat_order": GROUP_NAMES,
        "vector_size": VECTOR_SIZE,
        "groups": layout_description(),
        "mask_order": GROUP_NAMES,
        "missing_fill": "zeros, mask=0; no interpolation (preprocessing applies MEDIAPIPE_EVAL.md Section 6)",
        "holistic_settings": dict(HOLISTIC_SETTINGS),
        "versions": dict(versions),
        "created_at": created_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }


def write_npz(path, keypoints, mask, meta):
    keypoints = np.asarray(keypoints, dtype=np.float32)
    mask = np.asarray(mask, dtype=np.uint8)
    if keypoints.ndim != 2 or keypoints.shape[1] != VECTOR_SIZE:
        raise ValueError(f"keypoints must be [T, {VECTOR_SIZE}], got {keypoints.shape}")
    if mask.shape != (keypoints.shape[0], len(GROUPS)):
        raise ValueError(f"mask must be [T, {len(GROUPS)}], got {mask.shape}")
    np.savez_compressed(path, keypoints=keypoints, mask=mask,
                        meta=np.array(json.dumps(meta, ensure_ascii=False)))


def read_npz(path):
    """Return (keypoints, mask, meta dict). No pickle needed."""
    with np.load(path, allow_pickle=False) as data:
        return data["keypoints"], data["mask"], json.loads(str(data["meta"]))


def missing_pct(mask):
    """Per-group % of frames with mask 0."""
    mask = np.asarray(mask)
    n = mask.shape[0]
    return {name: (100.0 * float((mask[:, i] == 0).sum()) / n if n else None)
            for i, name in enumerate(GROUP_NAMES)}


def _fmt(value, digits):
    return "" if value is None else round(value, digits)


def report_row(result):
    """One report CSV row (dict) from a per-video result dict."""
    row = {
        "video": result["video"],
        "sample_id": result.get("sample_id", ""),
        "class_id": "" if result.get("class_id") is None else result["class_id"],
        "status": result["status"],
        "error": result.get("error") or "",
        "frames": result.get("frames", ""),
        "duration_s": _fmt(result.get("duration_s"), 3),
        "processing_s": _fmt(result.get("processing_s"), 3),
        "processing_fps": _fmt(result.get("processing_fps"), 2),
    }
    miss = result.get("missing_pct") or {}
    for name in GROUP_NAMES:
        row[f"missing_pct_{name}"] = _fmt(miss.get(name), 1)
    return row


def write_report(path, results):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for r in results:
            writer.writerow(report_row(r))


def summarize(results, total_s, selection_rule):
    ok = [r for r in results if r["status"] == "ok"]
    fps = [r["processing_fps"] for r in ok if r.get("processing_fps")]
    return {
        "total_videos": len(results),
        "succeeded": len(ok),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "failed_videos": [r["video"] for r in results if r["status"] == "failed"],
        "unlabelled_videos": sum(1 for r in results if r.get("class_id") is None),
        "total_time_s": round(total_s, 3),
        "mean_processing_fps": round(statistics.mean(fps), 2) if fps else None,
        "median_processing_fps": round(statistics.median(fps), 2) if fps else None,
        "selection_rule": selection_rule,
    }


def format_summary(summary):
    lines = [
        f"Videos: {summary['total_videos']} total, {summary['succeeded']} ok, "
        f"{summary['failed']} failed",
        f"Total time: {summary['total_time_s']:.2f} s",
        f"Processing fps (successful videos): mean {summary['mean_processing_fps']}, "
        f"median {summary['median_processing_fps']}",
        f"Selection rule: {summary['selection_rule']}",
    ]
    if summary["failed_videos"]:
        lines.append("Failed: " + ", ".join(summary["failed_videos"]))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Repository guard
# --------------------------------------------------------------------------

def find_repo_root(path):
    """Closest ancestor of ``path`` that contains a .git entry, else None."""
    p = Path(path).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def is_gitignored(path, repo_root, is_dir):
    """Ask git (read-only ``git check-ignore``) whether ``path`` is ignored."""
    rel = Path(path).resolve().relative_to(repo_root).as_posix()
    if is_dir:
        rel += "/"
    try:
        res = subprocess.run(["git", "-C", str(repo_root), "check-ignore", "-q", rel],
                             capture_output=True, check=False)
    except FileNotFoundError:
        return False  # cannot verify -> treat as not ignored (conservative)
    return res.returncode == 0


def unsafe_output_paths(paths_and_kinds, ignored_check=is_gitignored):
    """Return the output paths that are inside a git repo and not gitignored."""
    unsafe = []
    for path, is_dir in paths_and_kinds:
        root = find_repo_root(path)
        if root is not None and not ignored_check(path, root, is_dir):
            unsafe.append(str(path))
    return unsafe


# --------------------------------------------------------------------------
# MediaPipe processing
# --------------------------------------------------------------------------

def library_versions():
    import cv2
    import mediapipe as mp
    return {"python": platform.python_version(), "mediapipe": mp.__version__,
            "opencv": cv2.__version__, "numpy": np.__version__}


def process_video(video_path, out_dir, sample_id, class_id, split, versions):
    """Extract one video. Never raises: failures come back as status 'failed'."""
    result = {"video": Path(video_path).name, "sample_id": sample_id,
              "class_id": class_id, "status": "failed", "error": None}
    try:
        import cv2
        import mediapipe as mp

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            result["error"] = "could not open video"
            return result
        source_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count_reported = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frames = []
        # A fresh Holistic per video so tracking/smoothing state never leaks
        # between samples.
        with mp.solutions.holistic.Holistic(**HOLISTIC_SETTINGS) as holistic:
            start = time.perf_counter()  # decode + inference only, as in SB-15
            while True:
                ok, frame_bgr = cap.read()
                if not ok:
                    break
                res = holistic.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                frames.append({name: group_array(getattr(res, attr), count, fields)
                               for name, attr, count, fields in GROUPS})
            elapsed = time.perf_counter() - start
        cap.release()

        n = len(frames)
        if n == 0:
            result["error"] = "no frames decoded"
            return result

        keypoints, mask = stack_frames(frames)
        meta = build_meta(video=result["video"], sample_id=sample_id, class_id=class_id,
                          split=split, source_fps=source_fps, frame_count=n,
                          frame_count_reported=frame_count_reported,
                          width=width, height=height, versions=versions)
        write_npz(Path(out_dir) / f"{Path(video_path).stem}.npz", keypoints, mask, meta)

        result.update(status="ok", frames=n,
                      duration_s=(n / source_fps) if source_fps else None,
                      processing_s=elapsed,
                      processing_fps=(n / elapsed) if elapsed > 0 else None,
                      missing_pct=missing_pct(mask))
    except Exception as exc:  # keep the batch going
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    return result


def run(args):
    out_dir = Path(args.out)
    report_path = Path(args.report) if args.report else out_dir / "report.csv"
    summary_path = out_dir / "run_summary.json"

    unsafe = unsafe_output_paths([(out_dir, True), (report_path, False)])
    if unsafe:
        print("WARNING: these output paths are inside the git repository and not "
              "gitignored; refusing to write dataset-derived files there:", file=sys.stderr)
        for p in unsafe:
            print(f"  {p}", file=sys.stderr)
        print("Use a folder outside the repository (or a gitignored one such as "
              "landmarks_out/ or data/local/).", file=sys.stderr)
        return 2

    labels = read_labels(args.labels) if args.labels else None
    videos, rule = select_videos(args.videos, args.glob, args.limit)
    if not videos:
        print(f"No videos matched '{args.glob}' in {args.videos}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    versions = library_versions()

    results = []
    t0 = time.perf_counter()
    for i, video in enumerate(videos, start=1):
        sample_id, class_id = label_for_video(video.name, labels)
        r = process_video(video, out_dir, sample_id, class_id, args.split, versions)
        results.append(r)
        detail = (f"{r['frames']} frames, {r['processing_s']:.2f}s, "
                  f"{r['processing_fps']:.1f} fps") if r["status"] == "ok" else r["error"]
        print(f"[{i}/{len(videos)}] {video.name}: {r['status']} ({detail})")
    total_s = time.perf_counter() - t0

    write_report(report_path, results)
    summary = summarize(results, total_s, rule)
    summary.update({
        "command": " ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        "glob": args.glob, "limit": args.limit, "split": args.split,
        "labels_used": bool(args.labels), "layout_name": LAYOUT_NAME,
        "holistic_settings": HOLISTIC_SETTINGS, "versions": versions,
        "report": str(report_path),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    })
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    print("\n" + format_summary(summary))
    print(f"Report: {report_path}\nSummary: {summary_path}")
    return 0


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Batch MediaPipe Holistic landmark extraction (SB-50)")
    ap.add_argument("--videos", required=True, nargs="+",
                    help="video folder(s); searched non-recursively")
    ap.add_argument("--glob", default="*.mp4",
                    help="file pattern (default *.mp4; AUTSL color videos: *_color.mp4)")
    ap.add_argument("--labels", help="headerless sample_id,class_id CSV (optional)")
    ap.add_argument("--split", choices=SPLITS, help="split tag written to metadata (optional)")
    ap.add_argument("--out", required=True, help="output folder for .npz files and the run summary")
    ap.add_argument("--limit", type=int, help="process only the first N videos after sorting")
    ap.add_argument("--report", help="report CSV path (default: <out>/report.csv)")
    args = ap.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        ap.error("--limit must be >= 1")
    return args


if __name__ == "__main__":
    sys.exit(run(parse_args()))
