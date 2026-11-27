# SB-50 - MediaPipe Landmark Extraction Pipeline

**Jira:** [SB-50](https://el-dili.atlassian.net/browse/SB-50)
**Recorded:** 27 November 2026, Türkiye time
**Status:** Pipeline, output format, tests and this record prepared and run locally on two development clips. Running on AUTSL is moved to a follow-up issue in the next sprint. Team review, checks and merge pending.

## 1. Purpose and scope

SB-50 builds the batch step that turns sign videos into MediaPipe Holistic landmark files for offline training. It reuses the SB-15 per-frame layout ([MEDIAPIPE_EVAL.md](../MEDIAPIPE_EVAL.md), Sections 2-3) and adds what a batch needs: deterministic video selection, one `.npz` per video with a presence mask and metadata, a per-video report, a run summary and failure handling that does not stop the batch.

**Scope change.** The issue originally asked for a run on an AUTSL data sample; its title and AC-1/AC-4 were updated after the scope change. The official AUTSL download links returned HTTP 404 as of 27 November 2026, and the author of this change has no local copy of the data. By team decision, this issue therefore delivers the pipeline, the format, the tests and this document. The AUTSL run moves to a follow-up issue in the next sprint. No dataset was downloaded or fetched for this work.

In scope:

- `ml/eval/extract_landmarks.py` (batch pipeline) and `ml/eval/landmark_layout.py` (layout shared with SB-15)
- `ml/eval/tests/test_extract_landmarks.py` (pytest, fabricated data only)
- `.gitignore` entries for extraction outputs and local video folders
- a development run on two non-AUTSL clips and one intentionally corrupted file (Section 7)

Out of scope: AUTSL extraction, landmark quality measurement, gap interpolation, normalisation, resampling, model training and any recognition accuracy claim.

## 2. Environment and pinned versions

Same pins as SB-15 (`ml/eval/requirements.txt`, unchanged):

| Package | Pinned | Reported at runtime |
|---|---|---|
| Python | 3.11.4 | 3.11.4 |
| mediapipe | 0.10.9 | 0.10.9 |
| opencv-python | 5.0.0.93 | `cv2.__version__` = 5.1.0 |
| numpy | 2.4.6 | 2.4.6 |
| protobuf | 3.20.3 | - |

The OpenCV wheel `opencv-python==5.0.0.93` reports `5.1.0` as `cv2.__version__`. The `.npz` metadata stores the runtime value. The only new dependency is `pytest==8.3.4`, used only for tests and listed in `ml/eval/requirements-dev.txt`.

Machine for the development run: macOS, Apple M1 (arm64), CPU/XNNPACK.

## 3. Setup and commands

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r ml/eval/requirements-dev.txt

# tests (no video, no mediapipe call)
.venv/bin/python -m pytest ml/eval/tests -v

# generic run
.venv/bin/python ml/eval/extract_landmarks.py \
    --videos /path/outside/repo/videos --out /path/outside/repo/landmarks_out
```

Prepared command for the AUTSL follow-up (run from the folder that holds the private label file, or give its full path):

```bash
.venv/bin/python ml/eval/extract_landmarks.py \
    --videos /private/AUTSL/extracted/val \
    --glob "*_color.mp4" \
    --labels ground_truth.csv \
    --split val \
    --limit 30 \
    --out /private/AUTSL/landmarks_out/val_first30 \
    --report /private/AUTSL/landmarks_out/val_first30/report.csv
```

Arguments:

| Argument | Meaning |
|---|---|
| `--videos DIR [DIR ...]` | Required. One or more video folders, searched non-recursively |
| `--glob` | File pattern, default `*.mp4`. Use `*_color.mp4` for AUTSL RGB videos |
| `--labels` | Optional headerless `sample_id,class_id` CSV (SB-46 format) |
| `--split` | Optional tag stored in metadata: `train`, `val` or `dev` |
| `--out` | Required. Folder for `.npz` files and `run_summary.json` |
| `--limit N` | Process only the first N videos after sorting |
| `--report` | Report CSV path, default `<out>/report.csv` |

**Label matching.** The sample ID is the file name without the extension and without a trailing `_color` or `_depth`. For example, `signer0_sample1_color.mp4` becomes `signer0_sample1`, which is the SB-46 label key. A video with no label row gets `class_id = null` (an empty cell in the report). A label file with a header row, a duplicate sample ID or a row without exactly two columns is rejected.

**Repository guard.** Before writing anything, the script checks whether `--out` or `--report` lies inside a git repository. If it does and the path is not gitignored (checked with the read-only `git check-ignore`), the script prints a warning and exits with code 2 without creating any file. Gitignored folders such as `landmarks_out/` and `data/local/` are accepted.

## 4. Output format

### Per-video `.npz`

File name: `<video stem>.npz` in `--out`, written with `numpy.savez_compressed`. It can be read with `np.load(path, allow_pickle=False)`.

| Key | dtype | Shape | Content |
|---|---|---|---|
| `keypoints` | float32 | `[T, 1662]` | Per-frame vector in the SB-15 order: pose (33x4), face (468x3), left_hand (21x3), right_hand (21x3) |
| `mask` | uint8 | `[T, 4]` | 1 if the group was detected in that frame, 0 if not. Column order: pose, face, left_hand, right_hand |
| `meta` | str (0-d) | - | JSON string, fields below |

`T` is the number of decoded frames. No resampling is done.

**Missing groups.** A group that Holistic did not detect is filled with zeros and gets `mask = 0`. **No interpolation is done in this step.** The gap rule of [MEDIAPIPE_EVAL.md](../MEDIAPIPE_EVAL.md) Section 6 (interpolate gaps of up to 5 frames, zero-fill longer gaps, mask) belongs to the later preprocessing step. Keeping raw detections plus the mask here lets preprocessing apply or change that rule without re-running MediaPipe. Note that in the Section 6 rule an interpolated group has mask 1; in these raw files, mask 1 always means "detected by Holistic".

`meta` fields:

| Field | Content |
|---|---|
| `video`, `sample_id` | Source file name and derived sample ID |
| `class_id` | Integer from `--labels`, or `null` |
| `split` | `--split` value, or `null` |
| `source_fps`, `frame_count`, `frame_count_reported`, `width`, `height` | From OpenCV. `frame_count` is the decoded count (= `T`); `frame_count_reported` is the container value |
| `layout_name` | `legacy_holistic_543` |
| `concat_order`, `mask_order` | `["pose", "face", "left_hand", "right_hand"]` |
| `vector_size` | 1662 |
| `groups` | Per group: `landmarks`, `fields`, `values` (pose 33 / x,y,z,visibility / 132; face 468 / x,y,z / 1404; each hand 21 / x,y,z / 63) |
| `missing_fill` | Text description of the zero-fill/mask rule |
| `holistic_settings` | `static_image_mode=false`, `model_complexity=1`, `smooth_landmarks=true`, `refine_face_landmarks=false` |
| `versions` | python, mediapipe, opencv, numpy at runtime |
| `created_at` | UTC ISO-8601 timestamp |

A new Holistic instance is created for each video, so tracking and smoothing state never carries over between samples.

### Report CSV (one row per video)

`video, sample_id, class_id, status, error, frames, duration_s, processing_s, processing_fps, missing_pct_pose, missing_pct_face, missing_pct_left_hand, missing_pct_right_hand`

- `status` is `ok` or `failed`. For failed videos, `error` holds the reason and the numeric columns are empty.
- `duration_s` = frames / source FPS.
- `processing_s` times decode and Holistic inference only (as in SB-15). Model creation and `.npz` writing are excluded.
- `missing_pct_<group>` = percentage of frames with mask 0.

### Run summary

Printed to the console and written to `<out>/run_summary.json`: total, succeeded and failed video counts, names of failed videos, unlabelled count, total wall-clock time of the batch (including model creation and file writing), mean and median processing FPS over successful videos, the selection rule, the command line, versions and Holistic settings.

### Failure handling

A video that cannot be opened, that decodes zero frames, or that raises any exception is recorded as `failed` with the error message. No `.npz` is written for it, and the batch continues with the next video.

### Reproducibility

- Versions are pinned (Section 2) and stored in every `.npz` and in the run summary.
- Selection is deterministic: non-recursive glob in each `--videos` folder, sort by file name (Python code-point order, full path as tie-breaker), keep the first N. The rule text is written to the summary.
- The exact command is stored in `run_summary.json`.
- Holistic settings are fixed in code and stored in the metadata.

## 5. Landmark layout and open question (AC-2)

This pipeline uses **legacy MediaPipe Holistic** (`mp.solutions.holistic`) with `refine_face_landmarks=False`: 33 + 468 + 21 + 21 = **543 landmarks, 1662 values per frame**, the SB-15 standard.

"553 landmarks" can come from two different sources:

1. **Legacy Holistic with `refine_face_landmarks=True`.** The face mesh adds 10 iris landmarks (468 -> 478), giving 33 + 478 + 21 + 21 = 553. The result structure stays the same; only the face group grows.
2. **MediaPipe Tasks Holistic Landmarker.** It also returns 553 landmarks (478-point face), but through a different API and result structure (separate landmark lists per group plus optional outputs such as world landmarks and face blendshapes), and it is a different model package.

Which layout to use is an **open team decision**. Whatever is chosen must be the same in training and in the browser (SB-8 pipeline note; [SB-18 Feedback Matrix](../SB-18_Instructor_Feedback_Matrix.md) item D-7, "Before landmark extraction"). **SB-50 does not make this choice; it only flags it.** Every `.npz` stores `layout_name` (`legacy_holistic_543`) and the per-group counts, so files from a later layout can be told apart and a switch only needs a new `GROUPS` definition and layout name. D-7 should be decided before the full AUTSL extraction in the follow-up issue.

## 6. Code structure and tests

- `ml/eval/landmark_layout.py`: `GROUPS`, `group_array` and `flatten_frame`, moved unchanged from `mediapipe_eval.py`. It depends on numpy only. `mediapipe_eval.py` now imports them from here; its behaviour and the SB-15 numbers in MEDIAPIPE_EVAL.md are unchanged. After the move, the SB-15 script was re-run on one development clip and printed the same structure (1662 values; visibility set for pose only).
- `ml/eval/extract_landmarks.py`: the helper functions (selection, label CSV, flatten/mask, metadata, `.npz` I/O, report, summary, repository guard) import without mediapipe or OpenCV. These are imported only inside `process_video` and `library_versions`.

Tests use fabricated arrays, fabricated `signer900_sampleN` IDs and small CSVs written to a temporary folder. No real video, AUTSL label file or mapping is used. They cover:

- flatten always gives 1662 float32 values in the SB-15 order; missing groups are zero-filled and get mask 0
- headerless label CSV reading; header, duplicate and malformed rows rejected; `signerX_sampleY_color.mp4` -> `signerX_sampleY`; unlabelled video -> `null`
- deterministic sorted selection and `--limit`
- report rows and columns, and summary counts including a failed video
- `.npz` write/read round trip: shapes, dtypes, mask and metadata fields
- repository guard decision, and that a failure inside `process_video` is returned as `failed` instead of raised

Result on 27 November 2026 (Python 3.11.4, macOS arm64): **24 passed**.

## 7. Development run (AC-3 / AC-4)

**These clips are not AUTSL.** They are two clips from the Güncel TİD Sözlüğü (tidsozluk.aile.gov.tr), used only to exercise the pipeline end to end. They were kept outside the repository and were not committed.

| Clip | Resolution | Source FPS | Frames | Duration |
|---|---|---|---|---|
| `630-02_cr_0.1.mp4` | 162x108 | 25 | 50 | 2.0 s |
| `711-01_cr_0.1.mp4` | 162x108 | 25 | 63 | 2.5 s |

A third file, `zz_corrupt_intentional.mp4` (64 random bytes), was created in a temporary folder outside the repository. It is an **intentional failure test** for the error reporting, not a real video.

Command (output folder outside the repository; no label file, so `class_id` is null):

```bash
.venv/bin/python ml/eval/extract_landmarks.py \
    --videos <sb50_dev folder> <temporary corrupt-file folder> \
    --out <sb50_out folder outside the repository> --split dev
```

Report (`report.csv`, as written by the run):

| video | status | error | frames | duration_s | processing_s | processing_fps | missing % pose / face / left_hand / right_hand |
|---|---|---|---:|---:|---:|---:|---|
| `630-02_cr_0.1.mp4` | ok | | 50 | 2.0 | 1.946 | 25.7 | 0.0 / 0.0 / 62.0 / 36.0 |
| `711-01_cr_0.1.mp4` | ok | | 63 | 2.52 | 3.089 | 20.39 | 0.0 / 0.0 / 100.0 / 87.3 |
| `zz_corrupt_intentional.mp4` | failed | could not open video | | | | | |

Run summary: **3 videos, 2 succeeded, 1 failed** (`zz_corrupt_intentional.mp4`); total time **5.38 s**; processing FPS mean **23.05**, median **23.05** (over the 2 successful videos). Selection rule: non-recursive glob `*.mp4` in 2 folders, sorted by file name, all 3 matching files.

The batch continued past the corrupted file, and no `.npz` was written for it. The two `.npz` files were read back: `keypoints` float32 `[50, 1662]` and `[63, 1662]`, `mask` uint8 `[50, 4]` and `[63, 4]`, metadata as in Section 4 with `width=162`, `height=108`, `source_fps=25.0`. In both files, every block with mask 0 is all zeros and every block with mask 1 is non-zero.

Further checks in the same session:

- `--limit 1` on the development folder selected only `630-02_cr_0.1.mp4` ("first 1 of 2 matching files").
- `--out` pointing to a non-ignored folder inside the repository printed the warning, exited with code 2 and created no folder or file.

**Limits of this run.**

- Sample size is two very short clips plus one fabricated failure. This shows that the pipeline runs end to end and records failures; it says nothing about AUTSL coverage or full-dataset behaviour.
- The clips are very low resolution (162x108, half of the 324x216 SB-15 samples). The missing percentages above are reported only because the pipeline computes them. **Landmark quality was not measured in this issue.** Quality was evaluated in SB-15; measurement on AUTSL moves to the follow-up issue.
- The processing FPS values come from very short clips on one laptop and include per-video warm-up of the new Holistic instance. They are not a speed benchmark and are not comparable to the SB-15 figures.
- No recognition accuracy is claimed. MediaPipe extracts landmarks; it does not recognise signs.

## 8. Data handling rules (AC-5)

- Videos, label files, the class mapping and extracted `.npz` files must not enter the repository (SB-16 commitment: no redistribution of the dataset or derived landmarks without permission; [SB-46](SB-46_AUTSL_Verification.md); [SB-47](SB-47_Storage_and_Schema.md): training landmarks are external files).
- `.gitignore` now covers `landmarks_out/`, `*.npz` and `data/local/`. The script refuses to write to a non-ignored folder inside the repository (Section 3).
- Report CSVs and run summaries from real data contain sample IDs and class IDs. They are dataset-derived and stay outside the repository as well. Only aggregate figures should be copied into documents.
- Tests use fabricated data only.
- This change contains code, tests, `.gitignore` entries and this document. It contains no video, `.npz`, real label or mapping CSV, or credential.

## 9. Acceptance criteria and delivery state

| Criterion | Status | Evidence / remaining action |
|---|---|---|
| AC-1 - pipeline on a video folder, documented reproducible format, AUTSL label format accepted | Prepared | `extract_landmarks.py` run on 2 non-AUTSL development clips (Section 7). Output format and reproducibility in Section 4. `--glob "*_color.mp4"`, `--labels` (headerless `sample_id,class_id`) and `--split` accept the SB-46 AUTSL layout without code changes (Section 3, covered by tests in Section 6). The AUTSL run itself is in the follow-up issue |
| AC-2 - landmark layout recorded, 543 vs 553 flagged | Prepared | Legacy Holistic, 543 landmarks / 1662 values, stored as `layout_name` in every `.npz`. 543 vs 553 flagged as an open team decision; no choice made (Section 5) |
| AC-3 - processing time per video and failed videos | Prepared | Per-video `processing_s` / `processing_fps` in the report CSV; failed videos with error messages in the report and run summary, shown with an intentional corrupted file (Section 7) |
| AC-4 - development clips, number and limits stated; not AUTSL; no quality, accuracy or coverage claim | Prepared | Section 7: 2 TİD Sözlüğü clips at 162x108, explicitly not AUTSL; limits listed; landmark quality, recognition accuracy and full-dataset coverage not claimed |
| AC-5 - no dataset files or extracted landmark data committed | Prepared | Section 8; `.gitignore` entries and the runtime repository guard. This change contains no video, `.npz`, label, mapping or credential. The staged diff should be checked again before committing |
| AC-6 - branch `SB-50`, issue-referencing commits, PR targeting `main` | Pending | Done separately on GitHub |
| AC-7 - independent teammate approval, passing checks, merge | Pending | Done separately on GitHub |
| AC-8 - Confluence record and Jira evidence links updated | Pending | Done separately on Confluence and Jira |

## 10. Sources

1. [MEDIAPIPE_EVAL.md](../MEDIAPIPE_EVAL.md) (SB-15): layout, settings, versions and the Section 6 missing-landmark rule.
2. [SB-46 AUTSL verification](SB-46_AUTSL_Verification.md): headerless `sample_id,class_id` labels, `signerX_sampleY` IDs, `_color.mp4` video names, handling rules.
3. [SB-47 storage and schema](SB-47_Storage_and_Schema.md): landmarks and dataset files stay outside git and outside the database.
4. [SB-34 schedule](../sow/SB-34.md), row D10: post-SoW feasibility work including landmarks, Sprint 4, 16-29 November 2026.
5. [SB-18 Instructor Feedback Matrix](../SB-18_Instructor_Feedback_Matrix.md) D-7 and [SB-8 proposal](../SB-8_Project_Proposal_and_Scope.md): MediaPipe version must match between training and browser.
6. Development run outputs (report CSV, run summary, two `.npz` files) kept outside the repository.
