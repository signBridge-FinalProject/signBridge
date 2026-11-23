"""SB-47 behavioral checks using fabricated data only; no AUTSL rows or media."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import db


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.migrate(self.conn)

    def tearDown(self):
        self.conn.close()

    def sign(self, number=9001, gloss="İŞARET"):
        sign_id = f"SIGN_{number}"
        self.conn.execute("INSERT INTO sign_entry(sign_id,gloss,definition_tr,domain,variant_code) "
                          "VALUES (?,?,?,'daily','v1')", (sign_id, gloss, "Yalnızca yapay test kaydı"))
        return sign_id

    def source(self, sign_id, suffix="a"):
        source_id = sign_id + suffix
        self.conn.execute("INSERT INTO sign_source VALUES (?,?,?,NULL,?,?,?)",
                          (source_id, sign_id, "Fabricated test reference", "synthetic locator",
                           "2026-11-21", "Synthetic fixture only; not a dataset rights decision"))
        return source_id

    def event(self, sign_id, target, source=None, clip=None, role="source_checker"):
        sequence = self.conn.execute("SELECT count(*) FROM review_event").fetchone()[0]+1
        self.conn.execute("INSERT INTO review_event(review_id,sign_id,clip_id,target_status,source_id,"
                          "reviewer_name,reviewer_role,reviewed_at,review_note) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f"test-review-{sequence}", sign_id, clip, target, source,
                           "Synthetic reviewer", role, "2026-11-21T00:00:00Z", "Synthetic workflow test"))

    def checked_sign(self, number=9001):
        sign = self.sign(number)
        self.conn.execute("INSERT INTO sign_equivalent VALUES (?,?)", (sign, "işaret"))
        source = self.source(sign)
        self.event(sign, "source_checked", source)
        return sign, source

    def release(self):
        self.conn.execute("INSERT INTO dataset_release VALUES ('SYNTHETIC','fixture-v1',"
                          "'Artificial test release','test fixture','No source dataset content')")
        self.conn.execute("INSERT INTO dataset_class VALUES ('SYNTHETIC','fixture-v1','0007','örnek','example')")
        self.conn.executemany("INSERT INTO dataset_split VALUES ('SYNTHETIC','fixture-v1',?)",
                              [(name,) for name in ("train", "validation", "test")])
        self.conn.execute("INSERT INTO dataset_signer_split VALUES ('SYNTHETIC','fixture-v1','synthetic-signer','train')")

    def sample(self, color="train/synthetic_color.mp4", split="train", label="0007", signer="synthetic-signer"):
        self.conn.execute("INSERT INTO video_sample VALUES ('SYNTHETIC','fixture-v1','synthetic-sample',"
                          "?,?,?,?,'train/synthetic_depth.mp4',100,200)", (label, signer, split, color))

    def test_empty_initialization_and_integrity(self):
        result = db.check(self.conn)
        self.assertEqual(len(result["tables"]), 15)
        self.assertEqual(result["foreign_key_violations"], 0)
        for table in result["tables"]:
            if table != "schema_migration":
                self.assertEqual(self.conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0], 0)

    def test_migration_rerun_is_noop(self):
        self.assertEqual(db.migrate(self.conn), [])
        self.assertEqual(self.conn.execute("SELECT count(*) FROM schema_migration").fetchone()[0], 1)

    def test_changed_migration_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder)/"001_lexicon.sql"
            file.write_text((db.MIGRATIONS/file.name).read_text()+"\n-- changed\n")
            with self.assertRaisesRegex(RuntimeError, "changed"):
                db.migrate(self.conn, Path(folder))

    def test_failed_migration_rolls_back_schema_and_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder)/"002_broken.sql"
            file.write_text("CREATE TABLE should_not_remain(x INTEGER); INVALID SQL;")
            (Path(folder)/"001_lexicon.sql").write_bytes((db.MIGRATIONS/"001_lexicon.sql").read_bytes())
            with self.assertRaises(sqlite3.Error):
                db.migrate(self.conn, Path(folder))
            self.assertIsNone(self.conn.execute("SELECT name FROM sqlite_master WHERE name='should_not_remain'").fetchone())
            self.assertEqual(self.conn.execute("SELECT count(*) FROM schema_migration").fetchone()[0], 1)

    def test_existing_unversioned_database_refused(self):
        with contextlib.closing(db.connect(":memory:")) as conn:
            conn.execute("CREATE TABLE existing(x INTEGER)")
            with self.assertRaisesRegex(RuntimeError, "unversioned"):
                db.migrate(conn)
            self.assertIsNotNone(conn.execute("SELECT name FROM sqlite_master WHERE name='existing'").fetchone())

    def test_foreign_key_is_enforced(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO sign_equivalent VALUES ('SIGN_9999','örnek')")

    def test_same_gloss_can_have_distinct_sign_ids(self):
        self.sign(); self.sign(9002)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM sign_entry").fetchone()[0], 2)

    def test_sign_id_immutable_and_not_reusable(self):
        sign = self.sign()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE sign_entry SET sign_id='SIGN_9999' WHERE sign_id=?", (sign,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM sign_entry WHERE sign_id=?", (sign,))
        self.conn.execute("UPDATE sign_entry SET is_active=0 WHERE sign_id=?", (sign,))

    def test_turkish_normalization_and_case(self):
        self.assertEqual(db.normalize_turkish("  ilaç ışık  ", uppercase=True), "İLAÇ IŞIK")
        self.assertEqual(db.normalize_turkish("I\u0307LAÇ"), "İLAÇ")
        sign = self.sign(gloss="İLAÇ")
        self.conn.execute("INSERT INTO sign_equivalent VALUES (?,?)", (sign, "ilaç"))
        record = db.export_lexicon(self.conn, development=True)[sign]
        self.assertEqual(record["turkish_equivalents"], ["ilaç"])

    def test_original_dataset_label_is_text(self):
        self.release()
        self.assertEqual(self.conn.execute("SELECT original_label FROM dataset_class").fetchone()[0], "0007")

    def test_valid_paired_video_metadata(self):
        self.release(); self.sample()
        self.assertEqual(self.conn.execute("SELECT count(*) FROM video_sample").fetchone()[0], 1)
        self.assertEqual(db.check(self.conn)["foreign_key_violations"], 0)

    def test_no_unknown_class_or_signer(self):
        self.release()
        for params in ({"label": "missing"}, {"signer": "missing"}):
            with self.subTest(params=params), self.assertRaises(sqlite3.IntegrityError):
                self.sample(**params)

    def test_signer_cannot_leak_into_another_split(self):
        self.release()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO dataset_signer_split VALUES ('SYNTHETIC','fixture-v1','synthetic-signer','test')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.sample(split="test")

    def test_duplicate_sample_rejected(self):
        self.release(); self.sample()
        with self.assertRaises(sqlite3.IntegrityError):
            self.sample()

    def test_absolute_and_traversal_video_paths_rejected(self):
        self.release()
        for path in ("D:/AUTSL/a.mp4", "/data/a.mp4", "../a.mp4", "train/../a.mp4", "train\\a.mp4", "train//a.mp4"):
            with self.subTest(path=path), self.assertRaises(sqlite3.IntegrityError):
                self.sample(color=path)

    def test_raw_video_bytes_rejected_by_strict_schema(self):
        self.release()
        with self.assertRaises(sqlite3.IntegrityError):
            self.sample(color=b"not-a-video-path")

    def test_review_promotion_cannot_skip_source_check(self):
        sign = self.sign(); source = self.source(sign)
        self.conn.execute("INSERT INTO sign_equivalent VALUES (?,?)", (sign, "işaret"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(sign, "expert_reviewed", source, role="native_signer")

    def test_review_requires_source_equivalent_and_same_sign(self):
        sign = self.sign(); source = self.source(sign)
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(sign, "source_checked", source)
        self.conn.execute("INSERT INTO sign_equivalent VALUES (?,?)", (sign, "işaret"))
        other = self.sign(9002); other_source = self.source(other)
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(sign, "source_checked", other_source)
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(sign, "source_checked")

    def test_review_status_requires_append_only_event(self):
        sign = self.sign()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE sign_entry SET review_status='expert_reviewed' WHERE sign_id=?", (sign,))
        self.event(sign, "draft")
        for sql in ("UPDATE review_event SET review_note='changed'", "DELETE FROM review_event"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(sql)

    def test_material_change_requires_recorded_demotion(self):
        sign, source = self.checked_sign()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE sign_entry SET gloss='YENİ' WHERE sign_id=?", (sign,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM sign_equivalent WHERE sign_id=?", (sign,))
        self.event(sign, "draft")
        self.conn.execute("UPDATE sign_entry SET gloss='YENİ' WHERE sign_id=?", (sign,))

    def test_reviewed_source_cannot_be_rewritten(self):
        sign, source = self.checked_sign()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE sign_source SET source_item_ref='changed' WHERE source_id=?", (source,))

    def test_mapping_candidates_and_single_confirmation(self):
        self.release()
        sign, source = self.checked_sign()
        other, other_source = self.checked_sign(9002)
        for s, p in ((sign, source), (other, other_source)):
            self.conn.execute("INSERT INTO dataset_mapping VALUES ('SYNTHETIC','fixture-v1','0007',?,?,'candidate')", (s,p))
        self.conn.execute("UPDATE dataset_mapping SET mapping_status='confirmed' WHERE sign_id=?", (sign,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE dataset_mapping SET mapping_status='confirmed' WHERE sign_id=?", (other,))
        self.event(sign, "draft")
        self.assertEqual(self.conn.execute("SELECT mapping_status FROM dataset_mapping WHERE sign_id=?", (sign,)).fetchone()[0], "candidate")

    def test_unreviewed_mapping_cannot_be_confirmed(self):
        self.release(); sign = self.sign(); source = self.source(sign)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO dataset_mapping VALUES ('SYNTHETIC','fixture-v1','0007',?,?,'confirmed')", (sign,source))

    def test_single_default_clip(self):
        sign = self.sign()
        self.conn.execute("INSERT INTO animation_clip VALUES ('test-a',?,'synthetic/a.glb','draft',1)", (sign,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO animation_clip VALUES ('test-b',?,'synthetic/b.glb','draft',1)", (sign,))
        self.assertIsNone(db.export_lexicon(self.conn, development=True)[sign]["clip_file"])
        self.assertEqual(db.export_lexicon(self.conn), {})

    def test_clip_review_must_belong_to_same_sign(self):
        sign, source = self.checked_sign(); other = self.sign(9002)
        self.conn.execute("INSERT INTO animation_clip VALUES ('test-clip',?,'synthetic/a.glb','draft',1)", (other,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(sign, "source_checked", source, clip="test-clip")

    def test_production_json_gate_and_deterministic_equivalents(self):
        sign = self.sign()
        self.conn.executemany("INSERT INTO sign_equivalent VALUES (?,?)", [(sign,"örnek"),(sign,"işaret")])
        source = self.source(sign)
        self.event(sign,"source_checked",source)
        self.event(sign,"expert_reviewed",source,role="native_signer")
        self.conn.execute("INSERT INTO animation_clip VALUES ('synthetic-clip',?,'synthetic/a.glb','draft',1)", (sign,))
        self.assertEqual(db.export_lexicon(self.conn), {})
        self.event(sign,"source_checked",source,clip="synthetic-clip")
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(sign,"expert_reviewed",source,clip="synthetic-clip")
        self.event(sign,"expert_reviewed",source,clip="synthetic-clip",role="TID_consultant")
        record = db.export_lexicon(self.conn)[sign]
        self.assertEqual(record["clip_file"], "synthetic/a.glb")
        self.assertEqual(record["turkish_equivalents"], ["işaret","örnek"])
        self.event(sign,"draft")
        self.assertEqual(db.export_lexicon(self.conn), {})

    def utterance(self):
        sign = self.sign()
        self.conn.execute("INSERT INTO utterance(utterance_id) VALUES ('synthetic-utterance')")
        self.conn.executemany("INSERT INTO utterance_sign VALUES ('synthetic-utterance',?,?)", [(1,sign),(2,sign),(3,sign)])
        return sign

    def test_nonmanual_span_boundaries_and_contiguous_tokens(self):
        sign = self.utterance()
        for start,end in ((0,3),(3,2),(1,4)):
            with self.subTest(start=start,end=end), self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute("INSERT INTO nonmanual_span(span_id,utterance_id,start_position,end_position,"
                                  "marker_description,function_label) VALUES ('test-span','synthetic-utterance',?,?,'illustrative placeholder','unknown')", (start,end))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO utterance_sign VALUES ('synthetic-utterance',5,?)", (sign,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM utterance_sign WHERE position=2")

    def test_token_edit_invalidates_verified_spans_and_utterance(self):
        self.utterance(); other = self.sign(9002)
        self.conn.execute("INSERT INTO nonmanual_span VALUES ('test-span','synthetic-utterance',1,3,"
                          "'synthetic observation','unknown','verified','synthetic evidence','Synthetic reviewer','2026-11-21')")
        self.conn.execute("UPDATE utterance SET validation_status='verified',evidence_ref='synthetic evidence',"
                          "reviewer_name='Synthetic reviewer',reviewed_on='2026-11-21'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM utterance_sign WHERE position=3")
        self.conn.execute("UPDATE utterance_sign SET sign_id=? WHERE position=2", (other,))
        self.assertEqual(self.conn.execute("SELECT validation_status FROM utterance").fetchone()[0], "illustrative")
        self.assertEqual(self.conn.execute("SELECT validation_status FROM nonmanual_span").fetchone()[0], "illustrative")

    def test_empty_utterance_cannot_be_verified(self):
        self.conn.execute("INSERT INTO utterance(utterance_id) VALUES ('empty')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE utterance SET validation_status='verified',evidence_ref='synthetic evidence',"
                              "reviewer_name='Synthetic reviewer',reviewed_on='2026-11-21'")

    def test_export_rejects_non_normalized_gloss(self):
        self.sign(gloss="ilaç")
        with self.assertRaises(RuntimeError):
            db.export_lexicon(self.conn, development=True)

    def test_cli_end_to_end_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            database = str(Path(folder)/"metadata.sqlite3")
            output = Path(folder)/"lexicon.json"
            self.assertEqual(db.main(["check","--db",database]), 1)
            self.assertFalse(Path(database).exists())
            self.assertEqual(db.main(["init","--db",database]), 0)
            self.assertEqual(db.main(["init","--db",database]), 0)
            self.assertEqual(db.main(["check","--db",database]), 0)
            self.assertEqual(db.main(["export","--db",database,"--out",str(output)]), 0)
            self.assertEqual(json.loads(output.read_text()), {})
            self.assertEqual(db.main(["export","--db",database,"--out",str(output)]), 1)
            self.assertEqual(json.loads(output.read_text()), {})


if __name__ == "__main__":
    unittest.main()
