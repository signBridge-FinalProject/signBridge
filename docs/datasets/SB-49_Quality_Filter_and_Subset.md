# SB-49 — Video Quality Filter and Subset Selection

- **Jira:** [SB-49](https://el-dili.atlassian.net/browse/SB-49)
- **Owner:** KUTAY (Jira assignee)
- **Project:** SignBridge-TR, Yaşar University Software Engineering senior project
- **Status:** Ready for re-review, 27 November 2026. The full run on the SB-46 verified data (AC-4) was carried out on 27 November 2026 by Ceren Bilgenoğlu, who holds the verified copy, with script version `e000c69`; results in section 7. The run does not approve a final vocabulary or training subset.
- **Depends on:** [SB-46](https://el-dili.atlassian.net/browse/SB-46) (verified data and class mapping). Related: [SB-48](https://el-dili.atlassian.net/browse/SB-48) (scenario coverage audit).
- **Advisor source:** [Sprint 3 Review – Advisor Feedback](https://el-dili.atlassian.net/wiki/spaces/SIGNBRIDGE/pages/23134209/Sprint+3+Review+Advisor+Feedback) (data preparation): prefer everyday vocabulary, limit the number of copies per sign, and measure video quality with code instead of using every video.

## 1. What was added

| File | Purpose |
|---|---|
| `ml/data/select_subset.py` | The selection script. Measures each colour video, applies the thresholds, selects the subset and writes the manifest and the summaries. |
| `ml/data/test_select_subset.py` | 14 unit tests on synthetic videos generated during the test (no AUTSL data). |
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

Run from the repository root. The paths below follow the SB-46 verification layout (`D:\AUTSL\...`) and are examples only. Check each path against the actual local copy before running, in particular the location of `SignList_ClassId_TR_EN.csv`, which SB-46 does not list:

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
| `motion` | Mean absolute difference between consecutive frames | < 0.5 | Near-zero motion can point to a frozen or empty clip, but a low value is **not** on its own evidence of a broken video: valid signs with small or slow movements also score low (see section 7.3). Background movement and camera noise also count as motion. |
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
| `class-summary.csv` | Per class ID and split: samples before, excluded, selected, signers before and selected. Class IDs only, no Turkish or English class names | Yes, aggregate only |
| `quality-distribution.csv` | Min, p05, p25, median, p75, p95 and max of each measure per split | Yes, aggregate only |
| `run.json` | Parameters, chosen class IDs, SHA-256 of the input label files and of `manifest.csv`/`quality.csv`, tool versions and run time | Yes |

The manifest stays with the local data, as the SB-46 class mapping does. Its SHA-256 in `run.json` identifies the exact selection. Teammates with dataset access can reproduce it with the same command and parameters. No publishable file contains class names: the TR/EN names come from the private class list, and exporting them for an all-class run would reproduce the full ClassId/TR/EN mapping that SB-46 keeps out of the repository. Readers who need names look the IDs up in their local mapping. Tests check that the aggregate files contain no sample IDs and no class names.

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

## 7. Full run on the verified data (AC-4)

### 7.1 Run

| Item | Value |
|---|---|
| Date | 27 November 2026, 21:46 (UTC+3) |
| Run by | Ceren Bilgenoğlu, on the computer that holds the SB-46 verified copy (the data stays there) |
| Script version | `e000c69` (branch `SB-49`) |
| Environment | Windows 11, Python 3.12.10, OpenCV 5.0.0, NumPy 2.4.6, 2 workers |
| Classes | The 20 SB-48 found and candidate classes (`--classes coverage-glosses.csv candidate-classes.csv`); an example choice, not a vocabulary decision |
| Parameters | Defaults: `--samples-per-class 40`, test split not reduced by quality, thresholds unchanged (section 3) |
| Exit code | 0 |
| Measuring time | 730.4 s for 3,126 colour videos |
| Input SHA-256 | Class list and the three label files match SB-48 §2 (`43b46275…`, `13ab7878…`, `12e74248…`, `a3fe1571…`) |
| Local `manifest.csv` SHA-256 | `c95c69d9f5035a96367396d2e4933722ae8b1ae2d790710481eebd8739b00358` |
| Local `quality.csv` SHA-256 | `64d09295f452fb3dc17bca4e87aa1f92e63200e11b90af820a731e5a9e409049` |

The manifest and the per-video measures stay on the run computer. The four aggregate outputs are committed in [`SB-49/`](SB-49/): `summary.csv`, `class-summary.csv`, `quality-distribution.csv` and `run.json`. They contain no sample IDs and no class names (checked before committing).

### 7.2 Counts before and after selection

| Split | Labelled samples (all 226 classes) | In the 20 chosen classes | Missing / unreadable | Excluded by a threshold | Passed, not needed | **Selected** | Signers selected |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 28,142 | 2,420 | 0 / 0 | 12 (all `motion`) | 1,608 | **800** | 31 |
| Validation | 4,418 | 386 | 0 / 0 | 0 | 0 | **386** | 6 |
| Test | 3,742 | 320 | 0 / 0 | not applied | 0 | **320** | 6 |
| Total | 36,302 | 3,126 | 0 / 0 | 12 | 1,608 | **1,506** | 43 |

- **Train:** every chosen class reached the limit of 40 videos (20 × 40 = 800). All 31 training signers remain. Per class (`class-summary.csv`), the 12 exclusions fall in five classes (IDs 24: 4, 172: 3, 164: 2, 185: 2, 147: 1). Classes 24 and 172 each lose one signer (31 → 30 and 24 → 23), because all of that signer's videos in the class were excluded by the motion threshold (signers are taken in turn, so every signer with a passing video gets at least one).
- **Validation:** no class has more than 40 videos and no video failed a threshold, so all 386 videos are kept. The per-class limit only changes the train split in this run.
- **Test:** kept whole by design (section 4). Its lowest motion value is 0.493, so at least one test video would have failed the motion threshold if the filter had been applied there.
- No video was missing, unreadable or excluded by brightness, contrast, frame count, frozen frames or a missing depth video.

### 7.3 Threshold review

The measured ranges (`quality-distribution.csv`, colour videos of the 20 classes) are far from the brightness (30–225), contrast (15) and frame-count (16) limits in all splits: brightness 101.7–151.9, contrast 40.7–88.3, at least 20 decoded frames. Every video is 512×512 at 30 fps. Frozen-frame ratios stay at or below 0.294. Only the motion threshold excluded anything.

Ceren opened two of the 12 motion-excluded train videos, from different classes. In both, the person signing is visibly moving. So a motion value below 0.5 does **not** mean that a video is broken. The motion threshold can also exclude valid signs with little movement. Opening two videos does not check whether the signs are correct.

Consequences:

- The 12 exclusions are reported as "low motion", not as broken videos.
- The thresholds were **not** changed for this run. With 40 of 90–127 train videos needed per class, the exclusions did not reduce any class below the limit.
- Before this subset is used for training, the team should decide whether to keep `--min-motion 0.5`, lower it, or turn it off (`--min-motion 0`) and rely on ranking only. The lowest train motion value was 0.447 and the 5th percentile 0.666.

### 7.4 What this run does not establish

- It does not fix the final vocabulary or approve a training subset. The 20 classes are the SB-48 example set.
- It does not check that the signs are correct, that the hands stay in the frame, or that MediaPipe can track the signer (SB-50/SB-51).
- Container codec, profile and pixel format are not recorded by the script; it confirms 512×512 and 30 fps for the 3,126 measured colour videos only.

## 8. Showing the process in the end-of-term presentation (AC-4)

1. **Start:** 36,302 labelled samples, 226 classes, 31/6/6 signers (SB-46).
2. **Vocabulary:** the chosen everyday classes and the reason (SB-48), giving the "chosen classes" count in `summary.csv`.
3. **Quality screening:** the measures in section 3 and the exclusions per rule (full run: 12 train videos, all by the motion threshold).
4. **Limit per sign:** at most N videos per class, signers taken in turn.
5. **Result:** 36,302 → 3,126 (20 classes) → 1,506 selected (train 800, validation 386, test 320), with all 43 signers kept (section 7.2).
6. **Reproducibility:** one command, parameters and hashes in `run.json`; the test split is not filtered by quality.
7. **Limitation:** low motion is not proof of a broken video (section 7.3).

## 9. Tests

`python -m unittest test_select_subset -v` (in `ml/data`) gives 14/14 passed (Python 3.13, OpenCV 5.1, ResourceWarnings as errors). The tests generate small MP4 files and cover:

- a moving video that passes every rule, with frame count and size read correctly;
- dark, flat (no contrast) and frozen videos, each excluded by the right rule;
- a missing colour video, an undecodable file and a missing depth video;
- percentile ranks with ties;
- signer round-robin and the per-class limit;
- the test split kept whole while an unreadable test file is still dropped;
- an end-to-end run with a class CSV that contains a row without a class ID, checking counts, manifest reasons, `run.json` and that aggregate files contain no sample IDs;
- an all-class run, checking that no publishable file contains a class name and that `class-summary.csv` has no name columns;
- an unknown class ID and a malformed label row, both rejected with exit status 2 and no output.

## 10. Acceptance criteria

| AC | Where | Status |
|---|---|---|
| AC-1 | Section 2; `select_subset.py` arguments | Done, for review |
| AC-2 | Section 3; `quality.csv` | Done, for review |
| AC-3 | Sections 4–5; `manifest.csv` | Done (manifest produced locally, not committed), for review |
| AC-4 | Sections 6–8; `SB-49/` evidence | Done, for review: full run on the verified data, 3,126 → 1,506 videos (section 7) |
| AC-5 | Sections 1 and 5 | Done: no dataset files in the change |
| AC-6 | Branch `SB-49`, `SB-49:` commits, [PR #51](https://github.com/signBridge-FinalProject/signBridge/pull/51) to `main` | Done, for review |
| AC-7 | — | Pending independent approval, checks and merge |
| AC-8 | — | Pending; Confluence and Jira evidence links follow review |
