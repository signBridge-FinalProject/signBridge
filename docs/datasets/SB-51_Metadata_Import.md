# SB-51 - Dataset Label and Metadata Import

**Jira:** [SB-51](https://el-dili.atlassian.net/browse/SB-51)
**Recorded:** 27 November 2026, Türkiye time
**Status:** Import script, example queries, tests and this record prepared and validated locally on fabricated files. The real AUTSL import and the comparison with the SB-46 counts move to a follow-up issue in the next sprint. Team review, checks and merge pending.

## 1. Purpose and scope

SB-51 loads dataset class metadata, sample labels and split/signer information into the SB-47 SQLite schema, following the seven rules of the [SB-51 import boundary](../../backend/db/README.md#sb-51-import-boundary) in the SB-47 README.

**Scope change.** The official AUTSL download links returned HTTP 404 as of 27 November 2026, and the author of this change has no local copy of the data. With the team lead's approval, the real AUTSL import and its reconciliation against the SB-46 counts move to **a follow-up issue in the next sprint**. This issue delivers the import script, the tests, the example queries and a validation on fabricated files in the SB-46 format. No dataset was downloaded or fetched for this work.

Delivered:

- [`backend/db/import_dataset.py`](../../backend/db/import_dataset.py): import script (Python standard library only)
- [`backend/db/queries/dataset_examples.sql`](../../backend/db/queries/dataset_examples.sql): example queries
- [`backend/db/tests/test_import_dataset.py`](../../backend/db/tests/test_import_dataset.py): behavioral tests on fabricated files
- `.gitignore` entries for SQLite database files at the repository root
- a short pointer paragraph at the end of the README's SB-51 import boundary section

Not changed: `001_lexicon.sql` and `db.py`. The import uses `db.connect`, `db.migrate` and `db.check` as they are.

Out of scope: the real AUTSL import, reconciliation with the SB-46 figures, mapping dataset classes to curated signs, media decoding and MediaPipe extraction.

## 2. Input formats

The script reads the file formats recorded in [SB-46](SB-46_AUTSL_Verification.md):

| Input | Format | Import rule |
|---|---|---|
| Class mapping | CSV with header `ClassId,TR,EN` | One `dataset_class` row per ClassId. `original_label` = ClassId text, stored as opaque text (`007` stays `007`). `name_tr` / `name_en` stored exactly as in the file; no translation, case change or correction. An empty name is stored as NULL |
| Labels, one file per split | Headerless CSV `sample_id,class_id` | `sample_id` must match `signerX_sampleY`. `signer_id` = the part before the first `_` (`signer12_sample5` -> `signer12`) |

Split names, folders and the SB-46 label files:

| Normalised split | Media folder | SB-46 label file |
|---|---|---|
| `train` | `train` | `train_labels.csv` |
| `validation` | `val` | `ground_truth.csv` (validation) |
| `test` | `test` | `ground_truth.csv` (test) |

**Path rule.** Each sample is one color/depth pair. Paths are relative, use forward slashes and resolve under the release's private media root: `<folder>/<sample_id>_color.mp4` and `<folder>/<sample_id>_depth.mp4`, for example `val/signer902_sample1_color.mp4`. No absolute path, drive letter or backslash is stored. The SB-47 schema checks enforce this too.

Leading and trailing whitespace is trimmed from `sample_id`, `class_id` and `ClassId` cells; class names are not trimmed.

## 3. Setup and commands

Requirements are the same as SB-47: Python 3.10 or later with `sqlite3`, SQLite 3.37 or later, no pip packages. Keep the database and the report **outside the repository**. The script refuses (exit code 2) a `--db` or `--report` path that is inside the git checkout and not gitignored.

Arguments:

| Argument | Meaning |
|---|---|
| `--db` | Required. Private SQLite file; created and migrated with `db.migrate` if absent |
| `--dataset-name` | Default `AUTSL` |
| `--dataset-version` | Required. `latest`, `unknown` and `tbd` (any case) are rejected |
| `--local-snapshot` | Declares the version as a team-defined local snapshot ID. The release description then states that it is not a provider-issued version (README rule 2) |
| `--description`, `--source-reference`, `--usage-conditions` | `dataset_release` fields. Defaults exist; the usage default summarises the SB-16/SB-46 conditions (academic, non-commercial use; citation; no redistribution without explicit permission) |
| `--mapping` | Class mapping CSV (`ClassId,TR,EN`) |
| `--labels` | `train=PATH validation=PATH test=PATH`; at least one split |
| `--media-root` | Optional. Checks each color/depth file under the root and records byte sizes; without it, sizes stay NULL |
| `--expect` | Optional expected counts, e.g. `train=28142,validation=4418,test=3742,classes=226,signers=43`. Also accepted: `samples`, `<split>_signers`, `<split>_classes` |
| `--report` | Optional JSON report path |

### macOS / Linux

```bash
cd backend/db && python3 -m unittest discover -s tests -v && cd ../..

python3 backend/db/import_dataset.py \
    --db "$HOME/SignBridge-private/metadata.sqlite3" \
    --dataset-version <pinned-version-or-local-snapshot-id> \
    --mapping /private/path/class-id-sign-mapping.csv \
    --labels train=/private/path/train_labels.csv \
    --report "$HOME/SignBridge-private/sb51_report.json"
```

### Windows PowerShell

```powershell
Push-Location backend/db
py -3 -m unittest discover -s tests -v
Pop-Location

py -3 backend/db/import_dataset.py `
    --db "$env:USERPROFILE\SignBridge-private\metadata.sqlite3" `
    --dataset-version <pinned-version-or-local-snapshot-id> `
    --mapping "D:\private\class-id-sign-mapping.csv" `
    --labels "train=D:\private\train_labels.csv" `
    --report "$env:USERPROFILE\SignBridge-private\sb51_report.json"
```

If `py` is unavailable, use `python` instead of `py -3`.

### Prepared command for the follow-up issue

Using the SB-46 verification-machine layout (adjust the paths and choose the version or snapshot ID in the follow-up; `<snapshot-id>` is deliberately left open):

```powershell
py -3 backend/db/import_dataset.py `
    --db "$env:USERPROFILE\SignBridge-private\metadata.sqlite3" `
    --dataset-name AUTSL --dataset-version <snapshot-id> --local-snapshot `
    --mapping "D:\AUTSL\class-id-sign-mapping.csv" `
    --labels "train=D:\AUTSL\train\train_labels.csv" `
             "validation=D:\AUTSL\labels\validation\ground_truth.csv" `
             "test=D:\AUTSL\labels\test\ground_truth.csv" `
    --media-root "D:\AUTSL\extracted" `
    --expect "train=28142,validation=4418,test=3742,classes=226,signers=43" `
    --report "$env:USERPROFILE\SignBridge-private\sb51_autsl_report.json"
```

The release-to-media-root mapping stays private (README rule 6). Only relative paths enter the database.

## 4. Re-runs, errors and rollback

**Transaction.** All dataset rows are written in one `BEGIN IMMEDIATE` transaction. On any error the transaction is rolled back and no dataset row is written. On a new database file, `db.migrate` runs first and commits the empty schema, so the file can exist with zero dataset rows after a failed first import.

**Re-run (AC-1).** Each row is looked up by its primary key before insert:

- identical row: counted as `unchanged`; nothing is written
- absent row: inserted
- existing row with different content (for example the same `sample_id` with another `class_id`, a changed class name or a signer moved to another split): **not overwritten**. Every difference is listed (`table [key] column: database=..., input=...`), the import fails and the whole transaction is rolled back

Byte sizes are compared only when `--media-root` is given. A run with `--media-root` on a database imported without it reports the NULL-to-size change as a difference instead of updating it silently.

**Input errors** (exit code 1, nothing written):

- mapping without the `ClassId,TR,EN` header, duplicate or empty ClassId, rows without 3 columns
- label row without exactly 2 columns, header row in a label file, `sample_id` not in `signerX_sampleY` form
- class ID not in the mapping, duplicate `sample_id` (in one file or across splits)
- one signer in two splits (in the input or against rows already in the database)
- `latest` / `unknown` / `tbd` version, malformed `--labels` or `--expect`

**Boundary (README rule 3).** The script never writes `dataset_mapping` or `sign_entry`. A provider class ID is not a curated sign ID, and a matching name is not a confirmed mapping.

**Exit codes:** 0 = imported and all counts match; 1 = error, rolled back; 2 = refused output path; 3 = imported, but a count difference or a media problem was reported.

## 5. Count reconciliation and report (AC-2)

After the inserts and before commit, the script compares the counts read from the input files with the database row counts for this release:

| Level | Metrics |
|---|---|
| Per split (each split given in `--labels`) | samples, signers, distinct classes used |
| Total | samples, signers, classes (rows in `dataset_class`) |

If `--expect` is given, each expected value is also compared with the database count. An expectation for a split not given in `--labels` is reported as a difference. Every compared value is printed with `match` or `DIFFERENCE`; any difference gives exit code 3. Database rows of a split that are no longer in the input file show up as a database count higher than the file count.

With `--media-root`, missing files, zero-byte files and paths that resolve outside the media root are listed as media issues (the byte size stays NULL) and also give exit code 3.

`db.check` runs after the commit (migration ledger, `integrity_check`, `foreign_key_check`), and its result is included in the report.

JSON report fields: `tool`, `issue`, `run_at`, `dataset_name`, `dataset_version`, `local_snapshot`, `inputs` (file names and SHA-256 of the mapping and label files, whether media was checked), `migrations_applied`, `rows` (inserted/unchanged per table), `file_counts`, `database_counts`, `expected`, `comparison`, `differences`, `media_issues`, `check`, `status`, `exit_code`. On failure: `status: failed`, `error`, `error_details`.

The verified SB-46 figures (train 28,142, validation 4,418, test 3,742, 226 classes, 43 signers) are **not** checked in this issue. They will be passed with `--expect` in the follow-up issue.

## 6. Example queries (AC-3)

[`backend/db/queries/dataset_examples.sql`](../../backend/db/queries/dataset_examples.sql) holds six queries. Each is scoped to one release through `:dataset_name` and `:dataset_version` and starts with a `-- name:` line and a comment explaining it.

| Query | Returns |
|---|---|
| `samples_per_split` | Sample count per split |
| `samples_per_class_and_split` | Sample count per class and split, with the provider's TR and EN names |
| `signers_per_split` | Signer count and comma-separated signer list per split |
| `classes_with_fewest_train_samples` | The ten classes with the fewest training samples, including classes with none |
| `sample_lookup` | Class, names, signer, split, paths and byte sizes of one `:sample_id` |
| `samples_per_signer` | Sample count per signer, with the signer's split |

Output on the **fabricated** end-to-end database of Section 7. These are invented classes, signers and samples, not AUTSL data:

```
samples_per_split: train 5 | validation 2 | test 1
samples_per_class_and_split:
  0 örnek example  train 3 / test 1
  1 ışık  light    train 1 / validation 1
  2 Çiçek flower   train 1 / validation 1
signers_per_split: train 2 (signer900,signer901) | validation 1 (signer902) | test 1 (signer903)
classes_with_fewest_train_samples: 3 şeker 0 | 1 ışık 1 | 2 Çiçek 1 | 0 örnek 3
sample_lookup (signer902_sample2): class 2, Çiçek / flower, signer902, validation,
  val/signer902_sample2_color.mp4, val/signer902_sample2_depth.mp4, bytes NULL / NULL
samples_per_signer: signer900 train 3 | signer901 train 2 | signer902 validation 2 | signer903 test 1
```

The test suite runs every query on a fabricated database and checks these exact results.

## 7. Validation on fabricated files

Environment: macOS (arm64), Python 3.11.4, SQLite 3.42.0. All inputs were fabricated, all files were created in temporary folders outside the repository, and no AUTSL file, label or mapping was used. **None of the counts below are real dataset counts.**

**Tests.** `python3 -m unittest discover -s tests -v` in `backend/db`: **53 tests, all passed** (the 31 existing SB-47 tests and 22 new SB-51 tests). The new tests cover:

- first import (release, classes, splits, signer-split, samples, paths, report)
- a second run adding no rows
- local snapshot declaration and opaque labels
- a changed class or class name for an existing row being reported and rolled back
- invalid inputs writing nothing (unknown class, duplicate sample, header row, malformed row, bad sample ID, mapping header and duplicates)
- a sample or signer in two splits, including against existing rows
- rejection of `latest`/`unknown`/`TBD` versions
- count matches, `--expect` mismatches and database rows missing from the input
- `--media-root` sizes and missing or zero-byte files
- example query results
- no `dataset_mapping` or `sign_entry` rows
- the repository guard

**End-to-end CLI run.** Fabricated inputs: a mapping with 4 classes (0-3) and three label files with 5 / 2 / 1 samples from signers `signer900`-`signer903`. Version `fixture-2026-11-27` with `--local-snapshot`.

| Run | Result | Rows after run (release / class / split / signer-split / sample) | Exit |
|---|---|---|---|
| 1. First import | 1 / 4 / 3 / 4 / 8 inserted; all 12 comparisons `match`; `db.check` integrity ok, 0 FK violations | 1 / 4 / 3 / 4 / 8 | 0 |
| 2. Same inputs again | 0 inserted, all rows `unchanged`; all comparisons `match` | 1 / 4 / 3 / 4 / 8 | 0 |
| 3. `--expect train=6,validation=2,test=1,classes=4,signers=4` (train intentionally wrong) | `train samples files=5 database=5 expected=6 DIFFERENCE`; other values `match`; status `imported_with_differences` | 1 / 4 / 3 / 4 / 8 | 3 |
| 4. `--db` in a non-ignored repository folder (`docs/`) | Refused before creating any file | - | 2 |

`dataset_mapping` and `sign_entry` stayed at 0 rows in every run.

Note on run 4: the first guard attempt used `backend/db/guard_test.sqlite3`. That path is ignored by the existing `backend/db/.gitignore` (`*.sqlite3`), so the guard correctly allowed it and the fabricated database was created there. It was deleted immediately and the guard was re-run with a non-ignored path, which was refused as shown.

## 8. Data handling rules (AC-4)

- Database files, label and mapping CSVs, JSON reports and credentials do not enter the repository (SB-16 commitments; [SB-46](SB-46_AUTSL_Verification.md) handling conditions; [SB-47](SB-47_Storage_and_Schema.md) storage boundary).
- The root `.gitignore` now ignores `*.sqlite3`, `*.sqlite`, `*.db` and their journal/WAL files. `backend/db/.gitignore` already did the same for that folder.
- The script refuses database and report paths inside the checkout unless they are gitignored. Reports from real data contain input file names and digests; keep them private as well.
- Tests and the validation above use fabricated files only.
- This change contains SQL, Python, tests, `.gitignore` entries and documentation. It contains no database file, real CSV, report or password.

## 9. Acceptance criteria and delivery state

| Criterion | Status | Evidence / remaining action |
|---|---|---|
| AC-1: An import script loads class mapping, sample list and split information (in the SB-46 file format) into the schema and can be re-run without creating duplicates; validated on fabricated files. | Prepared | `import_dataset.py` (Sections 2-4); re-run with no new rows and conflict rollback shown in tests and end-to-end runs 1-2 (Section 7) |
| AC-2: The script compares database row counts with the counts read from the input files and reports any difference; demonstrated on fabricated files. Reconciliation against the verified SB-46 counts is done in a follow-up issue (next sprint). | Prepared | Section 5; end-to-end run 3 and tests (Section 7). SB-46 reconciliation is in the follow-up issue, with the command prepared in Section 3 |
| AC-3: Document a few example queries (for instance samples per class and per split). | Prepared | Six queries in `dataset_examples.sql`, tested; fabricated output in Section 6 |
| AC-4: No dataset files or credentials are committed. | Prepared | Section 8; `.gitignore` and the runtime guard. Check the staged diff again before committing |
| AC-5: Deliverable committed on the branch named exactly as this issue key, with issue-referencing commits and a PR targeting main. | Pending | Done separately on GitHub |
| AC-6: Independent teammate approval, applicable passing checks and merge are complete. | Pending | Done separately on GitHub |
| AC-7: Relevant Confluence record and Jira evidence links are updated. | Pending | Done separately on Confluence and Jira |

## 10. Sources

1. [SB-46 AUTSL verification](SB-46_AUTSL_Verification.md): file formats, split/folder correspondence, verified counts, handling conditions.
2. [SB-47 storage and schema](SB-47_Storage_and_Schema.md), [SB-47 validation record](SB-47_Validation.md) and [backend/db/README.md](../../backend/db/README.md) (SB-51 import boundary).
3. [SB-16 AUTSL access request](SB-16_AUTSL_Access_Request.md): academic, non-commercial use and no redistribution without permission.
4. [SB-34 schedule](../sow/SB-34.md), row D10: post-SoW feasibility work, Sprint 4.
5. [Sprint 3 Review advisor feedback](https://el-dili.atlassian.net/wiki/spaces/SIGNBRIDGE/pages/23134209): a database is not required for training-only data; dependent-work guidance (as summarised in SB-47).
