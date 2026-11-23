"""Tests for coverage_audit.py using small synthetic inputs (no AUTSL data).

Run: python -m unittest test_coverage_audit -v   (from this directory)
"""
import contextlib
import csv
import io
import os
import tempfile
import unittest

import coverage_audit as ca

# Synthetic class list: only the names the curated tables refer to, plus one
# extra class that receives no samples in any split.
NAMES = ["hastane", "doktor", "yardim", "ilac", "yarin", "okul", "cay", "eczane", "tesekkur", "saat",
         "beraber", "arkadas", "nerede", "olur", "tamam", "rica_etmek", "para", "seker", "sut", "bardak"]
EMPTY_CLASS = "bos_sinif"


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.out = os.path.join(self.d, "out")
        self.classes = [["ClassId", "TR", "EN"]] + [[str(i), n, n] for i, n in enumerate(NAMES)] + \
                       [[str(len(NAMES)), EMPTY_CLASS, "empty"]]
        # train: 2 samples per real class; validation/test: 1 per real class
        self.train = [[f"signer0_sample{i}_{k}", str(i)] for i in range(len(NAMES)) for k in range(2)]
        self.val = [[f"signer1_sample{i}", str(i)] for i in range(len(NAMES))]
        self.test = [[f"signer2_sample{i}", str(i)] for i in range(len(NAMES))]

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def read_csv(path):
        with open(path, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def write(self, name, rows):
        p = os.path.join(self.d, name)
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        return p

    def run_audit(self):
        args = ["--signlist", self.write("classes.csv", self.classes),
                "--train", self.write("train.csv", self.train),
                "--validation", self.write("val.csv", self.val),
                "--test", self.write("test.csv", self.test), "--out", self.out]
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = ca.main(args)
        return code, err.getvalue()

    def assert_fails_without_output(self, fragment):
        code, err = self.run_audit()
        self.assertEqual(code, 2, err)
        self.assertIn(fragment, err)
        self.assertFalse(os.path.exists(self.out), "no output directory may be created on invalid input")

    def test_valid_input_writes_four_csvs_and_counts_zero_classes(self):
        code, err = self.run_audit()
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(os.listdir(self.out)),
                         ["candidate-classes.csv", "coverage-glosses.csv", "coverage-summary.csv", "label-checks.csv"])
        checks = self.read_csv(os.path.join(self.out, "label-checks.csv"))
        train = [r for r in checks if r["split"] == "train"][0]
        self.assertEqual(train["classes_with_zero_samples"], "1")
        self.assertEqual(train["min_samples_per_class_incl_zero"], "0")
        self.assertEqual(train["max_samples_per_class"], "2")
        summary = {r["scenario"]: r for r in self.read_csv(os.path.join(self.out, "coverage-summary.csv"))}
        self.assertEqual(summary["HP-1"]["coverage"], "3/3")
        self.assertEqual(summary["HP-4"]["coverage"], "1/4")
        self.assertEqual(summary["HP-4"]["tokens_total"], "5")

    def test_wrong_column_count(self):
        self.train.append(["signer0_bad", "1", "extra"])
        self.assert_fails_without_output("expected 2 columns")

    def test_non_integer_class_id(self):
        self.val.append(["signer1_bad", "x"])
        self.assert_fails_without_output("is not an integer")

    def test_class_id_not_in_list(self):
        self.test.append(["signer2_bad", "999"])
        self.assert_fails_without_output("not in the class list")

    def test_duplicate_sample_id_within_split(self):
        self.train.append(list(self.train[0]))
        self.assert_fails_without_output("duplicate sample IDs")

    def test_duplicate_sample_id_across_splits(self):
        self.test.append([self.val[0][0], "0"])
        self.assert_fails_without_output("appears in both")

    def test_duplicate_class_id(self):
        self.classes.append(["0", "baska", "other"])
        self.assert_fails_without_output("duplicate ClassId")

    def test_bad_header(self):
        self.classes[0] = ["id", "tr", "en"]
        self.assert_fails_without_output("header must be")

    def test_curated_found_class_missing(self):
        self.classes = [r for r in self.classes if r[1] != "okul"]
        self.assert_fails_without_output("curated gloss OKUL")

    def test_curated_not_found_but_class_exists(self):
        self.classes.append(["500", "simit", "bagel"])
        self.assert_fails_without_output("curated gloss SİMİT")

    def test_existing_outputs_not_overwritten_on_error(self):
        os.makedirs(self.out)
        marker = os.path.join(self.out, "coverage-summary.csv")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("previous")
        self.train.append(list(self.train[0]))
        code, err = self.run_audit()
        self.assertEqual(code, 2)
        with open(marker, encoding="utf-8") as f:
            self.assertEqual(f.read(), "previous")


if __name__ == "__main__":
    unittest.main()
