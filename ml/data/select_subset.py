#!/usr/bin/env python3
"""SB-49 video quality filter and subset selection for the AUTSL dataset.

What the script does
--------------------
1. Reads the AUTSL class list (ClassId,TR,EN) and, per split, a label file
   (headerless ``sample_id,class_id``) and the extracted video directory. All
   locations and selection parameters are command-line arguments; no
   machine-specific path is stored in the code (AC-1).
2. Restricts the work to the chosen classes (``--classes``: class IDs, or CSV
   files with an ``autsl_class_id`` column such as the SB-48 evidence files).
   Without ``--classes`` every class is used.
3. Measures simple per-video quality values on the colour (RGB) video of every
   labelled sample of the chosen classes (AC-2; see QUALITY MEASURES below).
   Frames are decoded with OpenCV. Depth videos are only checked for presence
   and non-zero size.
4. Applies the exclusion thresholds, ranks the remaining videos inside each
   class and selects up to ``--samples-per-class`` per class and split,
   taking signers in turn so that one signer does not dominate a class.
   Splits named in ``--no-quality-selection`` (default: test) are not reduced
   by quality: every decodable sample of a chosen class is kept, so that the
   test set is not shaped by the quality measures.
5. Writes into ``--out`` (AC-3, AC-4):
   - quality.csv    one row per measured video with all measures;
   - manifest.csv   one row per measured sample: included yes/no and the reason;
   - summary.csv    counts before and after selection, per split;
   - class-summary.csv  counts before and after selection, per class ID and split
                    (class IDs only; no TR/EN names from the private class list);
   - quality-distribution.csv  percentiles of each measure, per split;
   - run.json       parameters, input file SHA-256, tool versions, timings.
   quality.csv and manifest.csv list sample IDs and must stay outside the
   repository. The other files contain aggregates only: no sample IDs and no
   class names, so publishing them never reproduces the ClassId/TR/EN mapping
   (SB-46 handling rule; AC-5).

QUALITY MEASURES (computed on greyscale frames)
-----------------------------------------------
  decoded_frames   frames OpenCV could decode. 0 means the file is unreadable.
  reported_frames, fps, width, height   container metadata reported by OpenCV.
  duration_s       decoded_frames / fps.
  brightness       mean grey level (0-255) over frames. Detects very dark or
                   washed-out recordings; says nothing about lighting on the hands.
  contrast         mean per-frame standard deviation of grey levels. Low values
                   mean a flat image (fog, overexposure, lens covered).
  sharpness        mean variance of the Laplacian. A common blur proxy; it also
                   rises with background texture, so it is only compared between
                   videos of the same class, not used as an absolute score.
  motion           mean absolute difference between consecutive frames. A sign
                   needs movement; near-zero motion suggests a frozen or empty clip.
                   Background movement also counts as motion.
  frozen_ratio     share of consecutive frame pairs whose difference is below
                   ``--frozen-diff``. Detects stuck or duplicated frames.
None of these values checks that the right sign is performed, that the hands are
visible, or that MediaPipe can track the signer. They are cheap screening values.

Ranking: inside a class and split, each passing video gets the mean of its
percentile ranks for sharpness, contrast and motion (higher is better).

Usage
-----
  python ml/data/select_subset.py --signlist <SignList_ClassId_TR_EN.csv> \\
      --split train <train_video_dir> <train_labels.csv> \\
      --split validation <val_video_dir> <validation/ground_truth.csv> \\
      --split test <test_video_dir> <test/ground_truth.csv> \\
      --classes docs/datasets/SB-48/coverage-glosses.csv \\
      --samples-per-class 40 --out <output-dir> [--workers 4]
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import os
import platform
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor

SAMPLE_RE = re.compile(r"^(signer\d+)_sample\d+$")
MEASURES = ["brightness", "contrast", "sharpness", "motion", "frozen_ratio", "duration_s"]
RANKED = ["sharpness", "contrast", "motion"]
QUALITY_FIELDS = ["split", "sample_id", "class_id", "signer", "color_file", "color_bytes", "depth_bytes",
                  "decoded_frames", "reported_frames", "fps", "width", "height", "duration_s",
                  "brightness", "contrast", "sharpness", "motion", "frozen_ratio", "error"]


# ----------------------------------------------------------------------------- inputs
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_classes(path, errors):
    classes = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows or [c.strip() for c in rows[0][:3]] != ["ClassId", "TR", "EN"]:
        errors.append(f"{path}: header must be ClassId,TR,EN")
        return classes
    for n, row in enumerate(rows[1:], start=2):
        if len(row) < 3 or not row[0].strip().isdigit():
            errors.append(f"{path}:{n}: expected integer ClassId,TR,EN")
            continue
        cid = int(row[0])
        if cid in classes:
            errors.append(f"{path}:{n}: duplicate ClassId {cid}")
        classes[cid] = (row[1].strip(), row[2].strip())
    return classes


def load_labels(split, path, classes, errors):
    labels = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for n, row in enumerate(csv.reader(f), start=1):
            if not row:
                continue
            if len(row) != 2 or not row[1].strip().isdigit():
                errors.append(f"{split} {path}:{n}: expected sample_id,class_id")
                continue
            sid, cid = row[0].strip(), int(row[1])
            m = SAMPLE_RE.match(sid)
            if not m:
                errors.append(f"{split} {path}:{n}: sample ID '{sid}' is not signerX_sampleY")
                continue
            if cid not in classes:
                errors.append(f"{split} {path}:{n}: unknown class ID {cid}")
                continue
            labels.append((sid, cid, m.group(1)))
    seen = collections.Counter(s for s, _, _ in labels)
    dup = sorted(s for s, c in seen.items() if c > 1)
    if dup:
        errors.append(f"{split}: {len(dup)} duplicate sample IDs, e.g. {dup[0]}")
    return labels


def parse_classes(values, classes, errors):
    """--classes items: integer IDs (comma-separated allowed) or CSV files with autsl_class_id."""
    chosen = set()
    for value in values:
        if os.path.isfile(value):
            with open(value, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if "autsl_class_id" not in (reader.fieldnames or []):
                    errors.append(f"{value}: no autsl_class_id column")
                    continue
                for row in reader:
                    v = (row["autsl_class_id"] or "").strip()
                    if v:  # empty for glosses without a class (e.g. SB-48 'not found')
                        chosen.add(int(v))
        else:
            for part in value.split(","):
                part = part.strip()
                if part:
                    if not part.isdigit():
                        errors.append(f"--classes: '{part}' is neither a file nor a class ID")
                        continue
                    chosen.add(int(part))
    unknown = sorted(c for c in chosen if c not in classes)
    if unknown:
        errors.append(f"--classes: unknown class IDs {unknown}")
    return chosen


# ----------------------------------------------------------------------------- measuring
def measure(job):
    """Measure one sample. job = (split, sample_id, class_id, signer, video_dir, args dict)."""
    split, sid, cid, signer, vdir, opt = job
    color = os.path.join(vdir, f"{sid}_color.mp4")
    depth = os.path.join(vdir, f"{sid}_depth.mp4")
    row = dict.fromkeys(QUALITY_FIELDS, "")
    row.update(split=split, sample_id=sid, class_id=cid, signer=signer, color_file=os.path.basename(color))
    row["color_bytes"] = os.path.getsize(color) if os.path.isfile(color) else 0
    row["depth_bytes"] = os.path.getsize(depth) if os.path.isfile(depth) else 0
    if not row["color_bytes"]:
        row.update(decoded_frames=0, error="colour video missing or empty")
        return row
    try:
        import cv2
        import numpy as np
        cap = cv2.VideoCapture(color)
        row["reported_frames"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        row["fps"] = round(fps, 3)
        row["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        row["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        bright, contrast, sharp, diffs = [], [], [], []
        prev, decoded = None, 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            decoded += 1
            if (decoded - 1) % opt["frame_stride"]:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            bright.append(float(gray.mean()))
            contrast.append(float(gray.std()))
            sharp.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            if prev is not None:
                diffs.append(float(cv2.absdiff(gray, prev).mean()))
            prev = gray
        cap.release()
        row["decoded_frames"] = decoded
        if not decoded:
            row["error"] = "no frame could be decoded"
            return row
        row["duration_s"] = round(decoded / fps, 3) if fps > 0 else ""
        row["brightness"] = round(float(np.mean(bright)), 3)
        row["contrast"] = round(float(np.mean(contrast)), 3)
        row["sharpness"] = round(float(np.mean(sharp)), 3)
        row["motion"] = round(float(np.mean(diffs)), 4) if diffs else 0.0
        row["frozen_ratio"] = round(sum(d < opt["frozen_diff"] for d in diffs) / len(diffs), 4) if diffs else 1.0
    except Exception as exc:  # a broken file must not stop the whole run
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


# ----------------------------------------------------------------------------- selection
def exclusion_reasons(row, a):
    """Return the list of failed thresholds for one measured row (empty = passes)."""
    if not row["color_bytes"]:
        return ["missing colour video (file absent or empty)"]
    if row["error"] or not row["decoded_frames"]:
        return [f"unreadable ({row['error'] or 'no frames'})"]
    out = []
    if not row["depth_bytes"]:
        out.append("depth video missing or empty")
    if row["decoded_frames"] < a.min_frames:
        out.append(f"decoded_frames {row['decoded_frames']} < {a.min_frames}")
    if row["brightness"] < a.min_brightness:
        out.append(f"brightness {row['brightness']} < {a.min_brightness}")
    if row["brightness"] > a.max_brightness:
        out.append(f"brightness {row['brightness']} > {a.max_brightness}")
    if row["contrast"] < a.min_contrast:
        out.append(f"contrast {row['contrast']} < {a.min_contrast}")
    if row["sharpness"] < a.min_sharpness:
        out.append(f"sharpness {row['sharpness']} < {a.min_sharpness}")
    if row["motion"] < a.min_motion:
        out.append(f"motion {row['motion']} < {a.min_motion}")
    if row["frozen_ratio"] > a.max_frozen_ratio:
        out.append(f"frozen_ratio {row['frozen_ratio']} > {a.max_frozen_ratio}")
    return out


def percentile_ranks(values):
    """Rank in [0, 1]; ties share the mean rank. A single value gets 1.0."""
    if len(values) == 1:
        return [1.0]
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2 / (len(values) - 1)
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def select(rows, a):
    """Return manifest rows (one per measured row) with included/reason/score/rank."""
    manifest = []
    groups = collections.defaultdict(list)
    for row in rows:
        groups[(row["split"], row["class_id"])].append(row)
    for (split, cid), members in sorted(groups.items()):
        passing, failing = [], []
        for row in members:
            reasons = exclusion_reasons(row, a)
            if split in a.no_quality_selection:
                # keep every decodable sample; only unreadable files are dropped
                reasons = [r for r in reasons if r.startswith(("unreadable", "missing colour"))]
            (failing if reasons else passing).append((row, reasons))
        scores = {}
        if passing:
            per_measure = [percentile_ranks([r[m] for r, _ in passing]) for m in RANKED]
            for idx, (row, _) in enumerate(passing):
                scores[row["sample_id"]] = round(sum(p[idx] for p in per_measure) / len(RANKED), 4)
        chosen = {}
        if split in a.no_quality_selection:
            for row, _ in passing:
                chosen[row["sample_id"]] = None
        else:
            by_signer = collections.defaultdict(list)
            for row, _ in passing:
                by_signer[row["signer"]].append(row)
            for lst in by_signer.values():
                lst.sort(key=lambda r: (-scores[r["sample_id"]], r["sample_id"]))
            # signers in turn; within a turn, the signer whose next video scores best goes first
            rank = 0
            while len(chosen) < a.samples_per_class and any(by_signer.values()):
                turn = sorted((lst[0] for lst in by_signer.values() if lst),
                              key=lambda r: (-scores[r["sample_id"]], r["sample_id"]))
                for row in turn:
                    if len(chosen) >= a.samples_per_class:
                        break
                    rank += 1
                    chosen[row["sample_id"]] = rank
                    by_signer[row["signer"]].pop(0)
        n_signers = len({r["signer"] for r, _ in passing})
        for row, reasons in passing + failing:
            sid = row["sample_id"]
            if sid in chosen:
                if split in a.no_quality_selection:
                    reason = f"{split}: class chosen; split kept whole (no quality-based selection)"
                else:
                    reason = (f"passes all thresholds; selection rank {chosen[sid]} of "
                              f"{min(a.samples_per_class, len(passing))} in class, signer round-robin "
                              f"over {n_signers} signers")
                included = "yes"
            elif reasons:
                included, reason = "no", "excluded: " + "; ".join(reasons)
            else:
                included, reason = "no", f"passes thresholds; not needed (limit {a.samples_per_class} per class reached)"
            manifest.append({"split": split, "sample_id": sid, "class_id": cid, "signer": row["signer"],
                             "included": included, "selection_rank": chosen.get(sid) or "",
                             "quality_score": scores.get(sid, ""), "reason": reason})
    return manifest


# ----------------------------------------------------------------------------- outputs
def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def pct(values, q):
    v = sorted(values)
    if not v:
        return ""
    k = (len(v) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 3)


def build_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--signlist", required=True, help="SignList_ClassId_TR_EN.csv")
    ap.add_argument("--split", nargs=3, action="append", required=True, metavar=("NAME", "VIDEO_DIR", "LABELS"),
                    help="split name, extracted video directory and label CSV; repeat per split")
    ap.add_argument("--classes", nargs="*", default=[],
                    help="class IDs (comma-separated) and/or CSV files with an autsl_class_id column; default all")
    ap.add_argument("--samples-per-class", type=int, default=40, help="maximum selected videos per class and split")
    ap.add_argument("--no-quality-selection", nargs="*", default=["test"],
                    help="splits kept whole for the chosen classes (default: test)")
    ap.add_argument("--min-frames", type=int, default=16)
    ap.add_argument("--min-brightness", type=float, default=30.0)
    ap.add_argument("--max-brightness", type=float, default=225.0)
    ap.add_argument("--min-contrast", type=float, default=15.0)
    ap.add_argument("--min-sharpness", type=float, default=0.0, help="absolute Laplacian-variance floor (0 = off)")
    ap.add_argument("--min-motion", type=float, default=0.5)
    ap.add_argument("--max-frozen-ratio", type=float, default=0.5)
    ap.add_argument("--frozen-diff", type=float, default=0.25,
                    help="mean absolute grey difference below which a frame pair counts as frozen")
    ap.add_argument("--frame-stride", type=int, default=1, help="measure every n-th decoded frame")
    ap.add_argument("--limit", type=int, default=0, help="measure at most n samples per split (dry run)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.samples_per_class < 1 or a.frame_stride < 1 or a.workers < 1:
        ap.error("--samples-per-class, --frame-stride and --workers must be >= 1")
    return a


def main(argv=None):
    a = build_args(argv)
    errors = []
    for _, vdir, lab in a.split:
        if not os.path.isdir(vdir):
            errors.append(f"video directory not found: {vdir}")
        if not os.path.isfile(lab):
            errors.append(f"label file not found: {lab}")
    if not os.path.isfile(a.signlist):
        errors.append(f"class list not found: {a.signlist}")
    names = [s[0] for s in a.split]
    if len(set(names)) != len(names):
        errors.append("split names must be unique")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 2
    classes = load_classes(a.signlist, errors)
    labels = {name: load_labels(name, lab, classes, errors) for name, _, lab in a.split}
    all_ids = collections.Counter(s for rows in labels.values() for s, _, _ in rows)
    if any(c > 1 for c in all_ids.values()):
        errors.append("a sample ID appears in more than one split")
    chosen = parse_classes(a.classes, classes, errors) if a.classes else set(classes)
    if not chosen:
        errors.append("no class selected")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 2

    os.makedirs(a.out, exist_ok=True)
    opt = {"frame_stride": a.frame_stride, "frozen_diff": a.frozen_diff}
    jobs = []
    for name, vdir, _ in a.split:
        rows = [r for r in labels[name] if r[1] in chosen]
        if a.limit:
            rows = rows[:a.limit]
        jobs += [(name, sid, cid, signer, vdir, opt) for sid, cid, signer in rows]
    started = time.time()
    print(f"measuring {len(jobs)} colour videos in {len(chosen)} classes with {a.workers} workers", file=sys.stderr)
    measured = []
    if a.workers == 1:
        it = map(measure, jobs)
    else:
        pool = ProcessPoolExecutor(max_workers=a.workers)
        it = pool.map(measure, jobs, chunksize=8)
    for i, row in enumerate(it, start=1):
        measured.append(row)
        if i % 500 == 0 or i == len(jobs):
            print(f"  {i}/{len(jobs)} ({time.time() - started:.0f} s)", file=sys.stderr)
    if a.workers != 1:
        pool.shutdown()
    elapsed = time.time() - started

    manifest = select(measured, a)
    write_csv(os.path.join(a.out, "quality.csv"), QUALITY_FIELDS, measured)
    write_csv(os.path.join(a.out, "manifest.csv"),
              ["split", "sample_id", "class_id", "signer", "included", "selection_rank", "quality_score", "reason"],
              manifest)

    # aggregates (safe to publish: no sample IDs)
    summary, class_rows, dist = [], [], []
    for name, _, _ in a.split:
        m = [r for r in manifest if r["split"] == name]
        q = [r for r in measured if r["split"] == name]
        excl = collections.Counter()
        for r in m:
            if r["reason"].startswith("excluded: "):
                for part in r["reason"][len("excluded: "):].split("; "):
                    excl[part.split(" ")[0]] += 1
        summary.append({
            "split": name,
            "labelled_samples_all_classes": len(labels[name]),
            "classes_all": len({c for _, c, _ in labels[name]}),
            "labelled_samples_chosen_classes": sum(1 for r in labels[name] if r[1] in chosen),
            "classes_chosen": len({c for _, c, _ in labels[name] if c in chosen}),
            "measured": len(q),
            "missing_colour": sum(1 for r in q if not r["color_bytes"]),
            "unreadable": sum(1 for r in q if r["color_bytes"] and (r["error"] or not r["decoded_frames"])),
            "excluded_by_threshold": sum(1 for r in m if r["reason"].startswith("excluded: ")),
            "passing_not_selected": sum(1 for r in m if r["reason"].startswith("passes thresholds; not needed")),
            "selected": sum(1 for r in m if r["included"] == "yes"),
            "selected_signers": len({r["signer"] for r in m if r["included"] == "yes"}),
            "quality_selection": "no" if name in a.no_quality_selection else "yes",
            "exclusions_by_measure": "; ".join(f"{k}={v}" for k, v in sorted(excl.items())),
        })
        for cid in sorted({r["class_id"] for r in m}):
            cm = [r for r in m if r["class_id"] == cid]
            # Class IDs and counts only: TR/EN names come from the private class list and are not exported
            class_rows.append({"split": name, "class_id": cid,
                               "before": len(cm),
                               "excluded": sum(1 for r in cm if r["reason"].startswith("excluded: ")),
                               "selected": sum(1 for r in cm if r["included"] == "yes"),
                               "signers_before": len({r["signer"] for r in cm}),
                               "signers_selected": len({r["signer"] for r in cm if r["included"] == "yes"})})
        ok = [r for r in q if not r["error"] and r["decoded_frames"]]
        for meas in ["decoded_frames", "fps", "width", "height"] + MEASURES:
            vals = [float(r[meas]) for r in ok if r[meas] != ""]
            dist.append({"split": name, "measure": meas, "n": len(vals), "min": pct(vals, 0), "p05": pct(vals, .05),
                         "p25": pct(vals, .25), "median": pct(vals, .5), "p75": pct(vals, .75),
                         "p95": pct(vals, .95), "max": pct(vals, 1)})
    write_csv(os.path.join(a.out, "summary.csv"), list(summary[0]), summary)
    write_csv(os.path.join(a.out, "class-summary.csv"),
              ["split", "class_id", "before", "excluded", "selected", "signers_before", "signers_selected"],
              class_rows)
    write_csv(os.path.join(a.out, "quality-distribution.csv"),
              ["split", "measure", "n", "min", "p05", "p25", "median", "p75", "p95", "max"], dist)

    try:
        import cv2
        import numpy
        versions = {"opencv": cv2.__version__, "numpy": numpy.__version__}
    except ImportError:
        versions = {}
    params = {k: v for k, v in vars(a).items() if k not in ("split", "signlist", "out", "classes")}
    run = {
        "script": "ml/data/select_subset.py (SB-49)",
        "run_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "python": platform.python_version(), "platform": platform.platform(), **versions,
        "parameters": params,
        "classes_argument": [os.path.basename(c) for c in a.classes],
        "chosen_class_ids": sorted(chosen),
        "inputs_sha256": {"signlist": sha256(a.signlist),
                          **{f"{n}_labels": sha256(lab) for n, _, lab in a.split}},
        "outputs_sha256": {f: sha256(os.path.join(a.out, f)) for f in ("quality.csv", "manifest.csv")},
        "measure_seconds": round(elapsed, 1),
    }
    with open(os.path.join(a.out, "run.json"), "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2, ensure_ascii=False)
        f.write("\n")
    for s in summary:
        print(f"{s['split']}: {s['labelled_samples_chosen_classes']} labelled in chosen classes -> "
              f"{s['selected']} selected ({s['excluded_by_threshold']} excluded, of which {s['missing_colour']} missing "
              f"and {s['unreadable']} unreadable)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
