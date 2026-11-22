# SB-48 — Scenario Coverage Audit Against AUTSL Classes

- **Jira:** [SB-48](https://el-dili.atlassian.net/browse/SB-48)
- **Owner:** Yasmin Malgir
- **Project:** SignBridge-TR, Yaşar University Software Engineering senior project
- **Status:** Draft for team review, 22 November 2026. It records findings and options; it is not a vocabulary or scope decision.
- **Schedule link:** This is the coverage-audit part of D10. Its result is the input to I1 ("MVP vocabulary and scenarios fixed after the coverage audit") in the Schedule of Deliverables.
- **Evidence:** `docs/datasets/SB-48/` contains the four generated CSV files (`coverage-glosses.csv`, `coverage-summary.csv`, `candidate-classes.csv`, `label-checks.csv`), the generator `coverage_audit.py` and its tests `test_coverage_audit.py`.

## 1. Question, boundaries and status of each statement

The audit asks one question. For each sign that the SoW scenarios need in Direction A (sign → voice), it asks:

- whether the AUTSL class list contains a class with that name and a matching English label;
- how many labelled samples that class has in each split.

Three topics are kept apart:

| Topic | What this audit establishes | What it does not establish |
|---|---|---|
| **Dataset coverage** | Whether a class with a matching name exists, and its labelled sample counts per split | That the AUTSL sign is the TİD sign the scenario intends |
| **Recognition model success** (O1; SB-24 §4.6 criterion 1) | Nothing. No model has been trained or evaluated | Any accuracy for a class or a scenario |
| **Avatar clip coverage** (D16; criterion 4) | Nothing new. The SB-40 pilot produced four test clips (§2), and this audit does not assess them | That the avatar library covers the scenario vocabulary, or that any clip is linguistically correct |

**Name-level limitation (AC-2).** A matching class name is **not** proof that the intended TİD sign is covered. Every "found" result is a match of the Turkish class name and its English label only. No sign was inspected visually, and none was checked by a TİD user, an interpreter or the Current TİD Dictionary. The same Turkish word may correspond to a different sign, and a scenario may need a different sign from the one recorded in AUTSL.

Statements in this report are of four kinds:

- **Verified finding:** checked against the class list or the label files in this audit. Sections 4, 5 and 7.
- **Carried-over record:** stated in an earlier document and re-checked here. Section 8.
- **Option for a decision:** a recommendation for the team and the advisor; no decision has been taken. Section 9.
- **Not measured:** sign identity, recognition accuracy, avatar comprehension and video quality.

## 2. Reviewed sources and versions

Audit date: **22 November 2026**. Repository: `signBridge-FinalProject/signBridge`, `main` at **`b47bc6ea691f33d38907129528d9c2430d88902e`** (SB-39, PR #45, 12 November 2026).

| Source | Version reviewed | Used for |
|---|---|---|
| Statement of Work, Confluence [page 5046283](https://el-dili.atlassian.net/wiki/spaces/SIGNBRIDGE/pages/5046283/Statement+of+Work) | **v16**, 13 Nov 2026, "Revised submission copy v3.0" | §5 Happy Paths (summary), §6 Scope, §7 Schedule (D10, D14, I1), §11 Acceptance criteria |
| SoW assembly draft `docs/sow/SB-39-assembly-draft.md` | commit `b47bc6e` | The full happy-path text that went into the SoW, including preconditions |
| Project Proposal v1.1 R6 `docs/SignBridge-TR_Project_Proposal.pdf` | commit `3707736` | Table 2 O1 (p. 4); Methods 1, feasibility check (c) (p. 7); Table 6 (p. 9) |
| Happy paths `docs/sow/happy-paths.md` (SB-23, SB-32) | commit `1892cf6` | Signed input per scenario (§3–§6, §5.1), vocabulary table (§2), preconditions |
| Scope and acceptance criteria `docs/sow/SB-24.md` (SB-38 mapping) | commit `daffd62` | §1.1 item 6 (supported scenarios); §4.6 criteria 1, 4 and 13 |
| Schedule `docs/sow/SB-34.md` | commit `831f5dd` | D10, D14, D16, I1 |
| Supporting Technical Notes `docs/SB-18_Supporting_Technical_Notes.md` | commit `3707736` | §1.1 coverage method and name-check examples |
| Instructor feedback matrix `docs/SB-18_Instructor_Feedback_Matrix.md` | commit `3707736` | Item F-3 (SB-14 class-name comparison) |
| SB-14 lexicon design `docs/SB-14_TID_Gloss_and_Lexicon_Schema_Design.pdf` | commit `061f661` | The 12 example entries (SIGN_0001–SIGN_0012) |
| SoW literature review and personas `docs/sow/SB-42.md` | commit `beb9e24` | §2.3 vocabulary note; §4 register items P-2 and C-2 |
| Avatar pilot `docs/avatar-pilot/README.md` (SB-40) | commit `8cb4c9f` | The pilot clips and their limits |
| SB-46 AUTSL verification report | branch `SB-46`, head `a123cb1` (PR #46). Jira recorded it as open and unmerged on 21 Nov 2026; its current state was not verified for this audit | Cross-check of label totals only |
| Sprint 3 Review – Advisor Feedback, Confluence [page 23134209](https://el-dili.atlassian.net/wiki/spaces/SIGNBRIDGE/pages/23134209) | v4, 17 Nov 2026 | Items 5 and 7 (everyday vocabulary; narrowing raised, no decision) |

**Dataset inputs.** These are the team's local copy of the AUTSL ChaLearn release, read only. Video files were not opened or copied.

| File | Bytes | SHA-256 |
|---|---|---|
| `labels/SignList_ClassId_TR_EN.csv` | 4,063 | `43b4627505d1775be5c8cc95decc6ce8ed0f8fe39cfc42973d7af8f7d257403a` |
| `labels/train_labels.csv` | 653,817 | `13ab78789655d5ccde3a056968bc3c3433002a459d9ae383822bab5223e7b86c` |
| `labels/validation/ground_truth.csv` | 102,264 | `12e74248fb6199ad41fa58aa85b151966e6da31912ec109b790c6c6d627c773b` |
| `labels/test/ground_truth.csv` | 86,676 | `a3fe15717484beb2565fd812aba720afcccb36c43173f891ce31163af9137651` |

The class list and the label files are not committed. The evidence CSVs contain only the audited classes.

### 2.1 Points where the sources differ

These are recorded, not resolved, by this audit.

- **D-1 — When the audit is scheduled.**
  - Proposal R6 Methods 1 (p. 7) places the coverage audit in the feasibility check "before the Statement of Work scope is fixed on 13 November 2026".
  - SoW v16 §7 places it in D10, Sprint 4 (16–29 November 2026), as a proposed move that is "pending advisor confirmation".
  - Jira SB-48 plans it for Sprint 4.
  - This audit follows the Jira issue. It does not decide the schedule question.
- **D-2 — Happy-path preconditions.**
  - In `happy-paths.md` and the SoW assembly draft, the preconditions of HP-1 and HP-3 say that "the words of the scenario are in the recognition vocabulary (Direction A) and in the avatar clip library (Direction B)". The HP-2 precondition says this for the avatar library.
  - In the same files, the vocabulary table says that no gloss is confirmed. SB-42 recorded this as P-2.
  - The SoW v16 happy-path summary on Confluence leaves these preconditions out and states that "all glosses are illustrative and not yet confirmed by the coverage audit".
  - The repository text and the submitted SoW therefore differ on this point (see §8, P-2).
- **D-3 — Vocabulary priority and dataset content.**
  - Proposal R6 Table 2, O1, gives priority to "health, pharmacy, public services and daily conversation".
  - The audit finds that several health words used in the scenario descriptions are not AUTSL classes (§4.2).
  - This is not a contradiction between documents, but it affects how far the health scenarios can be supported from this dataset.

### 2.2 Earlier partial checks this audit extends

Name-level checks have already been made. This audit re-runs them against the full class list and label files, and adds counts, categories and per-scenario coverage.

| Earlier check | Where | What it covered |
|---|---|---|
| Vocabulary status table | `happy-paths.md` §2 (SB-32) | The happy-path glosses: 7 found and 5 not found by class name, plus candidate replacement classes |
| Name check examples | Tech Notes §1.1; Proposal R6 Methods 1 (c) | hastane, doktor, ilaç, eczane, saat, yardım and yarın are classes. randevu, karın, ağrı and gitmek are not. saat does not cover numbers or times |
| SB-14 comparison | Tech Notes §1.1; matrix item F-3 | 8 of the 12 SB-14 examples found by name; SU, RANDEVU, BUGÜN and GİTMEK not found |
| Vocabulary note | SB-42 §2.3 | Restated the happy-path results and recorded that the full audit had not yet been run |

## 3. Categories and counting rules

| SB-48 category (AC-1) | Proposal R6 Methods 1 (c) / Tech Notes §1.1 | Meaning here | In the numerator? |
|---|---|---|---|
| found | exact match, name level and provisional | A class with the same Turkish name exists, and its English label agrees with the intended meaning | Yes, with the AC-2 limitation |
| needs linguistic check | uncertain match | A class exists, but whether it fits the scenario's use is doubtful or documented as limited | No |
| not found | missing | No class with that name or a spelling variant | No |

- **Numerator:** the number of distinct glosses in the scenario classified as "found".
- **Denominator:** the total number of distinct glosses the scenario needs in Direction A.
- **Repeated glosses:** a gloss repeated within one scenario is counted once. Token counts are reported separately for transparency.
- **Fingerspelling:** reported separately and never counted as covered. No word in the happy-path signed input is marked for fingerspelling, so the count is 0 in every scenario. The 226 AUTSL class names contain no fingerspelling (alphabet) classes; the only names of two letters or fewer are *et*, *ev* and *un*. A word a user fingerspells therefore cannot be recognised from this dataset. Fingerspelling in Direction B belongs to D16 and criterion 13 and is not assessed here.
- **Curated decisions:** the categories and meaning judgements are human-curated decisions recorded in `coverage_audit.py`. The script checks them for consistency with the class list. It does not verify meaning or sign identity.
- **Matching:** Turkish characters are folded (İ→i, Ç→c, Ş→s and so on) before names are compared. Candidate replacement classes are listed separately (§6) and are not synonyms.

## 4. Gloss results (verified against the class list)

### 4.1 Happy-path signed input (Direction A)

Re-counted from the happy-path flow tables:

| Scenario | Source | Signed sequence | Tokens | Distinct glosses |
|---|---|---|---|---|
| HP-1 | `happy-paths.md` §3 step 2 | HASTANE, DOKTOR, YARDIM | 3 | 3 |
| HP-2 | §4 step 4 | İLAÇ, YARIN, Mİ | 3 | 3 |
| HP-3 | §5 step 2 | YARIN, OKUL, BULUŞMAK, Mİ | 4 | 4 |
| HP-4 | §6 step 2 | ÇAY, BİR, SİMİT, BİR, LÜTFEN | 5 | 4 |
| **Total** | | | **15 tokens** | **14 distinct uses per scenario; 12 distinct glosses overall** |

YARIN and Mİ each occur in two scenarios, and BİR occurs twice in HP-4. HP-3P (proposed, D-23; §5.1 step 3) repeats the HP-3 sequence and is not counted again.

| Gloss | Source scenario | Category | AUTSL ClassId / TR (EN) | Train / Validation / Test* | Rationale |
|---|---|---|---|---|---|
| HASTANE | HP-1 | found | 83 / hastane (hospital) | 126 / 20 / 17 | Same name; English label agrees. Name level only |
| DOKTOR | HP-1 | found | 52 / doktor (doctor) | 112 / 18 / 10 | Same name; English label agrees. Name level only |
| YARDIM | HP-1 | found | 211 / yardim (help) | 127 / 20 / 14 | Same name; English label agrees. Name level only |
| İLAÇ | HP-2 | found | 96 / ilac (medicine) | 123 / 17 / 17 | Same name; English label agrees. Name level only |
| YARIN | HP-2, HP-3 | found | 212 / yarin (tomorrow) | 117 / 17 / 17 | Same name; English label agrees. Name level only |
| OKUL | HP-3 | found | 144 / okul (school) | 126 / 20 / 17 | Same name; English label agrees. Name level only |
| ÇAY | HP-4 | found | 38 / cay (tea) | 126 / 20 / 17 | Same name; English label agrees. Name level only |
| Mİ | HP-2, HP-3 | not found | — | — | No class for the question particle. This does **not** show that TİD needs a separate manual question sign; whether the question can be formed without one is an open linguistic question |
| BULUŞMAK | HP-3 | not found | — | — | No class or spelling variant |
| BİR | HP-4 | not found | — | — | No number classes. The single *saat* (hour) class does not cover numbers or clock times |
| SİMİT | HP-4 | not found | — | — | No class |
| LÜTFEN | HP-4 | not found | — | — | No class. *rica_etmek* (request) is a candidate replacement, not a verified synonym |

\* Test-split counts are a descriptive inventory only. They are not used for vocabulary choice or model tuning (SB-24 §4.6 criterion 1: the vocabulary and the split are fixed without using test results).

### 4.2 Documented scenario vocabulary outside the happy-path signed input

These words come from the scenario descriptions in Proposal R6 Methods 1 (c) and Tech Notes §1.1, and from the SB-14 example entries. They are not part of any happy-path signed sequence, so they are not in the denominators. They show what the supported scenarios would need if they were extended.

| Gloss | Source | Category | AUTSL ClassId / TR (EN) | Train / Validation / Test* |
|---|---|---|---|---|
| ECZANE | Proposal R6 Methods 1 (c); SB-14 SIGN_0011 | found | 58 / eczane (pharmacy) | 120 / 16 / 17 |
| TEŞEKKÜR | SB-14 SIGN_0012 | found | 196 / tesekkur (thanks) | 126 / 20 / 17 |
| SAAT | Proposal R6 Methods 1 (c); Tech Notes §1.1 | needs linguistic check | 165 / saat (hour) | 127 / 20 / 17 |
| RANDEVU | Proposal R6 Methods 1 (c); SB-14 SIGN_0007 | not found | — | — |
| KARIN | Proposal R6 Methods 1 (c) | not found | — | — |
| AĞRI | Proposal R6 Methods 1 (c) | not found | — | — |
| GİTMEK | Proposal R6 Methods 1 (c); SB-14 SIGN_0010 | not found | — | — |
| SU | SB-14 SIGN_0005 | not found | — | — |
| BUGÜN | SB-14 SIGN_0008 | not found | — | — |

- **SAAT:** marked "needs linguistic check" because a single *hour* class may not be the sign intended for appointment or clock-time use. It does not cover numbers or clock times (Tech Notes §1.1).
- **SB-14 comparison:** confirmed as recorded in matrix item F-3. 8 of the 12 examples are found by name; SU, RANDEVU, BUGÜN and GİTMEK are not.

## 5. Coverage by scenario (dataset coverage at name level)

| Scenario | Numerator (found, distinct) | Denominator (required, distinct) | Coverage | Tokens found / total | Not found |
|---|---|---|---|---|---|
| HP-1 Hospital desk (Ayşe) | 3 | 3 | **3/3 (100%)** | 3/3 | — |
| HP-2 Pharmacy counter (customer) | 2 | 3 | **2/3 (67%)** | 2/3 | Mİ |
| HP-3 Classroom, Emre signing (Zeynep) | 2 | 4 | **2/4 (50%)** | 2/4 | BULUŞMAK, Mİ |
| HP-4 Café order (Can) | 1 | 4 | **1/4 (25%)** | 1/5 | BİR, SİMİT, LÜTFEN |
| All happy paths, distinct across scenarios | 7 | 12 | **7/12 (58%)** | 8/15 | Mİ, BULUŞMAK, BİR, SİMİT, LÜTFEN |

- **Fingerspelled words:** 0 in every scenario. No "needs linguistic check" gloss occurs in the happy-path signed input.
- **What HP-1's 3/3 means:** only that three AUTSL classes have matching names. It does not show that a recognition model works, that the signs are linguistically correct, or that any other precondition of HP-1 holds end to end.
- **HP-3P:** has the same signed input as HP-3, so the same name-level figure (2/4) applies.

## 6. Candidate replacement classes (not verified synonyms)

`happy-paths.md` §2 names classes that "could replace" missing glosses after the audit. All of them exist in AUTSL. Each one would change the scenario sentence, so using any of them is a scenario decision for the team and the advisor, and the meaning of each sign still needs checking.

| ClassId / TR (EN) | Named for | Train / Validation / Test* |
|---|---|---|
| 32 / beraber (together) | HP-3 | 126 / 20 / 17 |
| 15 / arkadas (friend) | HP-3 | 121 / 20 / 15 |
| 138 / nerede (where) | HP-3 | 127 / 20 / 17 |
| 165 / saat (hour) | HP-3 | 127 / 20 / 17 |
| 147 / olur (allright) | HP-3 | 126 / 20 / 17 |
| 186 / tamam (okay) | HP-3 | 96 / 20 / 16 |
| 164 / rica_etmek (request) | HP-4 | 127 / 19 / 17 |
| 196 / tesekkur (thanks) | HP-4 | 126 / 20 / 17 |
| 154 / para (money) | HP-4 | 127 / 20 / 17 |
| 172 / seker (sugar) | HP-4 | 90 / 20 / 11 |
| 185 / sut (milk) | HP-4 | 127 / 20 / 17 |
| 24 / bardak (glass) | HP-4 | 123 / 19 / 16 |

## 7. Label-file checks (verified)

Counts are based on **sample IDs**. One label row is one sample; colour and depth videos were not read and are not counted separately.

| Split | Label rows | Distinct sample IDs | Duplicate IDs | Class IDs not in list | Classes with zero samples | Samples per class, min–max (zeros included) | Signer prefixes |
|---|---|---|---|---|---|---|---|
| Train | 28,142 | 28,142 | 0 | 0 | 0 of 226 | 90–127 | 31 |
| Validation | 4,418 | 4,418 | 0 | 0 | 0 of 226 | 12–20 | 6 |
| Test | 3,742 | 3,742 | 0 | 0 | 0 of 226 | 10–17 | 6 |

- **Further checks:** no sample ID appears in more than one split; every row has exactly two columns; the class list has 226 unique ClassIds (0–225) with no empty or duplicate names.
- **Agreement with SB-46:** the split totals are the same as in the SB-46 report (branch `SB-46`, head `a123cb1`).
- **Not checked here:** whether the video files exist, decode or are of usable quality. These checks belong to SB-46 (file correspondence, not re-run here) and SB-49 (quality filter).

## 8. Earlier gaps carried over (AC-3)

| ID | Earlier record | Source | Status after this audit |
|---|---|---|---|
| G-1 | HASTANE, DOKTOR, YARDIM, İLAÇ, YARIN, OKUL and ÇAY found by class-name match | `happy-paths.md` §2; SB-42 §2.3 | **Partly resolved.** Class IDs and sample counts are now recorded. Sign identity is still unverified (AC-2) |
| G-2 | Mİ and BULUŞMAK not among the 226 classes | `happy-paths.md` §2; SB-42 §2.3 | **Confirmed, open.** Needs a scenario decision (§9). For Mİ, whether a manual sign is needed is itself open |
| G-3 | BİR, SİMİT and LÜTFEN not among the classes; HP-4 marked illustrative | `happy-paths.md` §2 and §6; SB-42 §2.3 | **Confirmed, open.** HP-4 coverage is 1/4 |
| G-4 | The single *saat* class does not cover numbers or clock times | Tech Notes §1.1; Proposal R6 Methods 1 (c) | **Confirmed, open.** No number classes exist; SAAT is "needs linguistic check" |
| G-5 | randevu, karın, ağrı and gitmek are not classes | Proposal R6 Methods 1 (c); Tech Notes §1.1 | **Confirmed, open.** Limits any extension of the hospital scenario |
| G-6 | SB-14 examples: 8 of 12 found by name | Tech Notes §1.1; matrix item F-3 | **Reconfirmed** against SIGN_0001–SIGN_0012 |
| G-7 | Full scenario coverage audit not yet run | SB-42 §2.3 | **Name-level audit completed here** (§4–§5). The linguistic and visual checks are still pending |
| G-8 (P-2) | Happy-path preconditions assume the scenario words are in the recognition vocabulary and the avatar library; the vocabulary table says no gloss is confirmed | SB-42 §4, P-2; see D-2 | **Partly addressed; still open.** Details below |
| G-9 | 38,336 vs 36,302 AUTSL sample figures | SB-42 §4, C-2 | **Outside SB-48.** Reconciled in the SB-46 report; the label counts here match 36,302 |

**P-2 in detail.**

- **Evidence provided by this audit (Direction A, name level):**
  - HP-1: all three signed glosses have matching classes.
  - HP-2: Mİ has no class.
  - HP-3: BULUŞMAK and Mİ have no class.
  - HP-4: BİR, SİMİT and LÜTFEN have no class.
- **Still open:**
  - Sign identity for the "found" glosses.
  - Whether a recognition model will recognise them (O1, not measured).
  - Whether the avatar library covers the scenarios. SB-40 produced two synthetic clips and two approximated TİD clips (ÇOK, TEYZE), none of which is a scenario word; scenario-wide, linguistically validated avatar coverage is D16 and criterion 4.
  - How the repository text and the submitted SoW should be aligned (D-2).
- **Proposed follow-up:** after the team decides on §9, update the happy-path preconditions in `happy-paths.md` in a separate change. This audit does not edit `happy-paths.md`, the SoW or the proposal.

## 9. Options for the MVP vocabulary and the scenarios (AC-4)

These are recommendations for the team and the advisor. **No decision has been taken**, and no target in the proposal or the SoW is changed.

1. **Candidate pool for the MVP recognition vocabulary.**
   - The 9 "found" classes: the 7 happy-path glosses, plus ECZANE and TEŞEKKÜR.
   - SAAT, after its linguistic check.
   - Any candidate replacement classes the team adopts (§6), after their meaning is checked.

   Train and validation counts for these classes are listed above. The final vocabulary is fixed on training and validation data only (Proposal R6 Table 2, O1; SB-24 §4.6 criterion 1).
2. **HP-1 (hospital desk).** The signed request has matching class names (3/3). Further hospital terms (randevu, karın, ağrı) are not AUTSL classes. *Option:* keep the Direction A request limited to classes that pass the meaning check, and treat other hospital content as out of scope for Direction A.
3. **HP-2 (pharmacy).** Mİ has no class. *Options:*
   - (a) Ask a TİD-competent reviewer whether the question can be expressed without a manual particle.
   - (b) Rephrase the question with existing classes. This is a candidate only and would need a meaning check.
4. **HP-3 (classroom).** BULUŞMAK and Mİ have no class. *Option:* rephrase with candidate classes from `happy-paths.md` (*beraber, arkadas, nerede, saat, olur, tamam*), after a meaning check.
5. **HP-4 (café).** Only ÇAY matches, and numbers are not available. *Options:*
   - (a) Narrow the order to sentences without quantities, using candidate classes (*rica_etmek, tesekkur, para, seker, sut, bardak*).
   - (b) Replace or drop the café scenario.
6. **Narrowing to the data (advisor option).** In the Sprint 3 Review, the team raised narrowing the scenarios to what the dataset contains, and the advisor suggested preferring everyday vocabulary (items 5 and 7). Options 2–5 follow that direction. No decision on narrowing was recorded, so this audit does not narrow any scenario.
7. **Checks still needed before I1 can be closed.**
   - A meaning check of every "found" and candidate class, against reference video or with a TİD user where available.
   - The quality filter and subset selection on the chosen classes (SB-49).
   - A team or advisor decision on options 2–6.
   - Updating the happy-path preconditions (P-2).
   - Confirmation of the D10 schedule (D-1).

## 10. Reproducing the evidence

```sh
python docs/datasets/SB-48/coverage_audit.py \
  --signlist <path>/labels/SignList_ClassId_TR_EN.csv \
  --train <path>/labels/train_labels.csv \
  --validation <path>/labels/validation/ground_truth.csv \
  --test <path>/labels/test/ground_truth.csv \
  --out docs/datasets/SB-48
```

`<path>` is the local AUTSL folder and is not stored in the repository.

The script validates all inputs before writing. If any problem is found, it prints it and exits with status 2, and it creates or overwrites no output file. The problems it checks for are:

- a wrong header or column count;
- a non-integer class ID, or a class ID that is not in the class list;
- duplicate ClassIds or duplicate class names;
- duplicate sample IDs, within a split or across splits;
- a curated category that is inconsistent with the class list.

Classes with zero samples in a split are counted as 0 and included in the minimum.

**Tests.** `test_coverage_audit.py` uses small synthetic inputs with no AUTSL data. Run it from `docs/datasets/SB-48` with `python -m unittest test_coverage_audit -v`. Its 11 cases cover:

- a valid run that writes the four CSVs, counts a zero-sample class and reports a minimum of 0;
- a wrong column count;
- a non-integer class ID;
- a class ID that is not in the list;
- a duplicate sample ID within a split, and one across splits;
- a duplicate ClassId;
- a wrong header;
- a curated "found" gloss whose class is missing;
- a curated "not found" gloss whose class exists;
- existing outputs that must not be overwritten on error.

## 11. Acceptance criteria status

| AC | Covered by | Status |
|---|---|---|
| AC-1 Compare every gloss; record found / not found / needs linguistic check | §3, §4, §5; `coverage-glosses.csv`, `coverage-summary.csv` | Draft complete; awaiting independent review |
| AC-2 Name match is not proof; limitation stated | §1, §3, §5 | Draft complete; awaiting review |
| AC-3 Carry over SB-42 / happy-paths gaps; mark which are resolved | §2.2, §8 | Draft complete; P-2 needs a team decision |
| AC-4 Recommendation for the MVP vocabulary and unsupported scenarios, incl. the advisor's narrowing option | §9 | Draft complete; options only, no decision |
| AC-5 Branch `SB-48`, issue-referencing commits, PR to `main` | Branch `SB-48`, commits containing `SB-48`, pull request to `main` | Pending; evidence links are recorded in the pull request and the Jira issue once they exist |
| AC-6 Independent approval, checks, merge | — | Pending independent review, checks and merge |
| AC-7 Confluence record and Jira evidence links | — | Pending; prepared after review |
