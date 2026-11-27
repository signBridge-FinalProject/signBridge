# SB-49 — Video Quality Filter and Subset Selection

- **Jira:** [SB-49](https://el-dili.atlassian.net/browse/SB-49)
- **Owner:** KUTAY (Jira assignee)
- **Project:** SignBridge-TR, Yaşar University Software Engineering senior project
- **Status:** Script and tests ready for review, 27 November 2026. Checked on a small example package only. The full run on the verified AUTSL data (AC-4) is still to be done by Ceren Bilgenoğlu, who holds the SB-46 verified copy.
- **Depends on:** [SB-46](https://el-dili.atlassian.net/browse/SB-46) (verified data and class mapping). Related: [SB-48](https://el-dili.atlassian.net/browse/SB-48) (scenario coverage audit).
- **Advisor source:** [Sprint 3 Review – Advisor Feedback](https://el-dili.atlassian.net/wiki/spaces/SIGNBRIDGE/pages/23134209/Sprint+3+Review+Advisor+Feedback) (data preparation): prefer everyday vocabulary, limit the number of copies per sign, and measure video quality with code instead of using every video.

## 1. What was added

| File | Purpose |
|---|---|
| `ml/data/select_subset.py` | The selection script. Measures each colour video, applies the thresholds, selects the subset and writes the manifest and the summaries. |
| `ml/data/test_select_subset.py` | 13 unit tests on synthetic videos generated during the test (no AUTSL data). |
| `ml/data/requirements.txt` | OpenCV and NumPy, pinned to the versions in `ml/eval/requirements.txt`. |
| `docs/datasets/SB-49_Quality_Filter_and_Subset.md` | This document. |

No video, label file, class list, manifest or per-video quality file is committed (AC-5).

## 2. How to run it (AC-1)

Everything that depends on the machine is an argument. Install once:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r ml/data/requirements.txt
```

Run from the repository root. The paths below follow the SB-46 verification layout (`D:\AUTSL\...`) and are examples only:

```powershell
python ml/data/select_subset.py `
  --signlist D:\AUTSL\labels\SignList_ClassId_TR_EN.csv `
  --split train      D:\AUTSL\extracted\train D:\AUTSL\train\train_labels.csv `
  --split validation D:\AUTSL\extracted\val   D:\AUTSL\labels\validation\ground_truth.csv `
  --split test       D:\AUTSL\extracted\test  D:\AUTSL\labels\test\ground_truth.csv `
  --classes docs/datasets/SB-48/coverage-glosses.csv docs/datasets/SB-48/candidate-classes.csv `
  --samples-per-class 40 `
  --out D:\AUTSL\sb49-out
```

Main arguments:

| Argument | Meaning | Default |
|---|---|---|
| `--signlist` | Class list `ClassId,TR,EN` | required |
| `--split NAME VIDEO_DIR LABELS` | One split: name, extracted video directory, headerless `sample_id,class_id` label file. Repeat per split. | required |
| `--classes` | Class IDs (`12,45,…`) and/or CSV files with an `autsl_class_id` column. Rows with an empty ID (SB-48 "not found" glosses) are skipped. | all 226 classes |
| `--samples-per-class` | Maximum selected videos per class in each split that is reduced by quality | 40 |
| `--no-quality-selection` | Splits that are kept whole for the chosen classes | `test` |
| `--min-frames`, `--min-brightness`, `--max-brightness`, `--min-contrast`, `--min-sharpness`, `--min-motion`, `--max-frozen-ratio` | Exclusion thresholds (section 3) | 16, 30, 225, 15, 0 (off), 0.5, 0.5 |
| `--frame-stride` | Measure every n-th frame (faster, less precise) | 1 |
| `--limit` | Measure at most n samples per split, for a dry run | 0 (all) |
| `--workers` | Parallel processes | CPU count − 1 |

Before anything is measured the script checks the inputs and stops with exit status 2, writing nothing, if a file or directory is missing, the class list header is not `ClassId,TR,EN`, a label row is not `signerX_sampleY,<class id>`, a class ID is unknown, or a sample ID repeats within or across splits.

**Choosing the classes is a team decision.** The command above uses the SB-48 found and candidate classes (20 classes) only as an example of "everyday vocabulary"; SB-48 itself records that no vocabulary decision has been taken. The script does not choose the vocabulary.

## 3. Quality measures and their limits (AC-2)

Each measure is computed with OpenCV on the greyscale frames of the **colour** video. The depth video is only checked for presence and non-zero size.

| Measure | What it measures | Exclusion rule (default) | Limits |
|---|---|---|---|
| `decoded_frames` | Frames OpenCV can decode; 0 means unreadable | < 16 frames, or 0 (unreadable) | Says nothing about content. Some decoders may report different counts from `ffprobe`. |
| `fps`, `width`, `height`, `duration_s` | Container metadata and decoded length | none (reported only) | Metadata, not a quality judgement. |
| `brightness` | Mean grey level, 0–255 | < 30 or > 225 | Whole-frame average. A bright background can hide dark hands, and the other way round. |
| `contrast` | Mean per-frame standard deviation of grey levels | < 15 | Low for a flat image (covered lens, fog, overexposure). Plain backgrounds lower it without harming the sign. |
| `sharpness` | Mean variance of the Laplacian (blur proxy) | off by default; used for ranking | Rises with background texture and compression noise, so values are only compared between videos of the same class. There is no universal blur threshold. |
| `motion` | Mean absolute difference between consecutive frames | < 0.5 | A sign needs movement, so near-zero motion points to a frozen or empty clip. Background movement and camera noise also count as motion. |
| `frozen_ratio` | Share of consecutive frame pairs with a mean difference below 0.25 | > 0.5 | Detects stuck or duplicated frames. A long hold at the start or end raises it. |
| depth presence | Depth video exists and is not empty | missing or empty | Does not decode the depth video. |

None of these values checks that the right sign is performed, that both hands stay in the frame, or that MediaPipe can track the signer. They are cheap screening values. Landmark-based checks belong to the MediaPipe extraction work (SB-50/SB-51), not to this script.

The default thresholds are starting values chosen to catch clearly broken clips (dark, flat, frozen, very short). They should be reviewed against `quality-distribution.csv` from the full run before the subset is used for training.

## 4. Selection rules

For each split and each chosen class:

1. **Exclude** videos that fail any threshold. The manifest records every failed rule.
2. **Score** the remaining videos: the mean of their percentile ranks within the class for sharpness, contrast and motion (0–1, higher is better).
3. **Select** up to `--samples-per-class` videos, taking signers in turn: in each round every signer with videos left contributes its best remaining video, best first. A class therefore keeps as many signers as possible, and one signer cannot fill the class.
4. Videos that pass but are not needed are recorded as "not needed (limit reached)".

**Test split.** By default the test split is not reduced by quality. For the chosen classes, every decodable sample is kept, and only missing or undecodable files are dropped. Selecting test videos by quality would make the evaluation easier than real use. The quality values are still measured and reported for the test split. Use `--no-quality-selection` to change this; any change should be recorded with the results.

The split boundaries from AUTSL are kept as they are, so the signer-independent split verified in SB-46 (31/6/6 signers, no overlap) carries over to the subset.

## 5. Outputs (AC-3, AC-5)

| File | Content | Commit? |
|---|---|---|
| `manifest.csv` | **Selection manifest:** one row per measured sample with split, sample ID, class ID, signer, `included` (yes/no), selection rank, quality score and the reason for inclusion or exclusion | **No** – lists sample IDs from the dataset |
| `quality.csv` | All measures per video | **No** – lists sample IDs |
| `summary.csv` | Counts before and after selection per split, with exclusions per rule | Yes, aggregate only |
| `class-summary.csv` | Per class and split: samples before, excluded, selected, signers before and selected | Yes, aggregate only |
| `quality-distribution.csv` | Min, p05, p25, median, p75, p95 and max of each measure per split | Yes, aggregate only |
| `run.json` | Parameters, chosen class IDs, SHA-256 of the input label files and of `manifest.csv`/`quality.csv`, tool versions and run time | Yes |

The manifest stays with the local data, as the SB-46 class mapping does. Its SHA-256 in `run.json` identifies the exact selection. Teammates with dataset access can reproduce it with the same command and parameters. A test checks that the aggregate files contain no sample IDs.

## 6. Example run on the small example package

The script was run on 27 November 2026 on a small example package supplied by Barış: the class list, the three full label files and three colour videos (one per split), not the full dataset. The label files and the class list match the SHA-256 values recorded in SB-48 §2:

| File | SHA-256 |
|---|---|
| `SignList_ClassId_TR_EN.csv` | `43b4627505d1775be5c8cc95decc6ce8ed0f8fe39cfc42973d7af8f7d257403a` |
| `train_labels.csv` | `13ab78789655d5ccde3a056968bc3c3433002a459d9ae383822bab5223e7b86c` |
| `validation/ground_truth.csv` | `12e74248fb6199ad41fa58aa85b151966e6da31912ec109b790c6c6d627c773b` |
| `test/ground_truth.csv` | `a3fe15717484beb2565fd812aba720afcccb36c43173f891ce31163af9137651` |

The classes of the three videos (41, 114, 136, 164) were chosen. All other videos of those classes are not in the package and were correctly reported as `missing colour video`.

| Sample | Split | Frames | fps | Size | Brightness | Contrast | Sharpness | Motion | Frozen | Result |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| `signer0_sample1000` | train | 43 | 30 | 512×512 | 128.7 | 79.9 | 1774.0 | 1.14 | 0.00 | Excluded: its depth video is not in the package |
| `signer1_sample1` | validation | 54 | 30 | 512×512 | 128.7 | 79.3 | 1521.0 | 1.00 | 0.00 | Selected, rank 1 |
| `signer6_sample1` | test | 55 | 30 | 512×512 | 134.9 | 86.7 | 5248.9 | 4.55 | 0.00 | Kept (test split kept whole) |

This run only shows that the script works end to end on real AUTSL files. The three videos pass every quality threshold. Its counts are not the AC-4 result.

## 7. Full run on the verified data (AC-4) – to do

Ceren runs the command in section 2 on the SB-46 verified copy and adds the results here:

- [ ] Command and parameters used (copy from `run.json`)
- [ ] Counts before and after selection per split (`summary.csv`)
- [ ] Exclusions per rule, and a check of a few excluded videos by eye to confirm that the thresholds catch real problems
- [ ] `quality-distribution.csv`, and any threshold change made after looking at it
- [ ] SHA-256 of the local `manifest.csv`
- [ ] Commit `summary.csv`, `class-summary.csv`, `quality-distribution.csv` and `run.json` under `docs/datasets/SB-49/`

Run time is not measured yet. A short dry run with `--limit 200` gives an estimate before the full run.

## 8. Showing the process in the end-of-term presentation (AC-4)

1. **Start:** 36,302 labelled samples, 226 classes, 31/6/6 signers (SB-46).
2. **Vocabulary:** the chosen everyday classes and the reason (SB-48), giving the "chosen classes" count in `summary.csv`.
3. **Quality screening:** the measures in section 3, with one passing and one excluded frame as examples, and the exclusions per rule.
4. **Limit per sign:** at most N videos per class, signers taken in turn.
5. **Result:** counts before and after per split, and the signer count kept per class (`class-summary.csv`).
6. **Reproducibility:** one command, parameters and hashes in `run.json`; the test split is not filtered by quality.

## 9. Tests

`python -m unittest test_select_subset -v` (in `ml/data`) gives 13/13 passed (Python 3.13, OpenCV 5.1). The tests generate small MP4 files and cover:

- a moving video that passes every rule, with frame count and size read correctly;
- dark, flat (no contrast) and frozen videos, each excluded by the right rule;
- a missing colour video, an undecodable file and a missing depth video;
- percentile ranks with ties;
- signer round-robin and the per-class limit;
- the test split kept whole while an unreadable test file is still dropped;
- an end-to-end run with a class CSV that contains a row without a class ID, checking counts, manifest reasons, `run.json` and that aggregate files contain no sample IDs;
- an unknown class ID and a malformed label row, both rejected with exit status 2 and no output.

## 10. Acceptance criteria

| AC | Where | Status |
|---|---|---|
| AC-1 | Section 2; `select_subset.py` arguments | Done, for review |
| AC-2 | Section 3; `quality.csv` | Done, for review |
| AC-3 | Sections 4–5; `manifest.csv` | Done (manifest produced locally, not committed), for review |
| AC-4 | Sections 6–8 | Example run done; full run on the verified data pending (Ceren) |
| AC-5 | Sections 1 and 5 | Done: no dataset files in the change |
| AC-6 | Branch `SB-49`, `SB-49:` commits, PR to `main` | Pending |
| AC-7 | — | Pending independent approval, checks and merge |
| AC-8 | — | Pending; Confluence and Jira evidence links follow review |
