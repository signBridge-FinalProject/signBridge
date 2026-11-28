# TİD Dataset Exploration (AUTSL & BosphorusSign22k)

Jira: SB-12 (skeleton); open items completed in [SB-52](https://el-dili.atlassian.net/browse/SB-52), 27 November 2026.

## Overview

Analysis of two public Turkish Sign Language (TİD) isolated-sign datasets: video format, resolution, frame rate, and annotation structure.

**How to read this document (SB-52).** Each AUTSL value is marked with its source:

- **[SB-46]** verified in the [AUTSL archive, extraction and label verification](SB-46_AUTSL_Verification.md);
- **[SB-16]** recorded in the [AUTSL access request record](SB-16_AUTSL_Access_Request.md);
- **[sample]** measured with `ffprobe` on the six video files of a small example package (section "Method"). These values hold for those files only and are **not verified for the whole dataset**;
- **[paper]** taken from the dataset paper and not re-checked;
- **Not verified** where no verified source exists. Such items are left open on purpose, not estimated.

BosphorusSign22k has not been acquired by the team, so none of its values are verified (see its section).

## Related dataset records

| Record | What it contains |
|---|---|
| [SB-16 AUTSL access request](SB-16_AUTSL_Access_Request.md) | How access was requested and received; usage commitments |
| [SB-46 AUTSL verification](SB-46_AUTSL_Verification.md) | Verified archive integrity, counts, label format, class mapping and signer-independent splits |
| [SB-47 storage and schema](SB-47_Storage_and_Schema.md) | Lexicon metadata schema |
| [SB-48 scenario coverage audit](SB-48_Coverage_Audit.md) | Scenario signs compared with the AUTSL class list |
| [Dataset records index](README.md) | All dataset documents in one list |

## Comparison

| Property | AUTSL | BosphorusSign22k |
|---|---|---|
| Source | Ankara University | Boğaziçi University |
| Signs (glosses) | 226 **[SB-46]** (226 unique class IDs, 0–225, in every split) | 744 [paper] |
| Signers | 43 **[SB-46]** (distinct signer IDs in the labels) | 6 (native signers) [paper] |
| Videos / clips | 36,302 labelled samples and 72,604 video files (one colour and one depth MP4 per sample) in the downloaded ChaLearn release **[SB-46]**. The earlier figure of 38,336 [paper] is not the size of this release, which contains only the balanced test set (see SB-46, "Reconciliation"). | 22,542 [paper] |
| Capture device | Kinect v2 [paper] | Kinect v2 [paper] |
| Modalities | Colour (RGB) and depth videos in the downloaded release **[SB-46]**. Skeleton data: no skeleton files in the extracted split directories (each sample has exactly two video files and there are no unexpected files) **[SB-46]**. Whether skeleton data is distributed separately is not verified. | RGB, depth, skeleton (+ pose estimates) [paper] |
| RGB resolution | 512×512 [sample]; 512×512 (clipped and resized) [paper] | 1920x1080 [paper] |
| Depth resolution | 512×512 [sample] (stored as an MP4 video stream, `yuv420p`) | 512x424 [paper] |
| Frame rate | 30 fps [sample] (`r_frame_rate` and `avg_frame_rate` 30/1 in all six files). Not verified for the whole dataset. | 30 fps [paper] |
| Skeleton | 25 joints, (x, y) [paper]; not in the extracted split directories **[SB-46]** | 25 joints, 3D [paper] |
| Video container / codec | MP4 container, MPEG-4 Part 2 video (`mpeg4`, Simple Profile), `yuv420p`, one video stream and no audio [sample]. Not verified for the whole dataset. | Not verified |
| Annotation format | Headerless CSV `sample_id,class_id`, one row per sample; class list `ClassId,TR,EN` **[SB-46]** (details below) | Not verified |
| Train/val/test split | 28,142 / 4,418 / 3,742 samples; 31 / 6 / 6 signers; no signer ID shared between splits **[SB-46]** | Not verified |
| Access / license | Access granted by the dataset authors on request; academic, non-commercial use, citation, no redistribution of the dataset or derived landmarks without permission **[SB-16]**, **[SB-46]**. No separate provider-issued licence or redistribution grant is recorded. | Not requested; not verified |

## AUTSL

### Video format

- **Folder structure [SB-46]:** one extracted directory per split. On the verification machine these were `extracted\train`, `extracted\val` and `extracted\test`; the validation directory is named `val`, not `validation`. These are local paths, not requirements.
- **File naming [SB-46]:** each labelled sample `signerX_sampleY` has exactly two files, `signerX_sampleY_color.mp4` and `signerX_sampleY_depth.mp4`. No missing, unexpected or zero-byte files were found in any split.
- **Sizes [SB-46]:** 19,111,761,758 bytes (train), 3,218,995,247 (validation), 2,796,878,753 (test); 25,127,635,758 bytes in total.
- **Container, codec, resolution, frame rate [sample]:** MP4, video codec `mpeg4` (Simple Profile), 512×512, `yuv420p`, 30 fps, one video stream and no audio, in both colour and depth files. The six files lasted 1.43–1.93 s (43–58 frames). **Not verified for the whole dataset.** The SB-49 script records fps, frame count and size for every measured colour video, so its full run can confirm or correct these values.
- **Codec decoding [SB-46]:** the archive tests validated archive integrity only; complete decoding of all videos was not checked.

### Annotations

- **Label files [SB-46]:** headerless two-column CSV `sample_id,class_id`, one row per sample. Train: `train_labels.csv`; validation and test: `ground_truth.csv` in their own label directories.
- **Checks [SB-46]:** 0 unknown class IDs and 0 duplicate sample IDs, and every labelled sample has both videos, in all three splits.
- **Class ID to sign name mapping [SB-46]:** `SignList_ClassId_TR_EN.csv` with the header `ClassId,TR,EN`. The verified mapping has 226 rows, IDs 0–225 without gaps, and no empty Turkish or English name. Source spellings are kept as given (ASCII forms such as `cay`, `ilac`). The Turkish names are class names, not TİD glosses; SB-48 found that a matching name does not prove that the intended TİD sign is covered.
- **Not in the repository:** the full mapping, the label files and the videos stay outside version control (SB-16 usage commitments). SB-46 gives the mapping's SHA-256 and explains how authorized teammates obtain or regenerate it.

### Notes

- Recorded in indoor and outdoor environments with varied backgrounds [paper].
- Two test sets (balanced and imbalanced) [paper]. The downloaded ChaLearn release contains only the balanced test set **[SB-46]**.
- Archive incident **[SB-46]**: one corrupt train archive part was found and replaced; file size alone did not detect it. Re-downloaded parts are compared by SHA-256.

## BosphorusSign22k

The team has not requested or downloaded BosphorusSign22k. Nothing below is verified.

### Video format
Not verified (dataset not acquired).

### Annotations
Not verified (dataset not acquired).

### Notes
- Signs come from health, finance, and everyday-life domains [paper].
- Higher resolution than AUTSL, fewer signers [paper].

## Observations for SignBridge

Verified facts that matter for the project:

- **Signer-independent evaluation is possible** with the official AUTSL split: 31/6/6 signers with no shared signer ID **[SB-46]**.
- **Vocabulary:** 226 classes. SB-48 shows that several scenario signs have no matching class, so the scenarios depend on the vocabulary decision (SB-48 §9).
- **Input modality:** the extracted release has colour and depth videos and no skeleton files **[SB-46]**. The browser prototype uses a regular RGB camera, so the colour videos are the relevant input, and landmarks have to be extracted from them (MediaPipe, see `docs/MEDIAPIPE_EVAL.md`).

Not verified, to be checked before conclusions are drawn:

- How well models trained on Kinect v2 colour video at 512×512 transfer to webcam input in the browser (resolution, framing, lighting). No experiment has been run.
- Video quality across the dataset. [SB-49](https://el-dili.atlassian.net/browse/SB-49) adds screening measures; its full run is pending.

## Method

- AUTSL counts, file structure, label format, class mapping and splits: taken from the SB-46 verification report, which recalculated the aggregates from evidence produced on the verification machine. They were not re-run for SB-52.
- Access and usage conditions: the SB-16 record and SB-46 "Usage conditions and handling".
- Container, codec, resolution and frame rate: `ffprobe -show_entries stream=codec_type,codec_name,profile,pix_fmt,width,height,r_frame_rate,avg_frame_rate,nb_frames,duration` on 27 November 2026, on the six video files of a small example package: `signer0_sample1000_color.mp4` and `signer0_sample1_depth.mp4` (train), `signer1_sample1_color.mp4` and `signer1_sample1_depth.mp4` (validation), `signer6_sample1_color.mp4` and `signer6_sample1_depth.mp4` (test). The package's class list and label files have the same SHA-256 values as those recorded in SB-48 §2.
- Values marked [paper] come from the dataset papers below and were not re-checked.

## Sources

- Sincan & Keles, AUTSL: A Large Scale Multi-modal Turkish Sign Language Dataset and Baseline Methods, 2020. https://arxiv.org/abs/2008.00932
- BosphorusSign22k Sign Language Recognition Dataset, LREC 2020 workshop. https://arxiv.org/abs/2004.01283
- [SB-16 AUTSL access request record](SB-16_AUTSL_Access_Request.md)
- [SB-46 AUTSL archive, extraction and label verification](SB-46_AUTSL_Verification.md)
- [SB-48 scenario coverage audit](SB-48_Coverage_Audit.md)
- [Official ChaLearn distribution description](https://chalearnlap.cvc.uab.cat/dataset/40/description/) (via SB-46)
