# Guided practice review

Implemented the attached 90-point review without broad page rearrangement. During an active starting check, recommendations become Other practice (optional), use secondary styling, and explain that progress is retained. A recommendation repeating the current check step is hidden. Completing the check restores Practice next as the primary recommendation. The check continuation link remains available when another sentence is selected.

The current instruction follows capture/preview/analyzing/error/result state, using the same current plan and attempt response. It does not create speech jobs or poll more frequently. Completed steps move the instruction to the next saved plan step. Settings auto-collapse only on initial plan initialization and not while a control inside is focused; later progress refresh preserves a manually opened disclosure.

Shared UI outcome wording appears on results and Profile: This check favored the [phone] sound; tested alternatives prompt practice; inconclusive evidence prompts another clear recording. Experimental limitations remain visible. Profile emphasizes Review recording, with Practice again secondary. How it works uses one short sentence per step and a disclosure for limits and processing details. Existing file/text limits remain at input controls.

Validation: full suite ran 245 test entries in 51.924 seconds; 244 passed and one skipped. The account renderer wrapper includes 42 controlled cases; profile wrapper 11; microphone lifecycle wrapper 11. Added coverage for optional-path priority, duplicate check suggestions, state-aware instructions and preserved settings expansion. Deprecation/resource warnings remain in output/guided-flow-regression-20261109.log.

Browser sample-data evidence: keyboard Tab moved from expanded settings to input-mode with visible solid focus. Practice/Profile/Help had no horizontal overflow at 360, 390, 768 and 1140px. Evidence in output/ui-responsive-preview/guided-layouts.json and guided-mobile.png. This used route-generated HTML with temporary sample accounts and canned responses, not production speech inference or microphone acceptance. Physical-phone and increased browser-zoom acceptance remain unverified.

The user requested saved recordings for functional replay. The initial browser check was blocked by sign-in and an older running process. The user subsequently restarted and signed in. The November 10 live replay and its limitations are documented below; no fresh microphone results are claimed.

Core transcription, MFA, generation and backend input-revision files remain unchanged. No commit, merge, push, model installs or changes to existing user recordings.

## Live saved-recording verification, November 10

Branch remains `feature/speed-free-speech`, HEAD `529e28e79fd996b228f8d8309a0642aee5caea6b`. All existing modified and untracked integration/UI work was preserved; no staging, commits or pushes. The app health endpoint returned HTTP 200 before testing.

The real authenticated browser reopened saved free-speech attempt `485c67008fd740edabb67720fcb2b725`, using original learner asset `845e3924c9ef494bafd9c2b036a29339`. Recognized and confirmed text were both `I think so.`, input revision 3. Native playback ran successfully: duration 3.18 seconds, readyState 4, source under this attempt's authenticated original-audio route. No synthetic example was requested or assessed.

Live inspection found a navigation defect: opening a saved free-speech attempt after the plan initially rendered could leave Continue starting check pointing at the current free-speech panel. The minimal fix assigns `check-continue-link` and updates its href when the actual mode/lesson loads. Free speech also hides the entire preset listening-example disclosure. Changes are in `web_assets/accounts.js`, `web_assets/lesson_plan.js`, and the focused regression in `tests/session_playback.cjs`. The live link now points to `/practice?lesson=think&plan=1`.

Observed browser checks:

| Check | Result and evidence |
| --- | --- |
| Loading and duplicate-submit control | PASS: visible progress indicator, analyzing copy, aria-busy=true and Analyze disabled. No duplicate click was submitted. |
| Immediate Practice result | PASS: completed findings appeared in place, with Analysis complete and Saved in My history messages. |
| Identity and revision | PASS in both completed replays: original asset, confirmed text and revision 3 retained. TH and IH remained inconclusive; no pronunciation error or validated grade was claimed. |
| History persistence | PASS: navigation to View in History loaded structured JSON identical to the final Practice response, including timings, asset and revision. Returning to Practice retained the result. |
| Connection loss and recovery | Observed interruption during the attempted repeat: the app process exited/restarted without an agent restart. The UI offered Check status again, then Retry analysis, and hid old findings. Retry completed successfully. The reason for the process restart is not established. |
| Starting-check progress | Remained 0 of 3; this free-speech replay is optional practice, not a starting-check lesson completion. |

Existing instrumentation, seconds (analysis-only; transcription was reused from November 3):

| Run | Worker/environment classification | Audio stage | Alignment | Phoneme analysis | Analysis total | Outcome |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | First-use after app startup; new speech processes observed; about 1,027 MB free physical RAM of 16,077 MB | 6.710 | 27.694 | 70.872 | 115.761 | Completed, inconclusive TH/IH |
| 2 | Intended loaded-model repeat, interrupted by app restart | unavailable | unavailable | unavailable | unavailable | Connection lost; retry required |
| 3 | Retry after that restart; not a comparable warm run | 6.317 | 23.289 | 31.688 | 71.559 | Completed, inconclusive TH/IH |

Queue measurements were 0.021 and 0.082 seconds for completed runs. Listed stage timers do not cover the full analysis total. No new instrumentation was added. Process startup, model loading, disk-cache status and lock waiting are not independently isolated by this visible response. There is no valid warm before/after comparison here and no evidence that this UI work caused the latency. These runs do not establish an under-10-second guarantee. Low free memory is an observed condition, not proof of the sole cause. No power settings, apps, models, caches or timeouts were changed.

Evidence: `output/practice-live-processing-20261110.png`, `output/practice-live-result-20261110.png`, and `output/practice-live-completed-20261110.png`. These are actual saved-recording browser checks, distinct from the earlier sample-data responsive previews.

Focused verification after the navigation fix: `node --test tests/session_playback.cjs` passed all 43 controlled renderer cases; its Python unittest wrapper also passed. `git diff --check` passed. Core session/revision, transcription, MFA and generation files still match HEAD.

Complete rerun: `.\\.venv\\Scripts\\python.exe -B -m unittest discover -s tests -p 'test_*.py'` executed 245 test entries in 65.202 seconds: 244 passed, one skipped. Log: `output/guided-flow-regression-20261110.log`. Existing deprecation and unclosed-event-loop ResourceWarnings remain. This suite includes unit/mocked renderer and temporary-store integration checks; its count is not a fresh human-accuracy validation or a real-model performance benchmark. Actual real-model/browser evidence is limited to the replay cases above.

Remaining acceptance gaps: fresh microphone capture/permission-denial, all six human pronunciation cases, physical-phone use, actual 200-percent browser zoom, and broader pronunciation accuracy. Next performance work should diagnose startup/model loading and memory conditions separately, then measure uninterrupted warm runs before renewing speed claims.
