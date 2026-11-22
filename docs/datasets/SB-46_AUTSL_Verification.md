# SB-46 — AUTSL Archive, Extraction and Label Verification

**Jira:** [SB-46](https://el-dili.atlassian.net/browse/SB-46)  
**Owner:** Ceren Bilgenoğlu  
**Project:** SignBridge-TR, Yaşar University Software Engineering senior project  
**Verification window:** 20–21 November 2026, Türkiye time  
**Report date:** 21 November 2026  
**Status:** Technical evidence prepared; published on branch `SB-46` with a PR targeting `main` (21 November 2026); independent review, checks and merge pending.

## Outcome and evidence scope

The supplied AUTSL ChaLearn distribution contains 36,302 labelled samples, each with one RGB/color MP4 and one depth MP4: 72,604 video files totalling 25,127,635,758 bytes. All three archive tests and extractions reported `Everything is Ok` in the terminal output supplied by Ceren. The final full train archive test additionally has an explicitly recorded exit code of 0. Separate validation/test exit-code outputs were not supplied; their displayed success summaries are the evidence used here.

Verification ran on Ceren's Windows computer using PowerShell and 7-Zip 26.06 x64, with archives and extracted data on the exFAT USB drive D:. The report author reviewed four uploaded CSV evidence files, recalculated their aggregates and pairwise signer intersections, and inspected the uploaded class mapping. The report author did not directly access the USB drive or rerun checks on the raw videos.

## Verified distribution and counts

| Split | Labelled samples | Video files | Extracted bytes | Classes | Distinct signer IDs |
|---|---:|---:|---:|---:|---:|
| Train | 28,142 | 56,284 | 19,111,761,758 | 226 | 31 |
| Validation | 4,418 | 8,836 | 3,218,995,247 | 226 | 6 |
| Test | 3,742 | 7,484 | 2,796,878,753 | 226 | 6 |
| Total | 36,302 | 72,604 | 25,127,635,758 | 226 unique classes | 43 unique signer IDs |

The local validation video directory is named `val`, not `validation`. The correspondence used was:

| Split | Extracted video directory | Label file |
|---|---|---|
| Train | `D:\AUTSL\extracted\train` | `D:\AUTSL\train\train_labels.csv` |
| Validation | `D:\AUTSL\extracted\val` | `D:\AUTSL\labels\validation\ground_truth.csv` |
| Test | `D:\AUTSL\extracted\test` | `D:\AUTSL\labels\test\ground_truth.csv` |

These are verification-machine paths, not deployment requirements. Source labels are headerless two-column CSVs: `sample_id,class_id`. An example sample ID follows `signerX_sampleY`; expected video names append `_color.mp4` and `_depth.mp4`.

### Reconciliation with the earlier 38,336-sample figure

The existing SB-12 exploration document lists 38,336 AUTSL samples. That value must not be presented as the expected size of these downloaded archives. The official ChaLearn distribution page explains that AUTSL has balanced and imbalanced test sets, and that this challenge releases only the balanced test subset. It explicitly gives 28,142 training, 4,418 validation and 3,742 test samples, totalling 36,302, with 31/6/6 non-overlapping signers. The observed counts match that distribution exactly. The numerical difference from 38,336 is 2,034; this is not evidence of missing files from the supplied challenge archives. This verification does not claim acquisition of the separate imbalanced test distribution.

## Checks and results

| Check | Train | Validation | Test |
|---|---:|---:|---:|
| Unknown class IDs in labels | 0 | 0 | 0 |
| Duplicate sample-ID groups within labels | 0 | 0 | 0 |
| Missing color videos for labelled samples | 0 | 0 | 0 |
| Missing depth videos for labelled samples | 0 | 0 | 0 |
| Unexpected files in extracted split directories | 0 | 0 | 0 |
| Zero-byte files | 0 | 0 | 0 |

Every observed split has exactly two video files per labelled sample. Extracted directory counts and total byte sizes match the successful extraction summaries. Pairwise intersections of the signer IDs parsed from label sample IDs are all empty:

| Pair | Shared signer IDs |
|---|---:|
| Train / Validation | 0 |
| Train / Test | 0 |
| Validation / Test | 0 |

This establishes disjointness of the provided signer identifiers. It is not an independent biometric verification of participants' identities.

### Class ID to sign-name mapping

`class-id-sign-mapping.csv` was generated locally from the supplied `SignList_ClassId_TR_EN.csv`, sorted by numeric class ID. Its schema is `ClassId,TR,EN`. Inspection of the uploaded mapping confirmed exactly 226 rows and 226 unique IDs, covering 0–225 without gaps, with no empty Turkish or English sign names. Source spellings were preserved; no translation or gloss normalization was introduced.

The complete mapping remains a local dataset-derived output. Do not add it, source label files, raw videos, extracted landmarks, archive credentials or private download URLs to the repository without checking redistribution permission. The report can reference the local mapping and its digest without republishing all mapping rows.

**Private handoff / reproduction (AC-4).** An authorized teammate can request the exact verified export privately from Ceren Bilgenoğlu under the team's dataset-access permissions and verify SHA-256 `57a2a1fbaa2e1646089cbaaa346f8448039cf0de2b6cdc6aa1bbc856a82f2eb1`. Alternatively, regenerate the mapping from the authorized local `SignList_ClassId_TR_EN.csv` by reading `ClassId,TR,EN`, sorting numerically by `ClassId` and exporting those three fields without changing source spellings; verify 226 unique IDs, 0–225, and non-empty names. The digest identifies the exact supplied export, not the provider's source file; a regenerated CSV may have different bytes because of encoding, quoting or line endings and must be compared by content as well. Do not publish the source list or regenerated full mapping in GitHub.

## Archive integrity and resolved incident

| Split | Number of parts | Total archive bytes | Final displayed test result | Displayed extraction result |
|---|---:|---:|---|---|
| Train | 18 | 18,514,780,403 | Everything is Ok; exit code 0 | Everything is Ok |
| Validation | 3 | 3,125,796,777 | Everything is Ok | Everything is Ok |
| Test | 3 | 2,693,843,542 | Everything is Ok | Everything is Ok |

Initial train verification encountered encrypted-data and header errors, with the first recorded failure at `train\signer32_sample456_depth.mp4`, followed by a group of header errors. Listing that member reported ZIP offset 9,820,775,422 and packed size 353,878 bytes. Its location is wholly within part 010, whose range starts at byte 9,437,184,000 for 1,048,576,000-byte parts.

A fresh part 010 was downloaded to the internal disk and compared with the existing USB copy. Their SHA-256 digests differed:

| Copy | SHA-256 |
|---|---|
| Original USB part 010 | `7477e1e60ed88630a32e55ad153c40cc14b27105eb0b72f3976695371bcff830` |
| Fresh download and replacement USB part 010 | `37d2ffe47b14c74a56830bbacfd712a9d0d391cfde95aaf4a7471aaa6779394c` |

The old USB file was retained as `train_set_vfbha39.zip.010.old`; the new copy's hash was verified after copying to USB. Both the previously failing member test and the subsequent full train test passed after replacement. This establishes that replacement resolved the observed failure. It does not establish whether the original difference arose during transfer, an interrupted write, filesystem repair, or another cause. File size alone did not detect this problem. Archive passwords are intentionally omitted from this report.

## Evidence files and provenance

Four PowerShell-produced CSVs were uploaded for review. The first three contain verification summaries; the fourth contains the locally generated mapping. SHA-256 values below identify the exact uploaded evidence bytes, not the dataset provider's original checksums.

| Evidence file | Rows | SHA-256 |
|---|---:|---|
| [label-summary.csv](SB-46/label-summary.csv) | 3 | `9d534c05d03a723230ed40156f22b517948bbcbdc1d63e7a6c409e41ea9709d6` |
| [file-summary.csv](SB-46/file-summary.csv) | 3 | `5725441517a8f99687f70c60fea6349aa47206f0e9648053f4ec19630245959b` |
| [signer-overlap.csv](SB-46/signer-overlap.csv) | 3 | `19d7ea5666b367bbea73f98741ab453b6e2ca190374107af991606178684c7a7` |
| `class-id-sign-mapping.csv` | 226 | `57a2a1fbaa2e1646089cbaaa346f8448039cf0de2b6cdc6aa1bbc856a82f2eb1` |

The summary CSVs support aggregate checks. Per-video checksum manifests and full saved 7-Zip logs were not supplied. Successful ZIP tests validate archive-level integrity; the work does not claim complete codec decoding, frame quality assessment, MediaPipe extraction, database import or model evaluation. Those are separate downstream activities, including SB-49, SB-50 and SB-51.

## Usage conditions and handling

The existing SB-16 record reproduces the team's access request committing to academic, non-commercial use, appropriate citation, compliance with the applicable terms, and no redistribution of the dataset or derived landmarks without explicit permission. It records that access credentials were received but does not establish an additional redistribution grant. The replacement-link email supplied for this work also does not itself contain a new licence grant.

Accordingly, the project handling policy remains academic/non-commercial use, citation of AUTSL and the relevant challenge distribution, and no redistribution without permission. Keep original correspondence and credentials privately. The official ChaLearn page also links its challenge terms; this report does not replace those terms or claim that the sent-request commitments are a separate provider-issued licence. Confirm any additional correspondence conditions before final review.

Only the report and permitted aggregate verification evidence should be proposed for GitHub. Keep raw/derived dataset files and credentials outside version control, and inspect the actual staged diff before committing. The prepared change is limited to this report and the three aggregate evidence CSVs below. The local full class mapping and all source dataset files are excluded. This is a check of this change, not a repository-wide credential audit.

## Acceptance criteria and delivery state

| Criterion | Evidence / remaining action |
|---|---|
| AC-1 — download all three splits and mapping | Locally evidenced by archive tests, extractions, labels and mapping; this change excludes credentials and private access links. |
| AC-2 — extract and record counts and sizes | Evidenced by successful extraction outputs and [file-summary.csv](SB-46/file-summary.csv). |
| AC-3 — compare classes, counts and signer-independent split | Matches the official 36,302-sample challenge distribution; earlier 38,336 figure reconciled above. |
| AC-4 — produce class-ID/name mapping | Local CSV produced and inspected: 226 unique IDs, 0–225, no empty names. |
| AC-5 — document usage conditions | Handling conditions recorded above from SB-16; any additional private-correspondence requirements remain for the owner/reviewer to confirm. |
| AC-6 — keep dataset files and passwords out of repository | The prepared package contains only the verification report and three aggregate CSVs; no videos, source labels, full mapping, passwords or private download URLs are included. |
| AC-7 — issue-key branch, commits and PR | Branch `SB-46` published and a PR opened targeting `main` on 21 November 2026; commit messages carry the SB-46 key. Historical note: an earlier delivery attempt was blocked by the connected GitHub integration returning 403 (Resource not accessible by integration), and no branch, commit or PR was created then. |
| AC-8 — independent review, checks and merge | Pending; this report is not a teammate approval. |
| AC-9 — Confluence and Jira evidence links | Delivery links are tracked in the SB-46 Jira comment and the Documentation summary; these do not imply approval or merge. |

Independent teammate approval, applicable passing checks and merge are still required. Technical verification and publication of this report do not close the issue.

## Sources

1. [SB-46 acceptance criteria](https://el-dili.atlassian.net/browse/SB-46), read for this report.
2. [SB-16 access request and response record](https://github.com/signBridge-FinalProject/signBridge/blob/main/docs/datasets/SB-16_AUTSL_Access_Request.md), source revision `f3c8ae7372f87a3876ba1efbf8946e1559ec97d3`.
3. [SB-12 dataset exploration](https://github.com/signBridge-FinalProject/signBridge/blob/main/docs/datasets/tid-dataset-exploration.md), source revision `de6e8abb7d579c734dded15c3dd8aafd49640b58`.
4. [Branching and PR strategy](https://github.com/signBridge-FinalProject/signBridge/blob/main/docs/BRANCHING.md), source revision `840c9f63287e4a3ee11c0024b153999766ed2158`.
5. [Official ChaLearn distribution description](https://chalearnlap.cvc.uab.cat/dataset/40/description/), sections Data Split and Structure / Basic Statistics, accessed 21 November 2026.
6. Four owner-generated CSV evidence files listed above and terminal output supplied during the local verification session. Download links and archive passwords are deliberately not reproduced.
