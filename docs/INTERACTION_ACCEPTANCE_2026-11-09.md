# Interaction review and verification

## Implemented gaps
- Profile warns about unsaved edits on ordinary same-window link navigation, sign-out and browser departure; cancelled navigation retains the in-memory draft. Save errors preserve edits. Successful save/discard clears the dirty state. No profile drafts are persisted in browser storage. Native departure prompts depend on browser support and user activation, especially on mobile.
- History offers Clear filters for zero matches, resets visible count on filter changes, and uses slice/re-render for Load more without duplicating rows. Connection failures offer Retry History; empty accounts link to first practice.
- Playback coordination pauses other page audio when another player starts. Starting capture or replacing the selected exercise pauses playback. Existing pagehide microphone disposal retains immediate track release. Unsaved recordings require confirmation before lesson/mode/guide changes. Cancellation preserves the clip; confirmed changes clear it. Save success removes the unsaved-recording flag.
- Processing finished labels describe job completion; experimental sound observations remain separate. Shared network/unreadable-response errors offer recovery instructions.

## Supporting flow refinements from attachment
Practice settings use a Change disclosure. It remains open for first-use selection and can close for a started preset plan. Sentence/example/capture remain together. Sidebar uses one progress label and one current-step instruction with a single About this check disclosure. Removed redundant sidebar copy. Profile has Account and Practice preferences fieldsets and hides inactive Save/Discard controls. Sound cards lead with short outcomes from actual results, followed by instructions, dates and recording links.

## Evidence
Full regression: 245 Python test entries in 58.251 seconds; 244 passed, one skipped. JS wrappers include 39 account renderer cases, 10 profile renderer cases and 11 controlled microphone lifecycle cases. Existing warnings are in output/interaction-regression-20261109.log.

Controlled cases cover unsaved cancellation/confirmation, successful/failed profile save, duplicate submissions, original/generated recording identity, stale-result display, missing results and retries; filter reset/load more/clear/retry; playback coordination; capture limit, permission failure and cleanup; and durable starting-plan progress, failed-analysis exclusion and deletion behavior through temporary HTTP/SQLite integration. These are not real-model pronunciation validation.

Browser preview uses current route HTML, local scripts and canned responses with temporary accounts. Verified keyboard Space selected a sound checkbox with a solid focus outline; profile Discard restored clean fields; real DOM History search/Clear filters recovered; returning preset plan settings were collapsed. At 360, 390, 768 and 1140px, Practice, Profile and History had no horizontal overflow, including a long sample display name and long sentence stress text. Preview fixtures do not bypass actual text limits or count as learner acceptance. Evidence: output/ui-responsive-preview/behavior-layouts.json and behavior-mobile.png. Preview server was stopped.

## Still unverified
No live authenticated saved-user browser journey, microphone capture, neural inference or performance measurement ran in this turn. Real physical-phone behavior, platform-native beforeunload dialogs, actual increased browser zoom, and end-to-end spoken error/retry behavior remain acceptance tasks. Native dialogs were tested with controlled events, not forced on the user's session. Do not call these checks passed based on the sample preview.

## Preservation and next steps
MFA/transcription/generation and backend session revision safeguards match the existing HEAD. No model configuration, installs, database migrations, persistent user-data edits, commits, merges or pushes. Existing local integration and user output preserved.

Next: launch/restart app, hard-refresh, run an authorized live recording/preview/confirm/analysis/review, test unsaved navigation and playback, then repeat at phone width and 200% browser zoom. Benchmark equivalent warm speech jobs separately before renewing latency claims.


## Small final visual adjustments
Removed duplicate visible Account legend while preserving an accessible Account details fieldset name. Hidden action row has zero measured height. Browser measurement initially found 59.18px between practice focus and saved message; corrected CSS and measured 23.99px. Helper/saved text computed 14px, body and navigation 16px. Settings copy verified as Lesson settings · Preset lesson and History badge as Ready to review. Starting instruction references the actual preset submission label Check and save my recording. Sample-data screenshot: output/ui-responsive-preview/profile-final-spacing.png.

Scoped verification after these small changes: profile rendering (11 cases), account renderer (39 cases) and seven account integration tests passed; syntax and diff checks passed. Full 245-entry suite was not rerun for these copy/spacing-only changes. No speech path changes, commits or pushes. Live microphone and actual browser-zoom acceptance still pending.
