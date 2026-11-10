# Result and feedback improvements

Follow-up: `RESULT_AUDIO_RELIABILITY_2026-11-10.md` records the subsequent audio-readiness and copy refinements. In particular, original playback now preloads metadata instead of using the earlier lazy-only audio behavior described below.

## Scope and preservation

Implemented the supplied output-screen review in the existing preset and confirmed-text result renderers. This change edits `web_assets/accounts.js`, `web_assets/ui-polish.css`, and `tests/session_playback.cjs`; it adds this report and local test/preview evidence under `output/`. Existing uncommitted integration, playback and other UI work was preserved. Branch: `feature/speed-free-speech`; HEAD: `529e28e79fd996b228f8d8309a0642aee5caea6b`. Nothing staged, committed, merged or pushed.

The shared backend contract, stored results, authentication/ownership checks, input revisions, recording limits, transcription, alignment, phoneme model, generation setup and speed caches were not changed. `git diff --exit-code HEAD -- accounts/sessions.py accounts/practice_jobs.py confirmed_analysis.py assessment.py speech_content.py pipeline.py phoneme_scoring voice_generation` passed.

## What changed

- Sound observations now appear immediately below the sentence title in structured cards: sound and word, outcome, explanation and a general practice tip where appropriate. `TH` is a learner label, not an invented `/TH/` phonetic transcription. Indexed occurrences retain word positions and occurrence IDs.
- Completed results have one small **Saved to My history.** line. Repeated completion banners and the generic completed-state explanation no longer dominate the screen. Loading indicators and the existing duplicate-submit guard remain.
- A sentence discrepancy shows **Selected sentence** versus **Recognized words**, explains that either speech content or transcription may differ, and does not show a positive sound card. Missing target words are named where possible. The recognized transcript is not treated as ground truth, and no lesson is switched automatically. Explicit backend `target_variant` results remain accepted variants.
- Presentation reasons distinguish sentence discrepancy, unverified words, insufficient evidence, unsupported coverage, detected audio problems and processing failure. Existing flags and error codes drive these messages; quietness or distortion is not invented from an inconclusive sound result. Raw evidence remains in the details/export.
- Recovery actions match the result: re-record the selected sentence, try the sentence again, replay the original, review confirmed text, or retry the existing confirmed-text analysis job. Unsupported coverage suggests another sentence rather than marking pronunciation wrong.
- **Continue to sentence N** uses an existing server-persisted practiced step and a subsequent plan step. Rendering does not advance or rewrite plan progress. Discrepancy recovery takes priority over continuation. General practice offers another sentence or a repeat.
- **Your recording** and **Example pronunciation** label different players. Existing playback coordination pauses other audio. Preset examples are loaded/played only on an explicit click; generated examples remain separate and optional.
- Transcript editing and analysis controls collapse after completion, with a review action for discrepancies. Editing clears the prominent findings immediately and preserves original playback. Repeating custom text retains the intended words without reusing the old recording as new input.
- Details, timing, export and History are secondary utilities. Deletion sits in **Attempt options** with an explanation and confirmation naming both the recording and analysis results.
- Result paragraphs have readable line lengths, related blocks use consistent spacing, audio fits its container, controls wrap, and no result card has a fixed height.

## Browser evidence

Read-only inspection/replay of existing saved results was used; no new transcription, analysis, generation or deletion was submitted for this UI change.

| Actual saved case | Observed behavior |
| --- | --- |
| Matching preset, `41f58768866d4cf9b8c0c2909b9ba3da` | Structured TH/think card, Expected sound favored, conservative qualification, repeat/continue-practice action and one save status. |
| Discrepancy preset, `105569633dfb4c1d987fc8cd2bf6c612` | Selected I think so; recognized The ship is here. Explicit target-word-not-confirmed explanation, re-record/replay actions, no positive pronunciation claim. Raw saved content status was mismatch and target evidence insufficient. |
| Confirmed free speech, `485c67008fd740edabb67720fcb2b725` | Separate inconclusive TH/IH cards, explanatory recovery, original 3.18-second audio played through the new replay button. Asset `845e3924c9ef494bafd9c2b036a29339`, revision 3 and saved analysis timings remained unchanged between Practice and History. |

