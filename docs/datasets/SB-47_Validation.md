# SB-47 - Executed validation record

Owner: Ceren Bilgenoğlu. Recorded: 21 November 2026, Türkiye time.

## Environment and scope

Execution environment: Linux, Python 3.12.14, SQLite 3.53.1. Tests ran in memory
and in disposable local files. No connection to Ceren's USB drive, no AUTSL
import, no production database, no participant information and no cloud service
was used. Test references, rights notes and reviewer identities are explicitly
fabricated fixtures, not real approvals or validated sign data.

## Results

| Check actually executed | Result |
| --- | --- |
| `python -m unittest discover -s tests -v` from `backend/db` | 31 tests passed, exit 0 |
| Fresh `db.py init --db <private-test-path>` | `001_lexicon.sql` applied; 14 application tables plus one migration ledger |
| Run `init` again on the same database | No migrations reapplied; existing database retained |
| `db.py check` | `integrity_check: ok`; zero foreign-key violations; foreign keys and recursive triggers enabled |
| Application row counts immediately after initialization | All 14 application tables empty; no dataset rows seeded |
| `db.py export --db ... --out <new-output>` | Exit 0, zero records, valid empty JSON object `{}` |
| Export to an already existing output (behavioral test) | Refused; previous output retained |
| Changed migration and failed-migration paths | Drift rejected; failed migration rolls back its schema changes and ledger entry |
| Invalid data relations | Unknown class/signer references, duplicate samples, signer-split leakage and invalid span endpoints rejected |
| Media/schema boundary | Absolute/traversal video paths and bytes in the TEXT path column rejected; no BLOB columns in the created schema |
| Review/lexicon gates | Event-driven promotions, append-only history, same-sign evidence, demotion before material edits, single confirmed mapping and default clip exercised |
| JSON contract | Turkish Unicode handling, stable-ID keys, deterministic equivalents and recorded expert-review eligibility exercised with synthetic data |

Migration `001_lexicon.sql` SHA-256:

`4df742e51f5bbe14d1c6154a82724f72e34551b4d2cea5cfe02f500dd3cfc0d0`

The test suite and run instructions are included so a teammate can reproduce
these results on the PR head. The branch is now published, but no remote CI result
is claimed here; an earlier publication attempt was blocked by a GitHub 403 error.

## What this does not verify

- Windows/Python installations other than the runtime listed above.
- SQL compatibility with PostgreSQL/MySQL or a deployed multi-user backend.
- Existence, decoding, visual quality or consent/licensing of actual media.
- Actual import of the SB-46 label/mapping files; SB-51 owns that work.
- TİD linguistic correctness, expert identity/qualification or commercial rights.
- An implemented live MediaPipe/recognition/translation pipeline or runtime JSON
  integration in the frontend.
- Retention policy for quick phrases, conversations or participant data.
- Independent teammate review, remote checks, GitHub merge or Jira Done.

## Acceptance-criteria traceability

| Jira criterion | Evidence / delivery state |
| --- | --- |
| AC-1 storage decision and recognition-video handling | Storage decision document, SoW v16 alignment table, files/metadata/JSON separation; choice awaits team review |
| AC-2 SB-14-based gloss, video and split schema | Nine SB-14 tables plus five inventory tables; explicit types/deviations documented |
| AC-3 create-from-scratch script and run instructions | SQL migration, Python runner, README and successful fresh initialization/test run |
| AC-4 raw videos outside database | No media-payload columns/import path; video_sample stores relative paths and metadata only |
| AC-5 exact issue branch, commit and main-targeting PR | Branch `SB-47` published and PR opened targeting `main` on 21 November 2026; review pending (earlier attempt blocked by GitHub 403) |
| AC-6 independent approval, applicable checks and merge | Pending; local tests do not replace teammate approval or remote gates |
| AC-7 Confluence/Jira evidence | Progress and artifact links tracked in the SB-47 Confluence summary/Jira comment; these do not imply Done |

No authoritative SoW, previous source design or task acceptance criterion was
edited while implementing this component.
