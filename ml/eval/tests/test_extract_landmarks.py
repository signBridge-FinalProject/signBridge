"""SB-50 checks using fabricated arrays and CSVs only.

No real video, no mediapipe/OpenCV and no AUTSL labels or mapping are used.
Run from the repository root:  python -m pytest ml/eval/tests -v
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import extract_landmarks as el  # noqa: E402
from landmark_layout import GROUPS, flatten_frame  # noqa: E402


def fake_group(name, value):
    _, _, count, fields = next(g for g in GROUPS if g[0] == name)
    return np.full((count, len(fields)), value, dtype=np.float32)


def full_frame(value=0.5):
    return {name: fake_group(name, value) for name, *_ in GROUPS}


# --- flatten / mask -----------------------------------------------------

def test_pure_module_does_not_import_mediapipe_or_cv2():
    assert "mediapipe" not in sys.modules
    assert "cv2" not in sys.modules


def test_vector_size_is_1662():
    assert el.VECTOR_SIZE == 1662
    assert sum(g[2] for g in GROUPS) == 543


@pytest.mark.parametrize("missing", [[], ["left_hand"], ["face", "right_hand"],
                                     [g[0] for g in GROUPS]])
def test_flatten_always_1662_and_missing_group_zero_filled(missing):
    frame = full_frame(0.5)
    for name in missing:
        frame[name] = None
    vec = flatten_frame(frame)
    assert vec.shape == (1662,)
    assert vec.dtype == np.float32

    offset = 0
    for name, _, count, fields in GROUPS:
        block = vec[offset: offset + count * len(fields)]
        offset += count * len(fields)
        if name in missing:
            assert np.all(block == 0.0)
        else:
            assert np.all(block == 0.5)

    mask = el.presence_mask(frame)
    assert mask.dtype == np.uint8
    assert mask.tolist() == [0 if g[0] in missing else 1 for g in GROUPS]


def test_concat_order_offsets():
    frame = {name: fake_group(name, i + 1) for i, (name, *_) in enumerate(GROUPS)}
    vec = flatten_frame(frame)
    assert np.all(vec[:132] == 1)            # pose 33x4
    assert np.all(vec[132:1536] == 2)        # face 468x3
    assert np.all(vec[1536:1599] == 3)       # left_hand 21x3
    assert np.all(vec[1599:1662] == 4)       # right_hand 21x3


def test_stack_frames_shapes_and_missing_pct():
    frames = [full_frame(), full_frame(), full_frame(), full_frame()]
    frames[1]["left_hand"] = None
    frames[2]["left_hand"] = None
    frames[3]["right_hand"] = None
    kp, mask = el.stack_frames(frames)
    assert kp.shape == (4, 1662) and kp.dtype == np.float32
    assert mask.shape == (4, 4) and mask.dtype == np.uint8
    assert np.all(kp[1, 1536:1599] == 0)
    miss = el.missing_pct(mask)
    assert miss == {"pose": 0.0, "face": 0.0, "left_hand": 50.0, "right_hand": 25.0}


# --- labels --------------------------------------------------------------

def write_csv(tmp_path, text, name="labels.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_read_headerless_labels(tmp_path):
    p = write_csv(tmp_path, "signer900_sample1,7\nsigner900_sample2,0\n\nsigner901_sample3,225\n")
    assert el.read_labels(p) == {"signer900_sample1": 7, "signer900_sample2": 0,
                                 "signer901_sample3": 225}


def test_header_row_is_rejected(tmp_path):
    p = write_csv(tmp_path, "sample_id,class_id\nsigner900_sample1,7\n")
    with pytest.raises(ValueError, match="headerless"):
        el.read_labels(p)


def test_duplicate_and_bad_rows_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate"):
        el.read_labels(write_csv(tmp_path, "signer900_sample1,7\nsigner900_sample1,8\n"))
    with pytest.raises(ValueError, match="2 columns"):
        el.read_labels(write_csv(tmp_path, "signer900_sample1,7,extra\n", "b.csv"))


@pytest.mark.parametrize("name,expected", [
    ("signer900_sample1_color.mp4", "signer900_sample1"),
    ("signer900_sample1_depth.mp4", "signer900_sample1"),
    ("signer900_sample1.mp4", "signer900_sample1"),
    ("clip-01_cr_0.1.mp4", "clip-01_cr_0.1"),
])
def test_sample_id_from_filename(name, expected):
    assert el.sample_id_from_filename(name) == expected


def test_label_matching_and_unlabelled_video_is_null(tmp_path):
    labels = el.read_labels(write_csv(tmp_path, "signer900_sample1,7\n"))
    assert el.label_for_video("signer900_sample1_color.mp4", labels) == ("signer900_sample1", 7)
    assert el.label_for_video("signer900_sample99_color.mp4", labels) == ("signer900_sample99", None)
    assert el.label_for_video("signer900_sample1_color.mp4", None) == ("signer900_sample1", None)


# --- selection -----------------------------------------------------------

def test_selection_is_sorted_and_limited(tmp_path):
    for n in ["c_color.mp4", "a_color.mp4", "b_color.mp4", "a_depth.mp4", "notes.txt"]:
        (tmp_path / n).write_bytes(b"x")
    sel, rule = el.select_videos([tmp_path], "*_color.mp4", limit=2)
    assert [p.name for p in sel] == ["a_color.mp4", "b_color.mp4"]
    assert "first 2 of 3" in rule and "sorted by file name" in rule
    sel_all, rule_all = el.select_videos([tmp_path])
    assert [p.name for p in sel_all] == ["a_color.mp4", "a_depth.mp4", "b_color.mp4", "c_color.mp4"]
    assert "all 4" in rule_all


# --- report / summary ----------------------------------------------------

def fabricated_results():
    ok = {"video": "signer900_sample1_color.mp4", "sample_id": "signer900_sample1",
          "class_id": 7, "status": "ok", "error": None, "frames": 50, "duration_s": 2.0,
          "processing_s": 1.0, "processing_fps": 50.0,
          "missing_pct": {"pose": 0.0, "face": 0.0, "left_hand": 80.0, "right_hand": 10.0}}
    ok2 = dict(ok, video="signer900_sample2_color.mp4", sample_id="signer900_sample2",
               class_id=None, processing_fps=30.0)
    bad = {"video": "broken.mp4", "sample_id": "broken", "class_id": None,
           "status": "failed", "error": "could not open video"}
    return [ok, ok2, bad]


def test_report_rows_and_columns(tmp_path):
    path = tmp_path / "report.csv"
    el.write_report(path, fabricated_results())
    import csv
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0].keys()) == el.REPORT_COLUMNS
    assert len(rows) == 3
    assert rows[0]["status"] == "ok" and rows[0]["class_id"] == "7"
    assert rows[0]["missing_pct_left_hand"] == "80.0"
    assert rows[1]["class_id"] == ""
    assert rows[2]["status"] == "failed"
    assert rows[2]["error"] == "could not open video"
    assert rows[2]["frames"] == "" and rows[2]["missing_pct_pose"] == ""


def test_summary_counts_failures():
    s = el.summarize(fabricated_results(), total_s=3.5, selection_rule="rule")
    assert s["total_videos"] == 3
    assert s["succeeded"] == 2
    assert s["failed"] == 1
    assert s["failed_videos"] == ["broken.mp4"]
    assert s["unlabelled_videos"] == 2
    assert s["mean_processing_fps"] == 40.0
    assert s["median_processing_fps"] == 40.0
    assert s["selection_rule"] == "rule"
    assert "1 failed" in el.format_summary(s)


def test_summary_all_failed_has_no_fps():
    s = el.summarize([fabricated_results()[2]], 0.1, "rule")
    assert s["succeeded"] == 0 and s["failed"] == 1
    assert s["mean_processing_fps"] is None and s["median_processing_fps"] is None


# --- npz round trip --------------------------------------------------------

def test_npz_round_trip(tmp_path):
    frames = [full_frame(0.25) for _ in range(3)]
    frames[0]["face"] = None
    kp, mask = el.stack_frames(frames)
    versions = {"python": "3.x", "mediapipe": "fake", "opencv": "fake", "numpy": np.__version__}
    meta = el.build_meta(video="signer900_sample1_color.mp4", sample_id="signer900_sample1",
                         class_id=None, split="dev", source_fps=25.0, frame_count=3,
                         frame_count_reported=3, width=160, height=120, versions=versions,
                         created_at="2026-11-27T00:00:00+00:00")
    path = tmp_path / "x.npz"
    el.write_npz(path, kp, mask, meta)

    kp2, mask2, meta2 = el.read_npz(path)
    assert kp2.shape == (3, 1662) and kp2.dtype == np.float32
    assert mask2.shape == (3, 4) and mask2.dtype == np.uint8
    assert np.array_equal(kp, kp2) and np.array_equal(mask, mask2)
    assert mask2[0].tolist() == [1, 0, 1, 1]
    assert meta2 == json.loads(json.dumps(meta))
    assert meta2["class_id"] is None
    assert meta2["layout_name"] == "legacy_holistic_543"
    assert meta2["concat_order"] == ["pose", "face", "left_hand", "right_hand"]
    assert meta2["groups"]["pose"] == {"landmarks": 33, "fields": ["x", "y", "z", "visibility"],
                                       "values": 132}
    assert meta2["groups"]["face"]["landmarks"] == 468
    assert meta2["holistic_settings"]["model_complexity"] == 1
    assert meta2["holistic_settings"]["smooth_landmarks"] is True
    assert meta2["holistic_settings"]["refine_face_landmarks"] is False
    for key in ("sample_id", "split", "source_fps", "frame_count", "width", "height",
                "versions", "created_at"):
        assert key in meta2


def test_write_npz_rejects_wrong_shape(tmp_path):
    with pytest.raises(ValueError):
        el.write_npz(tmp_path / "bad.npz", np.zeros((2, 1000), np.float32),
                     np.zeros((2, 4), np.uint8), {})


# --- repository guard ------------------------------------------------------

def test_guard_flags_repo_path_unless_ignored(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    out = repo / "some_out"
    outside = tmp_path / "outside"
    assert el.unsafe_output_paths([(out, True)], lambda p, r, d: False) == [str(out)]
    assert el.unsafe_output_paths([(out, True)], lambda p, r, d: True) == []
    assert el.unsafe_output_paths([(outside, True)], lambda p, r, d: False) == []


def test_process_video_failure_does_not_raise(tmp_path, monkeypatch):
    # Simulate an environment where the import itself fails: the video must be
    # reported as failed instead of stopping the batch.
    monkeypatch.setitem(sys.modules, "cv2", None)
    r = el.process_video(tmp_path / "missing.mp4", tmp_path, "missing", None, "dev", {})
    assert r["status"] == "failed" and r["error"]