The saved model outcomes are evidence of presentation/integration, not a new pronunciation-accuracy validation. The previously saved 71.56-second analysis timing was reused, not measured again by these UI checks.

Evidence: `output/feedback-live-supported-20261110.png`, `output/feedback-live-inconclusive-20261110.png`, and `output/feedback-final-live-discrepancy-20261110.png`.

The browser viewport override did not resize the live tab: requested mobile widths still measured 1664px. Those attempts are explicitly **not** mobile passes; see `output/feedback-ineffective-viewport-checks-20261110.json`. Responsive verification instead used production JavaScript/CSS inside same-origin, sample-data browser frames at outer widths 360, 390, 768 and 1140px. All 16 combinations of matching, discrepancy, limited-evidence and failure states had scrollWidth equal to clientWidth. Windows scrollbars reduced their measured content widths to 340, 370, 748 and 1120px. This verifies responsive CSS, not a physical phone, touch input, microphone permissions or mobile decoding.

Frame evidence: `output/feedback-frame-responsive-checks-20261110.json` and `output/feedback-frame-discrepancy-390-20261110.png`. In the frame, keyboard Tab reached the replay action with a solid focus outline. The explicit example action played the existing 1.73-second `think.wav` asset; this was static-example playback, not model generation or a learner acceptance recording.

## Tests

- `node --test tests/session_playback.cjs`: final run **61 passed, 0 failed**. Includes the existing playback/stale-response tests and new discrepancy, structured ordering, single-save-status, accepted variant, unverified content, evidence limits, audio flag, retry/revision, unsupported occurrence, plan continuation, safe text rendering, edit invalidation, repeat-context and example-failure cases. These are controlled DOM/HTTP doubles, not real speech inference.
- `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'`: **245 entries, 244 passed, 1 skipped**, 75.919 seconds. Log: `output/result-feedback-regression-final-20261110.log`. Existing deprecation and unclosed-event-loop warnings remain. This broader run preceded the final small example-playback/status adjustments; the final 61-case renderer rerun covered those adjustments, and browser playback also verified the explicit example action. The broad suite was not repeated afterward. Completion save lines now have status semantics; screen-reader speech itself was not tested.
- `node --check web_assets/accounts.js` and `git diff --check` passed. Git reports the existing Windows LF/CRLF normalization notice for the test file; no wholesale file formatting was performed.

## Speed impact and tradeoffs

No additional ASR, MFA, phoneme inference, automatic synthesis, polling interval or database operation was added to produce the new explanations. The UI consumes the response already obtained by the current workflow. Work added is bounded text comparison and DOM formatting. Audio uses `preload=none`, so browser downloading/decoding is deferred until requested. Clicking an example or replay can load an audio file; explicitly requesting synthetic generation still has its existing separate runtime cost.

This supports preserving the current inference path; it is **not** a measured end-to-end latency guarantee. No comparable before/after speech benchmark was performed for this presentation-only change. The previously observed slow startup/model/memory behavior remains a separate unresolved performance issue.

Gains: clearer distinction between word mismatch and sound uncertainty, more honest evidence presentation, fewer competing completion messages, specific recovery and continuation actions, labeled playback, and preserved original results in History/export.

Costs and limits:

- Technical details and completed transcript controls require expansion. Native players may not show duration before first playback because preload is disabled.
- Conservative word verification can suppress a positive-looking raw result when content is unconfirmed. ASR can be mistaken; replay/review is intentionally offered before another assessment.
- Preset sessions remain fixed exercises. They offer re-recording rather than pretending to edit/retry a fixed legacy job. Editable transcript review and same-recording analysis retry use the existing custom/free-speech flow. From History, repeating custom/free speech first opens its saved Practice context instead of silently selecting a default preset.
- Practice tips are general guidance. No new score, calibration, supported phoneme coverage or pronunciation-accuracy improvement is claimed.
- Broader fresh-human acceptance cases, physical-phone testing and increased browser zoom remain unverified. Starting-check completion rules and their existing distinction between practice activity and pronunciation accuracy remain unchanged.

Refresh the app page to load the versioned JavaScript/CSS; these changes do not require a model or backend restart.
