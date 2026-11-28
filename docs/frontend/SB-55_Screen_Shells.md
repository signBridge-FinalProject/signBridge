# SB-55 — Mode Selection and Two-Way Conversation Screen Shells

- **Jira:** [SB-55](https://el-dili.atlassian.net/browse/SB-55)
- **Owner:** Barış Hansu (Sprint 4 team leader)
- **Recorded:** 28 November 2026, Türkiye time
- **Status:** Screens, this record and local checks prepared. Independent review, applicable checks and merge are pending.
- **Depends on:** [SB-54](https://el-dili.atlassian.net/browse/SB-54) (frontend scaffold, merged). Related: [SB-53](https://el-dili.atlassian.net/browse/SB-53) (user research plan, which uses these screens as prototypes).
- **Sources:** Figure 2 wireframes of the Project Proposal v1.1 ([fig2_a_ayse.png](../fig2_a_ayse.png), [fig2_b_mehmet.png](../fig2_b_mehmet.png), [fig2_d_can.png](../fig2_d_can.png)); the happy-path renderings in [happy-paths.md](../sow/happy-paths.md); SoW function IDs MF1, MF10 and MF12 in [SB-24.md](../sow/SB-24.md).

## 1. Purpose and scope

SB-55 adds the entry flow of the app as **static screen shells** on top of the SB-54 scaffold: the mode selection (MF1) and the layouts of Sign to Voice, Voice to Sign and the two-way conversation (MF10). The shells show where the later features will sit, so the interface can be reviewed and used in the user research (SB-53) before recognition, speech and avatar work exists.

The shells contain **placeholder content only**. They do not open the camera or the microphone, recognise signs, transcribe speech, speak, play an avatar, store anything or call a server. Every screen says this on the page.

## 2. Screens and routes

| Route | Screen | Wireframe it follows | Function IDs |
|---|---|---|---|
| `/` | Home with the mode selection ("Nasıl iletişim kurmak istersiniz?") and the usage guides from SB-54 | Home, step 1 of Figure 2 (a) to (d) | MF1 |
| `/isaretten-sese` | Sign to Voice: sign step, sentence check, speaking screen | Figure 2 (a) steps 2–3, (d) steps 2–4 | MF2–MF6 (layout only), MF12 |
| `/sesten-isarete` | Voice to Sign: listening step, avatar step | Figure 2 (b) steps 2–3 | MF7–MF9 (layout only), MF12 |
| `/iki-yonlu` | Two-way conversation: both sides next to each other, turn indicator, example log | Figure 2 (a) and (b), the alternating steps combined into one layout | MF10, MF12 |
| `/hizli-ifadeler` | Placeholder that says Quick phrases are not part of this issue | Home button only | MF11 (not built) |

The home page keeps the SB-54 hero and guides. The four modes appear in the wireframe order: Sign → Voice, Voice → Sign, Two-way conversation, Quick phrases. Each screen has one `h1`, a "Mod seçimine dön" link and a notice that the content is a placeholder.

Steps inside Sign to Voice and Voice to Sign are local to the page. Their buttons only move between the shell steps (for example "Bitti" shows the sentence check). They do not start any work. When the step changes, focus moves to the step heading.

## 3. Differences from the wireframes (AC-2)

1. **Language and wording.** Labels are Turkish, following the SB-54 interface language. The wireframes use English labels.
2. **Placeholder content.** The wireframes show sample sentences and glosses (for example "Randevum var, karnım ağrıyor." and [BEN] [RANDEVU]). The shells show "Örnek cümle burada görünür." and [İŞARET 1] [İŞARET 2] [İŞARET 3], so no sentence or gloss looks like a recognition result. The English line under the Turkish sentence is not shown.
3. **Pictures.** The camera picture with tracked hands, the microphone with sound waves and the avatar drawing are replaced by labelled placeholder panels. The status "hands tracked" becomes "El takibi: kapalı".
4. **Confirm before speaking.** Figure 2 (a) and (b) speak the sentence directly ("Edit / repeat"). The shell follows the happy paths and the functional requirement: Done, then **Cümleyi kontrol edin** with "Konuş" and "Düzenle", then the speaking screen. This is open point 2 of [happy-paths.md](../sow/happy-paths.md) §8.
5. **Speaking screen.** It states that nothing is spoken. "Tekrarla" and "Yeni işaret ver" only move between the shell steps. "Düzenle" returns to the sign step because there is no text editor.
6. **Sending speech to the avatar.** Figure 2 (a) shows "Auto-sent" and (b) shows "Send to avatar". The shell has a neutral "Konuşmayı bitir" button. The team has not decided which behaviour applies (happy-paths §8, point 3).
7. **Avatar controls.** The wireframes show "speed 1.0× · replay". The shell shows the text "Hız 1,0×. Tekrar oynatma bu sürümde yoktur." and no replay control, because no playback exists.
8. **Two-way conversation.** The wireframes show it as a sequence of full screens. The shell shows both sides in one layout with a "Sıra" indicator, a "Sırayı değiştir" button and an example log marked "(örnek)". The camera view does not switch automatically.
9. **Not built.** The Quick phrases screens (MF11) and the success screens ("Outcome") are not part of SB-55. The Quick phrases button leads to a placeholder that says so.

## 4. Keyboard use and labels (AC-3)

- Every control is a native `a` or `button` with a visible text label. Icons are decorative (`aria-hidden`).
- All controls are reachable with Tab in reading order and are activated with Enter or Space. Nothing depends on a pointer or on hover.
- The focus outline of SB-54 also applies to step headings.
- The turn indicator on the two-way screen is a status region, so a screen reader announces a change of turn.
- Text uses the SB-54 base size and contrast values. No WCAG compliance is claimed.

## 5. What the shells do not do (AC-4)

- No `getUserMedia`, `SpeechRecognition`, `speechSynthesis`, MediaPipe, model or `fetch` call exists in the new code.
- No recognition result, recognised word, spoken output or avatar animation is shown or claimed. The only sentences and glosses are marked as placeholders or examples.
- No dataset file, label or landmark data is part of the change.

## 6. Checks run

Run locally on 28 November 2026 against the production build (`npm run build`, `vite preview`), in headless Chrome driven by Playwright, with axe-core 4.x. The script is not committed, because the frontend has no test runner yet.

| Check | Result |
|---|---|
| Build | Succeeds; `sw.js` generated |
| Home lists the four modes in wireframe order; each is reachable with Tab | Pass |
| Each mode screen opens from the home page by keyboard; the `h1` receives focus and the page title updates | Pass |
| Sign to Voice, three steps, forward and back, by keyboard only; focus lands on each step heading | Pass |
| Voice to Sign, two steps, forward and back, by keyboard only | Pass |
| Two-way: "Sırayı değiştir" switches the turn and updates the status region | Pass |
| Every route (8, including an unknown path) at 360, 768 and 1280 CSS pixels: no axe violations, no horizontal scroll | Pass, 24 of 24 |
| Every link and button has a text label; exactly one `h1` per route | Pass |
| `getUserMedia` is never called; no request leaves the origin; no console or page error | Pass |

97 of 97 automated checks passed. One earlier failure was a timing error in the test script, fixed by waiting for the route change.

**Not done.** No screen reader (VoiceOver, TalkBack, NVDA) was used, no real phone or tablet was tried, and only Chrome was exercised. Offline use of the new routes through the service worker was not tested. The wireframe comparison is by eye against the images listed under Sources.

### How a reviewer can repeat the main checks

```sh
cd frontend
npm ci
npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

| Action | Expected result |
|---|---|
| Open `/`. Press Tab until "İşaretten sese" is focused, then Enter. | The screen opens, its title is focused and the notice about placeholder content is visible. |
| Press Tab to "Bitti", Enter, then Tab to "Konuş", Enter. | "2. Adım" and then "3. Adım" are announced as headings. The last step says nothing is spoken. |
| Open `/iki-yonlu`, Tab to "Sırayı değiştir", Enter. | The status line changes from "Duyan kişi" to "İşaret eden kişi". |
| Open each screen at 360 pixels wide. | The two sides stack; nothing is cut off. |
| In the browser's network panel, open all screens. | No request to a server other than the static files. No permission prompt for camera or microphone. |

## 7. Acceptance criteria and delivery state

| AC | Where | Status |
|---|---|---|
| AC-1 Screens for mode selection, Sign to Voice, Voice to Sign and the two-way conversation, placeholder content only | Sections 2 and 5; `frontend/src/screens.jsx`, `frontend/src/pages.jsx` | Done, for review |
| AC-2 Screens follow the Figure 2 wireframes; differences listed | Sections 2 and 3 | Done, for review |
| AC-3 All controls usable with the keyboard and have text labels | Section 4; checks in section 6 | Done, for review. Screen reader not tested |
| AC-4 No recognition result, speech output or backend connection claimed | Section 5; notice on every screen | Done, for review |
| AC-5 Branch `SB-55`, issue-referencing commits, PR to `main` | PR for branch `SB-55` | Done after the PR is opened |
| AC-6 Independent approval, applicable checks and merge | GitHub | Pending |
| AC-7 Confluence record and Jira evidence links | Confluence Documentation; Jira comment | Pending until the PR is reviewed |
