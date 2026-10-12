# Accent Coach implementation report

Date: October 11, 2026

## Outcome

The local, reference-free practice app now has 12 lessons, saved-attempt review and deletion, bounded processing with recovery, and reproducible setup and evaluation tools. It remains an experimental practice system. It does not provide a validated pronunciation percentage, pass/fail grade, or general accent score.

## Changes completed

### Lessons and learner results

- Expanded the original three sentences to 12 presets: four each built around think, ship, and bad.
- Centralized sentence text, assessed contrasts, allowed transcript variants, hints, and practice sounds in prompts.json. Configuration validation catches duplicate IDs, missing/repeated target words, missing practice hints, and invalid lesson links.
- The new lessons need no reference WAV. The beginner app explicitly runs with compare_reference=False. Legacy optional reference paths remain for the original app's compatibility, but app_2 does not load them for assessment.
- Kept recognized words separate from phoneme-model evidence. Saved results now include recognized-word insertions, omissions, and substitutions for investigation. A recognizer mismatch still causes abstention.
- Assessment remains limited to TH versus S/T/F, IH versus IY, and AE versus EH in the configured target words. Other displayed sounds are written practice guidance.

### Saved attempts

- Added a collapsible history section, filtered by the selected lesson, with earlier experimental outcomes and audio playback.
- Added deletion of a selected completed attempt and its saved audio, requiring an explicit confirmation checkbox.
- Restricted history operations to valid run folders and canonical audio paths. Path traversal, symlinks, and Windows junctions are refused.
- Saved attempts remain until deleted. Gradio's separate upload/playback cache expires after about 24 hours while the app runs. Deleting a run does not instantly erase copies already cached in a browser.
- No existing learner recording was deleted during implementation; deletion tests used temporary test folders.

### Reliability

- Added a reusable CPU worker so successful attempts can reuse loaded models.
- Added a 180-second worker deadline, Windows process-tree cleanup, and a fresh worker after a timeout. MFA has its own 120-second timeout and subprocess cleanup.
- Added a shared OS file lock for MFA across app instances. Testing exposed a missing acoustic-model file when simultaneous processes used MFA's extraction cache. The affected lesson completed after the lock fix.
- Limited the Gradio queue to eight waiting requests and one active analysis. Direct concurrent worker requests are rejected.
- Added a 10 MB upload limit and backend channel/sample-rate limits before full decoding, alongside existing format, duration, silence, and sample validation.
- Saved stage processing times. Actual checks on this laptop took about 55–61 seconds with a cold worker and 35–42 seconds for subsequent valid speech. These are observations, not guaranteed response times; MFA dominated the elapsed time.

### Setup and validation tools

- Added an installation checker and explicit one-time download tool for the existing pinned speech models. Beginner-app model inference uses local caches with offline mode enabled.
- Added evaluation metrics separated by sound and speaker split. Metrics report decisions, uncertainty, false support, false alternatives, coverage, and agreement only for reviewer-labeled examples.
- Added checks against mixing a speaker between development and held-out splits.
- Added an export of actual target intervals and recognized words for human alignment review.
- Added a release snapshot containing source hashes, Git base, dependency versions, and model revisions. This records the tested working copy, including uncommitted files.
- Wrote DEMO_RUNBOOK.md and VALIDATION_PROTOCOL.md with setup, rehearsal, data collection, and deployment requirements.

## Verification completed

| Check | Observed result |
| --- | --- |
| Repository suite | 71 tests run: 70 passed, 1 skipped because Windows did not allow creating a symlink |
| Phoneme-scoring self-tests | 15 passed |
| Dependency consistency | pip check reported no broken requirements |
| Installation | Local model caches and MFA 3.3.7 ready |
| Dictionary and phone mapping | All 12 lessons covered; 25 distinct words and 40 mapped labels checked |
| Real pipeline operational checks | 18 passed: 12 synthetic lesson clips, 5 invalid/mismatch controls, 1 existing unlabeled partner recording |
| Additional audio controls | Very quiet input and seeded white noise both produced insufficient evidence rather than positive sound feedback |
| Timeout/concurrency recovery | Worker reuse, timeout recovery, MFA lock exclusion/release after process termination, and subprocess cleanup tested |
| History | Temporary-folder read/delete/path checks passed; existing saved-attempt selection and audio player inspected in the browser |

Evidence files are under runs/: release-tests-final.log, scoring-tests-final.log, release_smoke.json, audio_failure_checks.json, pronunciation_audit.json, setup_check.json, alignment_review.csv, and demo_release.json. Runs and recordings remain excluded from Git.

The operational checks establish that these inputs can be processed or rejected appropriately. Synthetic speech and one unlabeled human recording do not establish pronunciation accuracy. The affected lesson was rerun after the MFA lock fix; earlier passing operational cases were retained in the smoke report. Final automated tests exercised the later timeout-cleanup change.

## Work still required before the presentation

1. **Human validation:** Complete the planned 36 recordings and human sound labels, with speaker S03 held out from tuning. The current manifest has 0 recordings attached and 0 human-reviewed labels. Existing ad hoc clips have not been relabeled as this evaluation set. A second teammate should review disagreements.
2. **Boundary review:** Listen around exported target intervals and label whether MFA covers the intended sound. Numeric bounds and dictionary coverage alone do not validate alignment.
3. **Live rehearsal:** Test microphone permission/capture on the presentation laptop, a normal example, a deliberate sound change, a wrong sentence, and a retry. Confirm history playback and delete a disposable attempt. Browser capture was not exercised with a person speaking during this run.
4. **Review and share the build:** Review the source changes and commit the agreed version to the team repository. This implementation has not been committed or pushed. Keep model/audio assets and private settings out of Git.
5. **Frontend review:** Apply the team's next visual and language suggestions after agreeing on the final learner flow. This pass focused on functionality and reliability.

## Limits and deferred work

- No new pronunciation training or threshold calibration was performed. MFA aligns sounds; it does not itself grade pronunciation. Recognition and phoneme evidence can disagree.
- New lessons have configuration, dictionary, and synthetic operational checks, but no human accuracy validation. Arbitrary custom sentences remain outside the supported UI.
- The app is a local single-user service on 127.0.0.1:7861 with sharing disabled. Public multi-user hosting remains separate work: destination and capacity, authentication, per-user recording ownership, file-route isolation, retention, HTTPS, and deployment testing are still required. This run did not publish a website.
- Treat the demonstration as experimental, reference-free feedback on selected sound contrasts. Do not describe the test pass count as a learner pronunciation grade or claim a percentage of general project accuracy.

## Suggested team responsibilities

- **Sarrvesh:** Recording-quality cases, CPU timing/rehearsal, and reviewing audio around target boundaries.
- **Lucas:** Human sound labels and CTC/MFA disagreement review; run the held-out evaluation without tuning on held-out speakers.
- **Parthiban:** Live user-flow checks, history/retry behavior, and the upcoming frontend revisions.
- **Whole team:** Resolve reviewer disagreements, freeze the reviewed source version, and prepare representative demo clips plus screenshots.
