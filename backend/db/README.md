# SB-47 - Lexicon and dataset metadata database

[Jira SB-47](https://el-dili.atlassian.net/browse/SB-47) ·
[Storage decision and SoW/SB-14 traceability](../../docs/datasets/SB-47_Storage_and_Schema.md)

Owner: Ceren Bilgenoğlu. Implementation prepared for independent review.

This component creates a **local SQLite metadata database** and exports the
**JSON lexicon required by the SoW**. It is not a running backend service and does
not replace the browser's JSON contract. It does not download, copy, upload or
decode videos, run MediaPipe, import AUTSL, record conversations or save quick
phrases. Real metadata import is SB-51.

## Requirements

- Python 3.10 or later with its standard-library `sqlite3` module.
- Linked SQLite 3.37.0 or later, required by `STRICT` tables. The runner checks it.
- No pip packages, database server, Docker container or administrator privileges.
- Tested here: Python 3.12.14 / SQLite 3.53.1 on Linux. Windows execution has not
  been performed in this environment; the PowerShell commands below are provided
  for Ceren's machine. This does not claim testing every supported runtime.

Run all commands from the repository root. Keep the working database and exports
outside the checkout. Replace the example private directory if needed.

### Windows PowerShell

```powershell
py -3 -c "import sqlite3; print(sqlite3.sqlite_version)"
py -3 backend/db/db.py init --db "$env:USERPROFILE\SignBridge-private\metadata.sqlite3"
py -3 backend/db/db.py check --db "$env:USERPROFILE\SignBridge-private\metadata.sqlite3"
py -3 backend/db/db.py export --db "$env:USERPROFILE\SignBridge-private\metadata.sqlite3" --out "$env:USERPROFILE\SignBridge-private\lexicon.json"
```

If `py` is unavailable but Python is installed, substitute `python` for `py -3`.
The initial database has **zero application rows**, so its initial JSON export is
`{}`. That demonstrates the export path, not a completed vocabulary or library.

### Linux/macOS

```bash
python3 backend/db/db.py init --db "$HOME/SignBridge-private/metadata.sqlite3"
python3 backend/db/db.py check --db "$HOME/SignBridge-private/metadata.sqlite3"
python3 backend/db/db.py export --db "$HOME/SignBridge-private/metadata.sqlite3" --out "$HOME/SignBridge-private/lexicon.json"
```

`init` creates the database if absent and applies checksum-tracked migrations in
filename order, atomically per migration. Running it again is a no-op when the
migrations are unchanged. Edited/missing applied migrations and unversioned
nonempty databases are rejected. Add a new migration for later changes; do not
edit an applied migration. The runner does not drop existing data and provides no
destructive reset command. Back up an existing private database before upgrading.

`check` runs the migration-ledger comparison, SQLite `integrity_check` and
`foreign_key_check`. It does not test video existence, decoding, semantic mapping,
linguistic quality, review credentials or usage rights.

`export` refuses to overwrite an existing output; select a new filename for the
next version. Normal export includes only active expert-reviewed signs with at
least one Turkish equivalent and one default expert-reviewed clip. The index
prevents two defaults. Production gating here means recorded metadata meets the
gate; it is not independent evidence of expert qualification or asset correctness.

`--development` explicitly includes draft records; ineligible `clip_file` is
`null`. Never ship a development export as validated vocabulary. IDs key the JSON
object because a gloss can name multiple variants/senses. Equivalent lists are
deterministically sorted before clips are selected; rows are not multiplied by a
join. Output preserves Turkish Unicode characters.

## Run behavioral checks

```powershell
Push-Location backend/db
py -3 -m unittest discover -s tests -v
Pop-Location
```

```bash
cd backend/db
python3 -m unittest discover -s tests -v
```

Tests use fabricated dataset IDs, paths, evidence and reviewer names in temporary
databases. They make no network requests and require no AUTSL files or passwords.
They are not actual expert reviews, licence decisions or training examples.

## Schema and connection contract

`migrations/001_lexicon.sql` creates all nine SB-14 logical tables and five
dataset/sample tables; the runner adds `schema_migration`.

| Area | Tables |
| --- | --- |
| Lexicon | `sign_entry`, `sign_equivalent`, `sign_source` |
| Mappings and clips | `dataset_mapping`, `animation_clip`, `review_event` |
| Curated research examples | `utterance`, `utterance_sign`, `nonmanual_span` |
| Dataset inventory | `dataset_release`, `dataset_class`, `dataset_split`, `dataset_signer_split`, `video_sample` |

Every application connection must use `db.connect(...)`, which enables
`PRAGMA foreign_keys=ON` and `PRAGMA recursive_triggers=ON`. If another client runs
SQL directly, it must enable both pragmas **before** starting its transaction.
These are integrity safeguards for trusted local tooling, not authentication or
protection from a database owner who can change schema/pragmas.

Use parameterized statements for imports. Normalize Turkish lexical text with
`db.normalize_turkish(...)`; pass `uppercase=True` for gloss labels. Never use
SQLite's default case folding as Turkish-aware matching. Original dataset labels
are opaque TEXT and must not be normalized, translated or inferred from names.
The export checks NFC and Turkish uppercase; SQL alone does not enforce Unicode
NFC or Turkish casing on every insert.

### Review workflow

New signs/clips start as `draft`. Insert an accountable `review_event` to change a
state; its trigger updates the target in the same statement/transaction.
`draft -> source_checked` requires checked, specific same-sign source evidence;
signs also require a Turkish equivalent. `source_checked -> expert_reviewed`
additionally requires a `TID_consultant` or `native_signer` role. Roles and names
are recorded declarations; access control and verification of the real person's
qualification remain outside this database component.

Material sign/clip/equivalent edits require a recorded demotion to `draft` first.
Review events are append-only. Reusing sign IDs is prevented by retaining signs
and retiring them with `is_active=0`. Sign demotion changes confirmed mappings back
to candidates. Reference records already cited in reviews cannot be rewritten;
add a new source record. A candidate mapping is not a confirmed semantic match.
Confirmation requires a source-checked sign and recorded rights assessment;
source-checked is still not equivalent to expert-reviewed.

Utterance tokens are appended contiguously from position 1; remove them from the
end. Span endpoints reference tokens in the same utterance and may overlap.
Token changes invalidate utterance/span verification. Rebuilding order requires
first removing spans and rebuilding the illustrative sequence. Verified examples
require actual evidence, reviewer/date and at least one token. These tables are
for curated examples, not automatic storage of user conversations.

## SB-51 import boundary

1. Confirm this storage choice and the SB-47 PR in team review before integrating.
2. Create a named `dataset_release` with a pinned, documented version and usage
   conditions. A team-defined snapshot ID is allowed if identified explicitly as
   local, not misrepresented as a provider's version. Do not use `latest`/`unknown`.
3. Load provider class metadata separately from curated `sign_entry` records.
   An AUTSL class ID is not a `SIGN_...` ID; a matching name is not confirmation.
4. Create `train`, `validation` and `test` split records and one signer assignment
   per release. One signer ID cannot be assigned to two splits in that release.
5. Import one `video_sample` row per paired color/depth sample, preserving the
   provider sample ID and opaque original class label. Paths are forward-slash
   relative paths such as `val/<sample_id>_color.mp4` under that release's private
   media root. The normalized split name is `validation`, while the observed
   folder is `val`. Do not hardcode a USB drive letter into the schema.
   Cataloguing supplied depth files does not add a runtime depth-camera input
   or change the SoW's RGB-only capture scope.
6. Keep a private mapping from release IDs to absolute media roots. A future
   MediaPipe loader resolves and checks files there; this component is not that
   loader. SQL path checks do not replace filesystem containment/symlink checks.
7. Retain provider splits and original labels; use the training/validation data
   for vocabulary decisions. Test labels must not drive model/coverage selection.

The SB-46 evidence reports 28,142 / 4,418 / 3,742 samples and 226 classes in each
split for the balanced-test ChaLearn release. These figures are handoff metadata,
not seeded application rows. They do not prove that every class has a curated or
expert-reviewed lexicon entry. SB-51 must run its own import reconciliation.

Database files, raw/derived datasets, credentials, full provider label/mapping
exports and generated private JSON exports stay out of the repository. The
committed component consists only of SQL, Python, tests and documentation.
