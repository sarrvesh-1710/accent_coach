# UI review updates, November 9

Implemented the review priorities on top of the existing local integration.

Practice: prominent sentence, large microphone Start recording control with vector icon, optional Listen to example, secondary expandable upload, and recording review/save controls shown only after a clip exists. Stop appears during recording. Existing WAV and transcript submission boundaries remain.

Typography: 16px reading text, 14px supporting text and 32-40px page headings. Darker explanatory text, 1140px desktop shell, compact lesson sidebar, mobile stacking and reduced-motion support.

Encoding: replaced corrupted History timestamp separator, saving text and display-name helper. Explicit UTF-8 reads/writes used. Dates group by local calendar date, with readable time and status per row.

Profile: separate account and sound-preference headings, selected-sound styling, clearer sound recommendations. Model support wording remains experimental. Practice progress describes activity rather than proven accuracy gains.

History: compact date-grouped rows, sentence search, status filter and ten-row Load more. Filters/pagination operate on the existing API response of at most 100 recent attempts. No new all-history pagination, sound-level history fetches or inference calls added. Review opens the original playback/results through the existing authorized route.

How it works: shorter instructions and consistent inline SVG icons. Troubleshooting remains expandable. Privacy: plain-language summary reflecting existing local storage, training, account access and deletion limitations, plus readable spacing.

Validation: account integration 7 passed, profile preference 7 passed, profile and playback rendering wrappers passed; playback includes new review/discard and History filtering/load-more scenarios. Controlled microphone lifecycle wrapper passed (11 Node cases). Syntax, UTF-8 corruption checks, CSS block balance and diff whitespace checks passed. Rendering tests use DOM doubles; account tests use temporary stores and mocked analysis. No live browser screenshots, physical recording or performance benchmark were executed in this UI turn. App was not listening on port 7861 at inspection.

Next: launch/restart app, hard-refresh, review desktop/mobile layouts, record/discard/save, filter/review History, then capture screenshots for comparison. No backend speech logic/settings/generation changes, commit or push performed for this UI revision.
