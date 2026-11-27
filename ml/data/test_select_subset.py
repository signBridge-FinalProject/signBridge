"""Tests for select_subset.py using small synthetic videos (no AUTSL data).

Run: python -m unittest test_select_subset -v   (from ml/data)
"""
import argparse
import contextlib
import csv
import io
import json
import os
import tempfile
import unittest

import cv2
import numpy as np

import select_subset as ss


def write_video(path, kind, frames=24, size=64):
    """kind: moving | dark | frozen | flat"""
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (size, size))
    rng = np.random.default_rng(0)
    base = rng.integers(0, 255, (size, size), dtype=np.uint8)
    for i in range(frames):
        if kind == "moving":
            img = np.roll(base, i * 3, axis=1)
        elif kind == "dark":
            img = (np.roll(base, i * 3, axis=1) // 20).astype(np.uint8)
        elif kind == "frozen":
            img = base
        else:  # flat grey, no structure
            img = np.full((size, size), 128, np.uint8)
        w.write(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
    w.release()


def args(**kw):
    a = ss.build_args(["--signlist", "x", "--split", "train", "d", "l", "--out", "o"])
    for k, v in kw.items():
        setattr(a, k, v)
    return a


class MeasureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.opt = {"frame_stride": 1, "frozen_diff": 0.25}

    def tearDown(self):
        self.tmp.cleanup()

    def _row(self, kind, sid="signer0_sample1", depth=True):
        if kind == "missing":
            pass
        elif kind == "corrupt":
            with open(os.path.join(self.d, f"{sid}_color.mp4"), "wb") as f:
                f.write(b"not a video")
        else:
            write_video(os.path.join(self.d, f"{sid}_color.mp4"), kind)
        if depth:
            write_video(os.path.join(self.d, f"{sid}_depth.mp4"), "moving")
        return ss.measure(("train", sid, 0, "signer0", self.d, self.opt))

    def test_moving_video_passes(self):
        r = self._row("moving")
        self.assertEqual(r["decoded_frames"], 24)
        self.assertEqual((r["width"], r["height"]), (64, 64))
        self.assertGreater(r["motion"], 0.5)
        self.assertEqual(ss.exclusion_reasons(r, args()), [])

    def test_dark_video_excluded(self):
        reasons = ss.exclusion_reasons(self._row("dark"), args())
        self.assertTrue(any(x.startswith("brightness") for x in reasons), reasons)

    def test_frozen_video_excluded(self):
        r = self._row("frozen")
        self.assertEqual(r["frozen_ratio"], 1.0)
        reasons = ss.exclusion_reasons(r, args())
        self.assertTrue(any(x.startswith("frozen_ratio") for x in reasons))
        self.assertTrue(any(x.startswith("motion") for x in reasons))

    def test_flat_video_excluded_by_contrast(self):
        self.assertTrue(any(x.startswith("contrast") for x in ss.exclusion_reasons(self._row("flat"), args())))

    def test_missing_and_corrupt_are_unreadable(self):
        for kind, sid in (("missing", "signer0_sample7"), ("corrupt", "signer0_sample8")):
            r = self._row(kind, sid=sid)
            self.assertEqual(r["decoded_frames"], 0)
            expected = "missing colour" if kind == "missing" else "unreadable"
            self.assertTrue(ss.exclusion_reasons(r, args())[0].startswith(expected))

    def test_missing_depth_excluded(self):
        r = self._row("moving", depth=False)
        self.assertIn("depth video missing or empty", ss.exclusion_reasons(r, args()))


def fake_row(split, sid, cid, signer, sharp, **over):
    r = {"split": split, "sample_id": sid, "class_id": cid, "signer": signer, "error": "", "color_bytes": 10,
         "decoded_frames": 40, "depth_bytes": 10, "brightness": 100.0, "contrast": 40.0,
         "sharpness": sharp, "motion": 5.0, "frozen_ratio": 0.0}
    r.update(over)
    return r


class SelectionTests(unittest.TestCase):
    def test_percentile_ranks_ties(self):
        self.assertEqual(ss.percentile_ranks([1, 2, 2, 3]), [0.0, 0.5, 0.5, 1.0])
        self.assertEqual(ss.percentile_ranks([7]), [1.0])

    def test_signer_round_robin_and_limit(self):
        rows = [fake_row("train", f"signer0_sample{i}", 1, "signer0", 100 + i) for i in range(5)]
        rows += [fake_row("train", f"signer1_sample{i}", 1, "signer1", 10 + i) for i in range(2)]
        m = ss.select(rows, args(samples_per_class=4))
        chosen = [r for r in m if r["included"] == "yes"]
        self.assertEqual(len(chosen), 4)
        # both signers present although signer0 scores higher on sharpness
        self.assertEqual({r["signer"] for r in chosen}, {"signer0", "signer1"})
        self.assertEqual(sum(r["signer"] == "signer1" for r in chosen), 2)
        rest = [r for r in m if r["included"] == "no"]
        self.assertTrue(all("limit 4 per class" in r["reason"] for r in rest))

    def test_threshold_exclusion_reason(self):
        rows = [fake_row("train", "signer0_sample1", 1, "signer0", 50),
                fake_row("train", "signer0_sample2", 1, "signer0", 50, brightness=5.0)]
        m = {r["sample_id"]: r for r in ss.select(rows, args())}
        self.assertEqual(m["signer0_sample1"]["included"], "yes")
        self.assertTrue(m["signer0_sample2"]["reason"].startswith("excluded: brightness"))

    def test_test_split_kept_whole(self):
        rows = [fake_row("test", f"signer2_sample{i}", 1, "signer2", 50, brightness=5.0) for i in range(6)]
        rows.append(fake_row("test", "signer2_sample99", 1, "signer2", 0, decoded_frames=0, error="bad"))
        m = ss.select(rows, args(samples_per_class=2))
        self.assertEqual(sum(r["included"] == "yes" for r in m), 6)
        bad = [r for r in m if r["sample_id"] == "signer2_sample99"][0]
        self.assertEqual(bad["included"], "no")


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.d = self.tmp.name
        self.signlist = os.path.join(d, "signlist.csv")
        with open(self.signlist, "w", encoding="utf-8") as f:
            f.write("ClassId,TR,EN\n0,hastane,hospital\n1,doktor,doctor\n2,cay,tea\n")
        self.vids = {s: os.path.join(d, s) for s in ("train", "test")}
        labels = {"train": [("signer0_sample1", 0, "moving"), ("signer0_sample2", 0, "dark"),
                            ("signer3_sample3", 0, "moving"), ("signer0_sample4", 1, "moving"),
                            ("signer0_sample5", 2, "moving")],
                  "test": [("signer1_sample1", 0, "dark"), ("signer1_sample2", 1, "moving")]}
        self.labels = {}
        for split, rows in labels.items():
            os.makedirs(self.vids[split])
            self.labels[split] = os.path.join(d, f"{split}.csv")
            with open(self.labels[split], "w") as f:
                for sid, cid, kind in rows:
                    f.write(f"{sid},{cid}\n")
                    write_video(os.path.join(self.vids[split], f"{sid}_color.mp4"), kind)
                    write_video(os.path.join(self.vids[split], f"{sid}_depth.mp4"), "moving")
        self.classes_csv = os.path.join(d, "classes.csv")
        with open(self.classes_csv, "w") as f:
            f.write("gloss,autsl_class_id\nHASTANE,0\nDOKTOR,1\nMI,\n")
        self.out = os.path.join(d, "out")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, extra):
        argv = ["--signlist", self.signlist, "--split", "train", self.vids["train"], self.labels["train"],
                "--split", "test", self.vids["test"], self.labels["test"], "--out", self.out, "--workers", "1"]
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = ss.main(argv + extra)
        return code, err.getvalue()

    def read(self, name):
        with open(os.path.join(self.out, name), newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_full_run(self):
        code, _ = self.run_main(["--classes", self.classes_csv, "--samples-per-class", "5"])
        self.assertEqual(code, 0)
        summary = {r["split"]: r for r in self.read("summary.csv")}
        self.assertEqual(summary["train"]["labelled_samples_all_classes"], "5")
        self.assertEqual(summary["train"]["labelled_samples_chosen_classes"], "4")  # class 2 not chosen
        self.assertEqual(summary["train"]["selected"], "3")  # dark one excluded
        self.assertEqual(summary["test"]["selected"], "2")  # test kept whole, dark one included
        manifest = self.read("manifest.csv")
        self.assertEqual(len(manifest), 6)
        self.assertTrue(all(r["reason"] for r in manifest))
        run = json.load(open(os.path.join(self.out, "run.json"), encoding="utf-8"))
        self.assertEqual(run["chosen_class_ids"], [0, 1])
        self.assertIn("train_labels", run["inputs_sha256"])
        # aggregate files carry no sample IDs
        for name in ("summary.csv", "class-summary.csv", "quality-distribution.csv"):
            with open(os.path.join(self.out, name), encoding="utf-8") as f:
                self.assertNotRegex(f.read(), r"signer\d+_sample\d+")

    def test_unknown_class_rejected_without_output(self):
        code, err = self.run_main(["--classes", "0,9"])
        self.assertEqual(code, 2)
        self.assertIn("unknown class IDs [9]", err)
        self.assertFalse(os.path.exists(self.out))

    def test_bad_label_row_rejected(self):
        with open(self.labels["train"], "a") as f:
            f.write("not_a_sample,0\n")
        code, err = self.run_main([])
        self.assertEqual(code, 2)
        self.assertIn("is not signerX_sampleY", err)


if __name__ == "__main__":
    unittest.main()
