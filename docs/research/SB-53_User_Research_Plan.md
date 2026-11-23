# SB-53 — User Research Plan for the Interface Prototypes

- **Jira:** [SB-53](https://el-dili.atlassian.net/browse/SB-53)
- **Owner:** Yasmin Malgir
- **Project:** SignBridge-TR, Yaşar University Software Engineering senior project
- **Status:** Draft for team review, 22 November 2026. **This is a plan only.** No participant session has been held, no participant has been recruited or invited, and no ethics application or approval is recorded or claimed.
- **Sources:** reviewed on 22 November 2026 at `main` commit `b47bc6e`; the version of each source is listed in §8.1.
- **Schedule link:** D13 "User research and interface prototypes" (Sprints 4–6, 16 Nov – 27 Dec 2026) in the Schedule of Deliverables (`docs/sow/SB-34.md`). Participant sessions are gated by G1 (ethics approval) and written consent.

## 1. Purpose and boundaries

The plan describes how the team will study how the four proposal personas use the interface prototypes, which questions the study must answer, and what the team can and cannot do before ethics approval. It guides the prototype work in Sprints 4–6 (the Sprint 4 shells are SB-54 and SB-55).

It does not:

- hold or schedule any participant session;
- write the consent or information forms (SB-36 open item 4 tracks them);
- decide the open points in §9 (they belong to the team and the advisor);
- report any result. The usability and comprehension targets that need participants (task completion and SUS under SB-24 §4.6 criteria 14–16, and the target-user measures of criterion 4) stay **not measured / not verified** until they are measured with participants. Technical tests and accessibility checks that need no participants (for example criteria 5–9 and 11) are outside this plan and are reported with their own evidence.

## 2. Evidence classes

Four kinds of material will appear in the study. They are kept apart in every document, table and report.

| Class | What it is | Examples | May it be reported as a user-research result? |
|---|---|---|---|
| **S — Documented source** | A statement in an existing project document | Persona descriptions (proposal Table 3), happy paths, hypotheses | No. The personas are team-made constructs, not data from people |
| **I — Team-internal review** | A review by team members of the design or the prototypes | Cognitive walkthrough, heuristic review, accessibility self-check, protocol rehearsal | **No.** It is reported as "team-internal review" and never as a participant result or as a stage of O7 |
| **P1 — Simulated pre-test** | Volunteer participants under simulated conditions (O7 stage 1) | Scripted tasks in HP-1 to HP-4 | Yes, but only after G1 and written consent, reported as simulated and never as target-user evidence |
| **P2 — Target-user evaluation** | Suitable target users (O7 stage 2), if they can be reached | Deaf/hard-of-hearing TİD users, blind users, hearing non-signers | Yes, only after G1 and written consent, reported separately from P1 |

Simulated results do not establish usability for Deaf or blind users (ETHICS.md §3; proposal Methods 5). A team member who plays a participant in a rehearsal does not turn the rehearsal into class P1 or P2.

## 3. Goals

| # | Goal | Traces to |
|---|---|---|
| G-1 | Find out whether each persona can complete the happy path of the scenario without researcher assistance | O7; SB-24 §4.6 criteria 14 and 16; Hypothesis 3 |
| G-2 | Find interface problems in the confirmation order of the sign-to-speech flow (explicit end of sign, sentence review, then confirm or edit) | SB-24 §4.6 criterion 12 |
| G-3 | Check the usability of the avatar playback, caption and replay controls and, only in the target-user stage, whether Deaf TİD users understand the avatar output in the service flow | RQ3 (isolated-sign comprehension is a separate measure under criterion 4 and D16) |
| G-4 | Find accessibility problems in the flows with keyboard-only and screen-reader use | O6; criterion 11 (the formal audit is D20) |
| G-5 | Prepare the evaluation protocol, so that it can be agreed with the advisor and used once G1 is in place | O7, O8; SB-36 open item 3 |
| G-6 | Give the prototype work (SB-54, SB-55 and their successors) a ranked list of design questions and requirements | D13 |

## 4. Personas and scenarios covered

The four personas come from proposal Table 3 and are developed in `docs/sow/happy-paths.md` (SB-23, SB-32). The hearing counterpart is also a user (hospital staff, pharmacist, café staff, classmate).

| Persona | Group | Scenario | Role in the study | Status |
|---|---|---|---|---|
| Ayşe Yılmaz, Deaf, TİD | Deaf / hard-of-hearing TİD user | HP-1 hospital desk, two-way mode | Signer; the clerk is a hearing non-signer | In the MVP |
| Mehmet Kaya, hearing, no TİD | Hearing non-signer | HP-2 pharmacy counter, flow starts from the hearing side | Speaker; the customer is a Deaf TİD user | In the MVP |
| Zeynep Arslan, blind | Blind user | HP-3 classroom, mediated: Emre operates the device, Zeynep speaks and listens | Speaker and listener; Emre is a Deaf TİD user | HP-3 in the MVP. **HP-3P (independent blind-user flow) only if D-23 is approved**; RQ4 depends on D-23 |
| Can Demir, speech-impaired, TİD | Not named in O7 (see §9.1, A3) | HP-4 café order, sign to speech with sentence confirmation | Signer; the café staff member is a hearing non-signer | In the MVP |

## 5. Method

### 5.1 Phases

| Phase | When | What | Participants? |
|---|---|---|---|
| **A. Preparation** | Sprints 4–6 (now) | Source consolidation; task analysis of HP-1 to HP-4; team-internal reviews; draft protocol and instruments; recruitment and interpreter planning | **No** |
| **B. Stage 1: simulated pre-tests (P1)** | After G1 and written consent; the proposal plans April–May 2027 (D20) | Volunteers do scripted, fictional tasks in the four scenarios under simulated conditions | Yes (gated) |
| **C. Stage 2: target-user evaluation (P2)** | After G1 and written consent, only if suitable volunteers can be reached | The same tasks with target users | Yes (gated) |

The conditions of stage 1 (who plays which role, how the conditions are simulated) and the number and distribution of participants are **not** set here. They are agreed with the advisor before testing (O7). If target users cannot be reached, stage 2 is reported as **not measured / not verified**; it is not replaced by stage 1 results.

### 5.2 Activities in phase A (class I, team-internal)

1. **Task analysis.** For each happy path, list the user tasks, the screen for each step, the success rule (completed without researcher assistance) and the outcome states. Source: `docs/sow/happy-paths.md` and the storyboards in `docs/sow/happy-paths/`.
2. **Cognitive walkthrough** of the Figure 2 wireframes and of each prototype screen, using the happy-path steps and one persona at a time.
3. **Heuristic and accessibility self-check** of the prototypes (axe-core and manual checks, keyboard-only and screen-reader pass). This prepares criterion 11; it is not the WCAG audit of D20.
4. **Protocol and instrument drafting:** task scripts with fictional data, an observation sheet, a short interview guide, the SUS questionnaire (the Turkish wording must be chosen, §9.2, B7), and a session script that states the data rules of §7.
5. **Recruitment and interpreter planning:** a list of possible partner organisations and a plan for a TİD interpreter. No invitation is sent and no person is contacted for recruitment before the advisor confirms the arrangements (ETHICS.md §2).
6. **Protocol rehearsal** by team members (to test timing and wording). It is class I. Whether a rehearsal needs approval is asked of the advisor (§9.1, A4).

### 5.3 Questions the study must answer

| # | Question | Persona and path | Class and stage | Source |
|---|---|---|---|---|
| Q1 | Does the participant complete the happy path without researcher assistance? | All four | P1, P2 | Criteria 14, 16 |
| Q2 | Is the order "explicit end of sign, review the sentence, confirm or edit, then speak" clear for a newly generated sentence, and does anyone speak a newly generated sentence before confirming it? (The confirm/edit check applies to newly generated sentences. One-tap replay of a previously confirmed, saved quick phrase (UC-10) is the documented exception and is kept; it is not a breach of this check.) | Can (HP-4), Ayşe (HP-1) | I now; P1, P2 later | Criterion 12 |
| Q3a | Are the avatar playback, caption and replay controls easy to find and use? (Usability of the controls only. It is not evidence that anyone understands the signs.) | Ayşe, Emre in HP-3 | I now; P1 later | RQ3; criterion 12 |
| Q3b | Do Deaf TİD users understand the avatar output and the caption in the service flow? | Ayşe, Emre in HP-3 | **P2 only**, if Deaf TİD users are reached. A simulated stage (P1) cannot answer it | RQ3 |
| Q4 | Can the hearing counterpart start and follow the flow without learning the app first? | Mehmet, clerk, café staff | P1, P2 | O7; Table 3 needs |
| Q5 | Are the home screen, the mode choice and the controls operable by keyboard and screen reader? | All four paths | I now; P1/P2 later | O6; criterion 11 |
| Q6 | What do users do when the recognition or the gloss-to-sentence result is wrong (error and correction)? | Can, Ayşe | I now; P1, P2 later | SB-24 §2.4 (exception cases) |
| Q7 | Does the spoken or audio framing guidance tell the blind user that the signer is in frame? | Zeynep, HP-3P | **Only if D-23 is approved** | PX1–PX3; RQ4 |

Questions Q3b, Q4 and Q7 cannot be answered by class I material. Q1 and Q2 can be prepared by class I but not answered.

### 5.4 Work plan and findings log

The roles below are **suggestions, not assignments**. The team assigns the work at Sprint 5 planning.

| Activity | Suggested role | Required input | Output | Completion condition |
|---|---|---|---|---|
| 1. Task analysis of HP-1 to HP-4 | Research-plan owner | `happy-paths.md`, storyboards, criteria 12, 14, 16 | Table of tasks, steps, screens, success rule and outcome states per path | Every step is mapped to a screen or marked as a gap; a second team member has read it |
| 2. Cognitive walkthrough | Research-plan owner and an independent team reviewer | Task analysis, Figure 2, prototype screens (SB-54, SB-55) | Findings log entries (class I) | Every task step is walked for the persona of its path; each entry has all log fields; the reviewer has checked the entries |
| 3. Accessibility self-check | A team member who knows the accessibility checks | Prototype screens available at that time | Findings log entries marked "self-check, not audit" | Keyboard-only and screen-reader pass of the available screens is done; criterion 11 is still reported as not verified |
| 4. Protocol v0 and instruments | Protocol documentation owner | ETHICS.md §5, SB-36 open items 2 and 3, proposal O7, criteria 14–15 | Draft protocol, observation sheet, interview guide, SUS wording options | Sent to the advisor as drafts; the open decisions in §9 are listed; no approval is claimed |
| 5. Recruitment and interpreter planning | Team leader with the ethics follow-up owner | SB-20 record, ETHICS.md §2 | List of possible partner organisations and interpreter options; no contact made | List reviewed by the advisor; any contact waits for the advisor's confirmation (§9, A5) |
| 6. From findings to prototype requirements | Research-plan owner with the prototype owners | Findings log | Ranked requirements list | Every log entry has a resolution status; the prototype owners have seen the list |

**Findings log (team-internal findings, class I).** Each entry has these fields:

| Field | Content |
|---|---|
| Screen / step | The path, step number and screen, for example "HP-1, step 3, To the clerk" |
| Problem | What goes wrong or may go wrong, in one or two sentences |
| Severity | Proposed scale: 1 = blocks the task; 2 = slows or confuses the user; 3 = minor |
| Recommendation | The suggested change |
| Resolution status | Open; accepted for the prototype; fixed in the prototype (with a link); not pursued (with a reason); needs a decision (with the §9 item) |

## 6. Measures and reporting rules

Measures come from the proposal (O7, Methods 5) and SB-24 §4.4 and §4.6. The final protocol and any added measure are pending (SB-36 open item 3).

| Measure | Rule |
|---|---|
| Task completion | A task counts only if done **without researcher assistance**. Report numerator, denominator, participant count and limitations (criterion 14; target ≥80%, not a result) |
| SUS | Collected after each evaluated stage and group; report group and stage sizes; no pooled mean as evidence for each group (criterion 15; target ≥70, not a result) |
| Short interview | A few questions after the tasks; answers are not linked to a person (§7) |
| Observed problems | Recorded per task step with a severity note |

Reporting rules:

- Every figure carries its evidence class (I, P1 or P2) and stage.
- Stages and groups are reported separately and are not pooled.
- Small samples are not generalised.
- A target without evidence is written as **not measured / not verified**, never as passed.
- Technical tests (for example criteria 1, 3, 5, 6 and 7) are not part of this plan. The user measures of criterion 4 also need Deaf TİD participants; they follow their own protocol under D16 and the same approval conditions.

## 7. Ethics, consent and data conditions

The rules below come from `docs/ETHICS.md`, the proposal (O8, Methods 6) and SB-24 §4.3. They are conditions of the plan and are not decisions made here.

1. **No participant session before ethics approval and written consent.** This includes simulated pre-tests. Order: ethics approval (G1), then written, explicit informed consent, then the session. Sending documents to the advisor is not a submission and is not approval (ETHICS.md §8).
2. **Which rule applies now.** The verbal guidance of 11 November 2026 (SB-36) suggested that volunteers who only use the application, with no experiment and no personal data collection, might not need a committee application. It is verbal, unconfirmed and not yet reviewed by the advisor. Until the advisor reviews it (SB-36 open items 1 and 9), `docs/ETHICS.md` applies, and **this plan does not rely on the verbal guidance to start any session earlier.**
3. **Scripted, fictional scenarios and no real patient data** are proposed in the proposal and are not yet agreed.
4. **Privacy constraint (agreed, SB-36 open item 2):** feedback is anonymous and non-identifying; no names, no stored video or audio, no disability status linked to a person, no combinable demographics; free-text answers are not linked to a person, and participants are told not to include names.
5. **No session recording in this plan.** Under the constraint in item 4, research sessions are **not** audio- or video-recorded. ETHICS.md §5 still lists session recording as undecided, the draft consent forms still contain recording options, and the advisor has not yet reviewed the team's no-recording position (SB-36 open items 1 and 4). A different approach could be considered only after the constraint is re-evaluated with the relevant team members, the advisor and the institutional process; it is not an option in this plan.
6. **Two separate policies.** The application's camera-video policy (raw camera video is processed on the device, is not sent out and is not stored by the application; O8, criterion 9) is one thing. Recording of a research session is another, and under this plan it is not done. Neither policy changes the other.
7. **External services.** If speech-to-text, LLM or TTS runs outside the device during a session, the "not stored" statement to participants holds only if the provider also does not store the data (SB-36 open item 5; SB-37). The service choice must be made before any session.
8. **Evaluation data are research data and are not used for training.**
9. **Accessible information and consent** (including TİD for Deaf participants) belong to the protocol (ETHICS.md §5) and need an interpreter arrangement.
10. Participant names, signed forms and identifiable material are never committed to the public repository.

## 8. Inputs reused, outputs expected and timing

### 8.1 Inputs reused (not recreated)

| Input | Source and link | Version reviewed | Used for |
|---|---|---|---|
| Project Proposal v1.1 R6 | [`docs/SignBridge-TR_Project_Proposal.pdf`](https://github.com/signBridge-FinalProject/signBridge/blob/3707736/docs/SignBridge-TR_Project_Proposal.pdf): Table 3 (personas), O6–O8, RQ3–RQ4, Hypothesis 3, Methods 5–6, Table 6 | commit `3707736` (24 Oct 2026) | Personas, targets, evaluation design, data flow |
| Happy paths | [`docs/sow/happy-paths.md`](https://github.com/signBridge-FinalProject/signBridge/blob/1892cf6/docs/sow/happy-paths.md) and `docs/sow/happy-paths/*.png` (SB-23, SB-32) | commit `1892cf6` (28 Oct 2026) | Tasks and steps per scenario |
| Figure 2 wireframes | [`fig2_a_ayse.png`](https://github.com/signBridge-FinalProject/signBridge/blob/3707736/docs/fig2_a_ayse.png), [`fig2_b_mehmet.png`](https://github.com/signBridge-FinalProject/signBridge/blob/3707736/docs/fig2_b_mehmet.png), [`fig2_c_zeynep.png`](https://github.com/signBridge-FinalProject/signBridge/blob/3707736/docs/fig2_c_zeynep.png), [`fig2_d_can.png`](https://github.com/signBridge-FinalProject/signBridge/blob/3707736/docs/fig2_d_can.png) | commit `3707736` (24 Oct 2026) | Screens for the walkthrough |
| Acceptance criteria | [`docs/sow/SB-24.md`](https://github.com/signBridge-FinalProject/signBridge/blob/daffd62/docs/sow/SB-24.md) §4.3, §4.4, §4.6 (criteria 10–17) | commit `daffd62` (11 Nov 2026) | Measures and thresholds |
| Schedule | [`docs/sow/SB-34.md`](https://github.com/signBridge-FinalProject/signBridge/blob/831f5dd/docs/sow/SB-34.md): D11–D13, D20, G1, I5 | commit `831f5dd` (11 Nov 2026) | Timing and the approval gate |
| Ethics and data policy | [`docs/ETHICS.md`](https://github.com/signBridge-FinalProject/signBridge/blob/28927f9/docs/ETHICS.md); consent drafts [`onam-formu-TR.md`](https://github.com/signBridge-FinalProject/signBridge/blob/28927f9/docs/consent/onam-formu-TR.md) and [`consent-form-EN.md`](https://github.com/signBridge-FinalProject/signBridge/blob/28927f9/docs/consent/consent-form-EN.md) | commit `28927f9` (25 Oct 2026) | Conditions in §7 |
| SB-36 consultation record | [`docs/SB-36-consultation-record.md`](https://github.com/signBridge-FinalProject/signBridge/blob/96a0e0c/docs/SB-36-consultation-record.md) | commit `96a0e0c` (11 Nov 2026); verbal guidance, not a committee decision | Conditions in §7 and open items |
| SB-20 contact record | [`docs/SB-20-disability-unit-contact.md`](https://github.com/signBridge-FinalProject/signBridge/blob/e293c10/docs/SB-20-disability-unit-contact.md); [Jira SB-20](https://el-dili.atlassian.net/browse/SB-20); [Confluence summary](https://el-dili.atlassian.net/wiki/spaces/SIGNBRIDGE/pages/13139974/SB-20+Disability+Support+Unit+Contact+-+Summary) | Record commit `e293c10` (24 Oct 2026); Jira comments of 24 Oct 2026; Confluence summary v3 of 24 Oct 2026. See the SB-20 note below | Participant availability |
| Coverage audit | [PR #48](https://github.com/signBridge-FinalProject/signBridge/pull/48): `docs/datasets/SB-48_Coverage_Audit.md` | Branch `SB-48`, commit `2e08512` (22 Nov 2026); **not merged** when this draft was written | Vocabulary limits of the scripts |
| Statement of Work | [Confluence page 5046283](https://el-dili.atlassian.net/wiki/spaces/SIGNBRIDGE/pages/5046283/Statement+of+Work) | v16 (13 Nov 2026) | Current wording of D13 and G1 |
| Sprint 3 Review, advisor feedback | [Confluence page 23134209](https://el-dili.atlassian.net/wiki/spaces/SIGNBRIDGE/pages/23134209/Sprint+3+Review+Advisor+Feedback) | v4 (17 Nov 2026) | Advisor guidance on interface-first work and timing |
| Jira issue | [SB-53](https://el-dili.atlassian.net/browse/SB-53) | Read 22 Nov 2026 | AC-1 to AC-6 |

**SB-20 status, checked on 22 November 2026.** The sources I could reach are the repository record, the Jira SB-20 comments and the Confluence summary. All of them record that no response had been received from the disability support unit as of 24 October 2026, and none records a later response. This was **not verified** with the unit or in the sender's mailbox, so the current status is **not verified as of 22 November 2026**. The plan assumes no participant availability.

Two points in the inputs need the team's attention:

- **Figure 2 and the happy paths differ.** For example, Figure 2(a) shows the glosses BEN, RANDEVU, VAR, KARIN, AĞRI, while HP-1 uses HASTANE, DOKTOR, YARDIM. Figure 2(c) shows a library sentence, while HP-3 uses "Yarın okulda buluşalım mı?". The wireframes are used for screen layout only. The scripts follow the happy paths, which the SoW adopted.
- **Vocabulary.** SB-48 found 7 of the 12 happy-path glosses at name level (HP-4: 1 of 4). The task scripts are fixed only after I1 (MVP vocabulary and scenarios, 29 Nov 2026). Until then the study works on the interface flow, not on recognition vocabulary.

### 8.2 Expected outputs of Sprints 5 and 6

These are proposed targets, subject to Sprint 5 and 6 planning (the sprints are not yet in Jira). None of them contains participant data.

| Sprint | Dates | Expected output |
|---|---|---|
| Sprint 5 | 30 Nov – 13 Dec 2026 | Task analysis of HP-1 to HP-4; walkthrough and accessibility self-check findings on the prototype screens (class I); draft evaluation protocol v0 and instrument drafts (task scripts, observation sheet, interview guide, SUS wording options), sent to the advisor as drafts; recruitment and interpreter plan (no invitations) |
| Sprint 6 | 14 Dec – 27 Dec 2026 | Protocol v1 after advisor feedback; ranked list of design requirements for the prototypes; status note on G1 and on each open decision in §9; statement of what remains not measured |

### 8.3 Effect of the approval gate on timing

- In the current schedule, no participant session is planned for Sprints 4–6 (16 Nov – 27 Dec 2026). In this period the team does preparation and team-internal review (class I). Work with participants depends on G1 and written consent, and the current D20 plan is April–May 2027.
- The proposal estimates the committee review at two to three months, and SB-34 shows D12 as 30 Nov – 27 Dec 2026 and January 2027. The end of D12 is an estimate. **The date of G1 is not known.**
- The earliest planned participant work is D20 in April–May 2027, and I5 (participant results) at the end of May 2027 at the earliest. If approval is late, the proposal says to shorten the April–May evaluation and report a limitation.
- If G1 or consent is missing, or participants cannot be reached, the corresponding results are reported as **not measured / not verified**.

## 9. Open decisions (not decided in this plan)

The roles are decision owners by role, not named people. No number of participants and no approval date is proposed or assumed.

### 9.1 Needed for Sprint 5 preparation

| # | Decision | Decision owner | Resolve before |
|---|---|---|---|
| A1 | D-23: whether the blind-user path (HP-3P, PX1–PX3, RQ4, Q7) is part of the MVP | Team and advisor | Protocol v0 is sent to the advisor. If it is still open then, v0 keeps Q7 and HP-3P marked as conditional |
| A2 | Scenario narrowing and vocabulary after the coverage audit (SB-48 §9; I1 on 29 Nov 2026) | Team and advisor | The task scripts are fixed (activity 1) |
| A3 | Which O7 group the speech-impaired TİD user (Can) belongs to | Team and advisor | The group definitions in protocol v0 |
| A4 | Whether a protocol rehearsal by team members needs approval | Advisor | The rehearsal is held |
| A5 | Whether partner organisations may be contacted for recruitment before approval | Advisor | Any contact (until then, recruitment planning stays a list only) |

### 9.2 Needed before participant work

| # | Decision | Decision owner | Resolve before |
|---|---|---|---|
| B1 | Number and distribution of participants per stage and group | Team and advisor | The protocol is finalised for the ethics application |
| B2 | Conditions of the simulated stage and who plays the hearing counterpart (a team member or a recruited participant) | Team and advisor | The protocol is finalised for the ethics application |
| B3 | Advisor review of the SB-36 verbal guidance and its reconciliation with ETHICS.md (SB-36 open items 1 and 9) | Advisor, with the SB-36 owner | The ethics route is chosen |
| B4 | Ethics committee, required forms and submission route (ETHICS.md §6). The date of G1 is not known and is not assumed | Advisor and the institution | The application is prepared |
| B5 | Advisor review of the no-recording position, and alignment of ETHICS.md §5 and the consent drafts with it (SB-36 open items 1 and 4) | Team and advisor | The information and consent forms are finalised |
| B6 | Choice of speech-to-text, LLM and TTS services and their retention (SB-37) | Team and advisor | Any session that uses them, and before the "not stored" statement is given to participants |
| B7 | Turkish version of the SUS and how it is cited | Protocol documentation owner, with the advisor | The instruments are finalised |
| B8 | **Design question for the protocol:** how to report per group, as O7 requires, while following the agreed privacy constraint (no disability status linked to a person, no combinable demographics). Examples to work out: what group-level information is collected, and how very small groups are handled | Protocol documentation owner, with the advisor | The protocol is finalised for the ethics application |

## 10. Risks

| Risk | Effect on this plan | Response |
|---|---|---|
| No participants or no TİD interpreter (SB-20: no response recorded as of 24 Oct 2026; no later record found in the Jira, repository or Confluence sources; not verified with the unit as of 22 Nov 2026) | Stage 2 and some of stage 1 not possible | Report as not measured; agree numbers with the advisor |
| Ethics approval is late | Evaluation shortened | State the limitation (proposal risk table) |
| D-23 not approved | Q7 and HP-3P dropped | HP-3 stays as the mediated flow |
| Scenarios narrowed after the coverage audit | Scripts change | Fix scripts only after I1 |
| Class I findings read as user results | False evidence | Label every result with its class (§2) |
