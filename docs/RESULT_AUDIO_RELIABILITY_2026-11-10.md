# Result refinement and original-recording reliability

Follow-up to `RESULT_FEEDBACK_REVIEW_2026-11-10.md`, implementing the supplied 86/100 output review. Changes remain local on `feature/speed-free-speech`, HEAD `529e28e79fd996b228f8d8309a0642aee5caea6b`. Existing uncommitted integration, playback and speed work was preserved. No staging, commits or pushes.

## Implemented

- Original recordings now use **metadata preload**, replacing the previous deliberate `preload=none` behavior. The UI shows **Loading your recording…** and hides the native player until valid, positive-duration metadata arrives. It never invents a duration.
- Media errors show **Your recording couldn’t be loaded**, with **Retry loading recording**. Retry reloads the same authenticated audio URL; it does not submit analysis or transcription. Stalled loading offers recovery while still allowing a subsequent metadata event to complete normally. Zero, non-finite or invalid durations do not expose empty controls.
- Audio events are guarded by source generation, the requested URL and native currentSrc. Old metadata/error callbacks cannot reveal or fail a replacement recording. A queued error with no current native MediaError is ignored. Same-source session updates do not reload audio; preset polling now reuses its original player rather than rebuilding/refetching it. Hidden playback is stopped on result-read errors and when switching away from a preset.
- Missing target words have a short, specific heading, such as **We couldn’t confirm “think”**. The short explanation and selected/recognized comparison follow. If the target word appears but surrounding words differ, the message explains the existing full-sentence eligibility requirement instead of claiming the word is absent.
- Case/punctuation-only differences do not become a sentence discrepancy. Contradictory legacy content metadata stays unverified rather than upgrading a raw score. Accepted target variants keep their existing semantics. Backend content/phoneme eligibility and model outcomes are unchanged.
- In discrepancy/unverified views, **Your recording** sits immediately below the word comparison, followed by recovery actions. Replay operates on that same player. Custom/free-speech transcript review remains available through the existing confirmation flow.
- Matching results have one prominent observation, **This check favored the TH sound.** The tested-alternatives qualification is smaller. Word-position text is shown when needed to distinguish repeated word/sound occurrences; stable IDs remain in the data.
- One quiet **Saved to My history.** status is now in the result header, visible without scrolling past utilities. It appears only after a successful saved-result read. Result-read failures do not claim that saving or analysis succeeded; no new persistence status or backend transaction semantics were invented.
- Completed inconclusive/practice steps may offer **Continue to sentence N** only when existing server-persisted plan progress permits it. Word/sentence discrepancies and audio/processing problems keep recovery actions. Rendering never advances plan progress.
- Related spacing is tighter without reducing body readability. Mobile comparison fields and actions stack. Measured live typography was 28px result title, 21px outcome heading, 16px body, and approximately 44px action height. Details/deletion remain secondary.

## Verification

### Executed tests

- `node --test tests/session_playback.cjs`: **76 passed, 0 failed**. Controlled DOM/HTTP/media doubles cover loading/ready/error/stalled states, metadata-only retry, invalid durations, stale callbacks/currentSrc, audio reuse, discrepancy ordering, edit invalidation, punctuation/case, surrounding-word mismatch, save-status acknowledgement and persisted-step continuation. Log: `output/feedback-audio-tests-final.log`.
- `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'`: **245 entries in 58.381s; 244 passed, 1 skipped**. Log: `output/feedback-audio-regression-final-20261110.log`. Existing deprecation and unclosed-event-loop warnings remain. JavaScript cases are included through a wrapper; do not add the two test counts as independent totals.
- `node --check web_assets/accounts.js` and `git diff --check` passed. Git reports its existing LF/CRLF normalization notice for the JavaScript test file.

### Actual saved-recording browser checks

No analysis, transcription, generation, deletion, microphone capture or plan mutation was submitted during this verification.

| Saved case | Observed result |
| --- | --- |
| Matching preset `41f58768866d4cf9b8c0c2909b9ba3da` | Correct original source, automatic **2.474667s** metadata, nonempty player, concise observation, quiet save status and continuation based on the current saved plan. |
| Discrepancy preset `105569633dfb4c1d987fc8cd2bf6c612` | Dynamic think-not-confirmed heading, selected I think so versus recognized The ship is here, original **2.304s** player directly below comparison, real playback, recovery action. The same source/duration remained after opening History and refreshing. |
| Free speech `485c67008fd740edabb67720fcb2b725` | Original asset `845e3924c9ef494bafd9c2b036a29339`, automatic **3.18s** metadata and real playback. The same original source/duration appeared after History navigation and refresh. |

Both the discrepancy preset and free-speech recording were explicitly played again after opening History and refreshing: native players reported `playing=true`, with durations 2.304s and 3.18s and the correct distinct source URLs. This was a playback check, not just a metadata check.

Browser negative check: a sample-data result intentionally referenced a nonexistent audio file on the temporary preview server. The real browser received HTTP 404, hid the empty native player and displayed the recording-load error and retry. Retrying kept the same source and correctly returned to an error while the file remained absent. This is a browser/media wiring test, **not** a production storage failure or a human pronunciation result. Recovery to ready is covered by controlled media tests; no real account asset was broken to force that case.

Responsive verification used the production JavaScript/CSS in same-origin sample frames, since the browser viewport override did not reliably resize the live tab. Sixteen combinations of matching, discrepancy, limited evidence and processing failure at outer frame widths **360, 390, 768 and 1140px** had no horizontal overflow, including the audio-error/retry state. Measured content widths were 340, 370, 748 and 1120px because of Windows scrollbars. These are browser-rendered CSS checks, not physical-phone acceptance.

Evidence:

- `output/feedback-audio-final-live-20261110.png`
- `output/feedback-audio-live-matching-20261110.png`
- `output/feedback-audio-responsive-20261110.json`
- `output/feedback-audio-sample-error-390-20261110.png`

## Speed and remaining limits

The deliberate tradeoff is an automatic original-audio metadata request when viewing a result, instead of waiting for Play. Depending on the browser, this can fetch part or all of a short WAV and perform some browser audio work. It improves duration/readiness and error visibility, but is not zero-cost I/O. Same-source polling avoids redundant reloads, and result rendering does not wait for metadata to show the analysis outcome.

There are **no extra ASR, MFA, phoneme-analysis or automatic generation calls**. Model settings, caches, concurrency, timeouts, authentication, revision checks, recording limits and stored findings were not changed. No new end-to-end latency benchmark was run and no under-10-second guarantee or model-speed improvement is claimed. Earlier startup/memory/latency limitations remain separate work.

Files changed for this follow-up: `web_assets/accounts.js`, `web_assets/ui-polish.css`, `tests/session_playback.cjs`, this report, and a follow-up pointer in the previous report. Local preview/test evidence remains under `output/`. Temporary preview serving was stopped; the actual app was not restarted.

Fresh-human pronunciation accuracy, physical-phone use, screen-reader speech, browser zoom and genuine database-save failure remain unverified by this UI task. The models remain experimental and no percentage grade is introduced. Refresh the page to load the versioned assets; no backend restart is required.
