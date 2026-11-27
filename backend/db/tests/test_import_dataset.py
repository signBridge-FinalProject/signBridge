"""SB-51 import checks using fabricated files only; no AUTSL labels, mapping or media."""
import contextlib
import io
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest

import db
import import_dataset

QUERIES = Path(__file__).resolve().parents[1] / "queries" / "dataset_examples.sql"

MAPPING = "ClassId,TR,EN\n0,örnek,example\n1,ışık,light\n2,Çiçek,flower\n3,şeker,sugar\n"
TRAIN = ("signer900_sample1,0\nsigner900_sample2,1\nsigner900_sample3,0\n"
         "signer901_sample1,2\nsigner901_sample2,0\n")
VALIDATION = "signer902_sample1,1\nsigner902_sample2,2\n"
TEST = "signer903_sample1,0\n"
DATASET_TABLES = ("dataset_release", "dataset_class", "dataset_split",
                  "dataset_signer_split", "video_sample")


def load_queries():
    text = QUERIES.read_text(encoding="utf-8")
    parts = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = self.dir / "private" / "metadata.sqlite3"
        self.report = self.dir / "private" / "report.json"
        self.files = {}
        self.write("mapping.csv", MAPPING)
        self.write("train_labels.csv", TRAIN)
        self.write("validation_ground_truth.csv", VALIDATION)
        self.write("test_ground_truth.csv", TEST)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        self.files[name] = path
        return path

    def args(self, *extra, labels=None, version="fixture-v1"):
        labels = labels or {"train": self.files["train_labels.csv"],
                            "validation": self.files["validation_ground_truth.csv"],
                            "test": self.files["test_ground_truth.csv"]}
        return (["--db", str(self.db), "--dataset-name", "SYNTHETIC", "--dataset-version", version,
                 "--mapping", str(self.files["mapping.csv"]), "--report", str(self.report),
                 "--labels", *[f"{k}={v}" for k, v in labels.items()]] + list(extra))

    def run_import(self, *extra, **kw):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = import_dataset.run(self.args(*extra, **kw))
        self.stdout, self.stderr = out.getvalue(), err.getvalue()
        return code

    def counts(self):
        with contextlib.closing(db.connect(self.db)) as conn:
            return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in DATASET_TABLES}

    def query(self, sql, params=()):
        with contextlib.closing(db.connect(self.db)) as conn:
            return conn.execute(sql, params).fetchall()

    def report_json(self):
        return json.loads(self.report.read_text(encoding="utf-8"))

    def assert_nothing_written(self):
        if self.db.exists():
            self.assertEqual(set(self.counts().values()), {0})

    # ---------------------------------------------------------------- happy path

    def test_first_import_creates_expected_rows(self):
        self.assertEqual(self.run_import(), 0, self.stderr)
        self.assertEqual(self.counts(), {"dataset_release": 1, "dataset_class": 4, "dataset_split": 3,
                                         "dataset_signer_split": 4, "video_sample": 8})
        self.assertEqual(self.query("SELECT original_label,name_tr,name_en FROM dataset_class "
                                    "ORDER BY original_label"),
                         [("0", "örnek", "example"), ("1", "ışık", "light"),
                          ("2", "Çiçek", "flower"), ("3", "şeker", "sugar")])
        self.assertEqual(self.query("SELECT signer_id,split_name FROM dataset_signer_split ORDER BY signer_id"),
                         [("signer900", "train"), ("signer901", "train"),
                          ("signer902", "validation"), ("signer903", "test")])
        self.assertEqual(self.query("SELECT original_label,signer_id,split_name,color_path,depth_path,"
                                    "color_bytes,depth_bytes FROM video_sample WHERE sample_id=?",
                                    ("signer902_sample1",)),
                         [("1", "signer902", "validation", "val/signer902_sample1_color.mp4",
                           "val/signer902_sample1_depth.mp4", None, None)])
        for (path,) in self.query("SELECT color_path FROM video_sample UNION ALL "
                                  "SELECT depth_path FROM video_sample"):
            self.assertRegex(path, r"^(train|val|test)/signer\d+_sample\d+_(color|depth)\.mp4$")
        release = self.query("SELECT dataset_version,usage_conditions FROM dataset_release")[0]
        self.assertEqual(release[0], "fixture-v1")
        self.assertIn("non-commercial", release[1])
        report = self.report_json()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["differences"], [])
        self.assertEqual(report["check"]["foreign_key_violations"], 0)
        self.assertEqual(report["file_counts"]["total"], {"samples": 8, "signers": 4, "classes": 4})

    def test_second_run_adds_no_rows(self):
        self.assertEqual(self.run_import(), 0)
        before = self.counts()
        self.assertEqual(self.run_import(), 0, self.stderr)
        self.assertEqual(self.counts(), before)
        rows = self.report_json()["rows"]
        self.assertEqual(sum(r["inserted"] for r in rows.values()), 0)
        self.assertEqual(rows["video_sample"]["unchanged"], 8)

    def test_local_snapshot_is_declared(self):
        self.assertEqual(self.run_import("--local-snapshot", version="team-snapshot-2026-11-27"), 0)
        description = self.query("SELECT description FROM dataset_release")[0][0]
        self.assertIn("local snapshot ID, not a provider-issued version", description)

    def test_original_label_is_opaque_text(self):
        self.write("mapping.csv", "ClassId,TR,EN\n007,örnek,example\n")
        self.write("train_labels.csv", "signer900_sample1,007\n")
        self.assertEqual(self.run_import(labels={"train": self.files["train_labels.csv"]}), 0)
        self.assertEqual(self.query("SELECT original_label FROM video_sample"), [("007",)])
        self.write("train_labels.csv", "signer900_sample2,7\n")
        self.assertEqual(self.run_import(labels={"train": self.files["train_labels.csv"]}), 1)

    # ---------------------------------------------------------------- conflicts and rollback

    def test_changed_class_for_existing_sample_rolls_back(self):
        self.assertEqual(self.run_import(), 0)
        before = self.counts()
        self.write("train_labels.csv", TRAIN.replace("signer900_sample1,0", "signer900_sample1,3")
                   + "signer901_sample9,1\n")
        self.assertEqual(self.run_import(), 1)
        self.assertIn("video_sample [sample_id=signer900_sample1] original_label: database='0', input='3'",
                      self.stderr)
        self.assertEqual(self.counts(), before)  # the new signer901_sample9 was rolled back too
        self.assertEqual(self.query("SELECT original_label FROM video_sample WHERE sample_id=?",
                                    ("signer900_sample1",)), [("0",)])
        self.assertEqual(self.report_json()["status"], "failed")

    def test_changed_class_name_is_not_overwritten(self):
        self.assertEqual(self.run_import(), 0)
        self.write("mapping.csv", MAPPING.replace("ışık,light", "ışık,lamp"))
        self.assertEqual(self.run_import(), 1)
        self.assertIn("name_en: database='light', input='lamp'", self.stderr)
        self.assertEqual(self.query("SELECT name_en FROM dataset_class WHERE original_label='1'"), [("light",)])

    def test_invalid_inputs_write_nothing(self):
        cases = {
            "unknown class": ("train_labels.csv", TRAIN + "signer901_sample3,99\n", "not in the class mapping"),
            "duplicate sample": ("train_labels.csv", TRAIN + "signer900_sample1,1\n", "duplicate sample_id"),
            "header row": ("train_labels.csv", "sample_id,class_id\n" + TRAIN, "header row"),
            "malformed row": ("train_labels.csv", TRAIN + "signer901_sample3,1,extra\n", "expected 2 columns"),
            "bad sample id": ("train_labels.csv", TRAIN + "signer901-sample3,1\n", "invalid sample_id"),
            "mapping without header": ("mapping.csv", "0,örnek,example\n", "header"),
            "duplicate class": ("mapping.csv", MAPPING + "1,ışık,light\n", "duplicate ClassId"),
        }
        for name, (file, text, message) in cases.items():
            with self.subTest(name):
                original = self.files[file].read_text(encoding="utf-8")
                self.write(file, text)
                try:
                    self.assertEqual(self.run_import(), 1)
                    self.assertIn(message, self.stderr)
                    self.assert_nothing_written()
                finally:
                    self.write(file, original)

    def test_sample_in_two_splits_rejected(self):
        self.write("test_ground_truth.csv", TEST + "signer900_sample1,0\n")
        self.assertEqual(self.run_import(), 1)
        self.assertIn("appears in both train and test", self.stderr)
        self.assert_nothing_written()

    def test_signer_in_two_splits_rejected(self):
        self.write("test_ground_truth.csv", TEST + "signer900_sample7,0\n")
        self.assertEqual(self.run_import(), 1)
        self.assertIn("signer 'signer900' appears in both train and test", self.stderr)
        self.assert_nothing_written()

    def test_signer_split_conflict_with_existing_release_rejected(self):
        self.assertEqual(self.run_import(labels={"train": self.files["train_labels.csv"]}), 0)
        before = self.counts()
        self.write("test_ground_truth.csv", "signer900_sample7,0\n")
        self.assertEqual(self.run_import(labels={"test": self.files["test_ground_truth.csv"]}), 1)
        self.assertIn("dataset_signer_split [signer_id=signer900] split_name", self.stderr)
        self.assertEqual(self.counts(), before)

    def test_placeholder_versions_rejected(self):
        for version in ("latest", "unknown", " TBD "):
            with self.subTest(version):
                self.assertEqual(self.run_import(version=version), 1)
                self.assertIn("not allowed", self.stderr)
                self.assertFalse(self.db.exists())

    def test_bad_label_argument_rejected(self):
        self.assertEqual(self.run_import(labels={"val": self.files["validation_ground_truth.csv"]}), 1)
        self.assertIn("split=path", self.stderr)

    # ---------------------------------------------------------------- count comparison

    def test_counts_match_and_expect_match(self):
        code = self.run_import("--expect", "train=5,validation=2,test=1,classes=4,signers=4,"
                                           "samples=8,train_signers=2,validation_classes=2")
        self.assertEqual(code, 0, self.stdout)
        report = self.report_json()
        self.assertTrue(all(r["status"] == "match" for r in report["comparison"]))
        self.assertEqual(report["database_counts"]["per_split"]["train"],
                         {"samples": 5, "signers": 2, "classes": 3})

    def test_expect_mismatch_is_reported_with_nonzero_exit(self):
        self.assertEqual(self.run_import("--expect", "train=6,classes=4"), 3)
        report = self.report_json()
        self.assertEqual(report["status"], "imported_with_differences")
        self.assertEqual([(d["split"], d["metric"], d["files"], d["database"], d["expected"])
                          for d in report["differences"]], [("train", "samples", 5, 5, 6)])
        self.assertIn("expected=6  DIFFERENCE", self.stdout)

    def test_expect_for_split_not_imported_is_reported(self):
        code = self.run_import("--expect", "train=5,test=1", labels={"train": self.files["train_labels.csv"]})
        self.assertEqual(code, 3)
        self.assertEqual([d["metric"] for d in self.report_json()["differences"]], ["test"])

    def test_database_rows_missing_from_input_are_reported(self):
        self.assertEqual(self.run_import(), 0)
        self.write("train_labels.csv", "\n".join(TRAIN.splitlines()[:-1]) + "\n")
        self.assertEqual(self.run_import(), 3)
        diff = [(d["split"], d["metric"], d["files"], d["database"]) for d in self.report_json()["differences"]]
        self.assertIn(("train", "samples", 4, 5), diff)
        self.assertIn(("total", "samples", 7, 8), diff)

    def test_unknown_expect_key_rejected(self):
        self.assertEqual(self.run_import("--expect", "trains=5"), 1)
        self.assertIn("unknown entry", self.stderr)

    # ---------------------------------------------------------------- media root

    def test_media_root_records_sizes_and_reports_missing(self):
        media = self.dir / "media"
        (media / "train").mkdir(parents=True)
        (media / "train" / "signer900_sample1_color.mp4").write_bytes(b"c" * 11)
        (media / "train" / "signer900_sample1_depth.mp4").write_bytes(b"d" * 7)
        (media / "train" / "signer900_sample2_color.mp4").write_bytes(b"")  # zero bytes
        code = self.run_import("--media-root", str(media), labels={"train": self.files["train_labels.csv"]})
        self.assertEqual(code, 3)
        self.assertEqual(self.query("SELECT color_bytes,depth_bytes FROM video_sample WHERE sample_id=?",
                                    ("signer900_sample1",)), [(11, 7)])
        self.assertEqual(self.query("SELECT color_bytes,depth_bytes FROM video_sample WHERE sample_id=?",
                                    ("signer900_sample2",)), [(None, None)])
        issues = {(m["path"], m["problem"]) for m in self.report_json()["media_issues"]}
        self.assertIn(("train/signer900_sample2_color.mp4", "zero bytes"), issues)
        self.assertIn(("train/signer900_sample2_depth.mp4", "missing"), issues)
        self.assertEqual(len(issues), 8)  # 10 expected files, 2 present and non-empty

    def test_media_root_all_present(self):
        media = self.dir / "media"
        (media / "val").mkdir(parents=True)
        for line in VALIDATION.splitlines():
            sample = line.split(",")[0]
            for kind in ("color", "depth"):
                (media / "val" / f"{sample}_{kind}.mp4").write_bytes(b"x" * 5)
        code = self.run_import("--media-root", str(media),
                               labels={"validation": self.files["validation_ground_truth.csv"]})
        self.assertEqual(code, 0, self.stdout)
        self.assertEqual(self.query("SELECT DISTINCT color_bytes,depth_bytes FROM video_sample"), [(5, 5)])

    # ---------------------------------------------------------------- boundaries

    def test_no_curated_mapping_or_sign_rows(self):
        self.assertEqual(self.run_import(), 0)
        self.assertEqual(self.query("SELECT count(*) FROM dataset_mapping"), [(0,)])
        self.assertEqual(self.query("SELECT count(*) FROM sign_entry"), [(0,)])

    def test_repository_guard(self):
        repo = self.dir / "repo"
        (repo / ".git").mkdir(parents=True)
        inside, outside = repo / "x.sqlite3", self.dir / "outside" / "x.sqlite3"
        self.assertEqual(import_dataset.unsafe_paths([inside], lambda p, r: False), [str(inside)])
        self.assertEqual(import_dataset.unsafe_paths([inside], lambda p, r: True), [])
        self.assertEqual(import_dataset.unsafe_paths([outside, None], lambda p, r: False), [])

    # ---------------------------------------------------------------- example queries

    def test_example_queries(self):
        self.assertEqual(self.run_import(), 0)
        queries = load_queries()
        self.assertEqual(set(queries), {"samples_per_split", "samples_per_class_and_split", "signers_per_split",
                                        "classes_with_fewest_train_samples", "sample_lookup",
                                        "samples_per_signer"})
        p = {"dataset_name": "SYNTHETIC", "dataset_version": "fixture-v1", "sample_id": "signer902_sample2"}
        with contextlib.closing(db.connect(self.db)) as conn:
            run = lambda name: conn.execute(queries[name], p).fetchall()  # noqa: E731
            self.assertEqual(run("samples_per_split"), [("train", 5), ("validation", 2), ("test", 1)])
            self.assertEqual(run("samples_per_class_and_split"), [
                ("0", "örnek", "example", "train", 3), ("0", "örnek", "example", "test", 1),
                ("1", "ışık", "light", "train", 1), ("1", "ışık", "light", "validation", 1),
                ("2", "Çiçek", "flower", "train", 1), ("2", "Çiçek", "flower", "validation", 1)])
            self.assertEqual(run("signers_per_split"), [("train", 2, "signer900,signer901"),
                                                         ("validation", 1, "signer902"),
                                                         ("test", 1, "signer903")])
            self.assertEqual(run("classes_with_fewest_train_samples"), [
                ("3", "şeker", "sugar", 0), ("1", "ışık", "light", 1),
                ("2", "Çiçek", "flower", 1), ("0", "örnek", "example", 3)])
            self.assertEqual(run("sample_lookup"), [
                ("signer902_sample2", "2", "Çiçek", "flower", "signer902", "validation",
                 "val/signer902_sample2_color.mp4", "val/signer902_sample2_depth.mp4", None, None)])
            self.assertEqual(run("samples_per_signer"), [("signer900", "train", 3), ("signer901", "train", 2),
                                                          ("signer902", "validation", 2),
                                                          ("signer903", "test", 1)])
            other = dict(p, dataset_version="other")
            self.assertEqual(conn.execute(queries["samples_per_split"], other).fetchall(), [])


if __name__ == "__main__":
    unittest.main()
