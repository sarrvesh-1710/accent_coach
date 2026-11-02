# Teammate branch and integration review

October 27, 2026. Current branch: `feature/speed-free-speech`; HEAD remains `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`.

## Result

Fetched every configured remote (`origin`) with `git fetch --all --tags`, inspected all nine local branches and twelve remote branch heads, and independently checked advertised heads with `git ls-remote --heads origin`. No remote updates were fetched. The latest published commits authored by Lucas and Parthiban are dated October 13. Private work that has not been pushed cannot be discovered this way.

**Their active feature deliverables are already incorporated into the current application. No new source merge was necessary.** They were imported and adapted in `74978dc`, rather than joined through an ancestry merge. Git therefore still shows their feature commits as outside the current ancestry; that does not establish missing implementation. Source/payload comparisons confirmed the existing integration.

No working-tree merge, staging, commit, push, checkout, reset, stash, service launch/restart, package installation, model download, configuration change or database migration was performed. One new review document and ignored audit/test artifacts were created. All 176 previously inventoried tracked/untracked files and the local settings file retained their original content hashes. The index remains empty and `git ls-files --unmerged` is empty.

## What the teammates published

| Branch | Tip / date | Contribution | Integration decision |
| --- | --- | --- | --- |
| `origin/feature/profiles-personalization` | `76cef88`, Oct 13 | Lucas uploaded a 1,353-line patch: local accounts/Argon2 login, profiles, SQLite private attempts, authenticated playback/download/deletion, History UI, tests and setup instructions. | Already applied/adapted in `74978dc`; all 16 patch paths are present. Current account storage extends Lucas's implementation with confirmed sessions, revisions, logout cancellation, generation assets and conservative suggestions. Do not reapply the original patch. |
| `origin/feature/voice-conversion` | `09f6de1`, Oct 13 | Parthiban's five commits add local synthetic generation, optional isolated Kokoro backend/worker, a standalone generation demo, revision/timeout/failure controls, tests, timing/listening runbooks and conversion feasibility notes. They do not implement working voice-preserving conversion. | All 29 added paths exist locally: 27 match upstream after newline normalization; two are intentional contract adaptations (`voice_generation/service.py`, `tests/test_example_service.py`). Retain the adaptations. |
| `origin/lucas/mla` | `ccf99b6`, Sep 21 | Earlier MFA/alignment/scoring/model-configuration work. | Already an ancestor of HEAD. No incoming commits. |
| `origin/parth/application-feedback` | `b4d6ebe`, Sep 22 | Earlier application pipeline/feedback work and team integration. Tip itself is a Sarrvesh-authored merge; Parthiban's earlier contributions are in its history. | Already an ancestor of HEAD. No incoming commits. |
| `origin/american` | `e4117e2`, Oct 11 | Separate preset American-phoneme app, target data, root-level scorer snapshot, tests and Git bundle. Uses a 15-second scope and heuristic Correct/Incorrect labels. | Not imported into the current five-second, authenticated confirmed-text application. It explicitly lacks free-speech word verification and needs a separate compatibility/validation design. |
| `origin/chinese` | `231a8b3`, Oct 6 | Mandarin-learner profile, offline SpeechOcean evaluation/calibration tools and older app/pipeline snapshots. Does not supply trained calibration weights/corpus or voice conversion. | Not imported. Conflicts with current app/pipeline; uploaded module/data layout also differs from its import paths. Requires a dedicated port, dataset/model verification and performance study. |

Other inspected local/remote branches: `main`, `feature/speed-free-speech`, `fix/integration-interfaces`, `fix/pitch-and-phoneme-evidence`, `sarrvesh-dsp`, and `team/week1-foundation`. Their tips are Sarrvesh-authored, with no newer teammate deliverables found. The local profile and conversion branch pointers remain at the shared foundation; their remote tracking refs carry the published payloads. No teammate branch was moved or overwritten.

## Conflict review

Used `git merge-tree --write-tree --name-only --messages HEAD <remote-branch>` to inspect committed-tree merge previews. These write only Git objects; they do not modify the index, HEAD or working files, and do not model the current dirty working tree.

- Profiles: a raw merge would add the inert original patch file, not apply account changes. This would not integrate anything new.
- Generation: raw merge reports add/add conflicts in `voice_generation/service.py` and `tests/test_example_service.py`. Current versions intentionally map the approved flat fixtures and enforce 12 words/200 characters instead of the standalone demo's 1,000-character limit. Retained these already-reviewed adaptations; no actual working-tree conflict was created.
- American experiment: README content conflict; introduces a separate assessment surface outside the agreed recording/identity/feedback contract.
- Chinese experiment: README, `app.py` and `pipeline.py` conflicts. It uses an older `run_attempt(..., profile_id=...)` interface and reference-dependent general workflow. Its imports expect `phoneme_scoring/calibration.py` and `accent_profiles/chinese.json`, but those paths are absent from the uploaded branch snapshot (files were uploaded at root).
- Earlier alignment/application branches: already ancestors; previews add no changes.

No merge was manufactured merely to record ancestry, and no older experimental implementation replaced the current app. The two experimental branches remain available on origin for a separately scoped port.

## Verification executed now

Evidence directory: `runs/team-branch-audit-20261027T235356Z/` (ignored; no learner audio or production account database copied into this audit).

| Check | Command / method | Observed result |
| --- | --- | --- |
| Full current suite | `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v` | 195 tests run in 58.641 seconds: 194 passed, one existing Windows symlink-creation skip, zero failures. Log: `regressions.log`. |
| Real integrated speech/storage/generation | `.\.venv\Scripts\python.exe -B runs/team-branch-integration-smoke-current.py` | 17 checks passed. A copy of existing `tools/check_private_free_speech.py` with only its evidence destination changed; source tool untouched. Actual HTTP TestClient, temporary accounts/SQLite, local Whisper/MFA/phoneme inference, Windows synthesis, authorized generated playback and generated-reupload rejection. Log/JSON: `real-private-smoke.*`. |
| Conservative correction handling | Included in real smoke | The existing I think so recording deliberately paired with repeated-word/contraction transcripts produced inconclusive results and CONTENT_UNVERIFIED. This is a disagreement guard test, not fresh repetition/contraction acceptance. |
| Preservation | SHA-256 before/after comparison | All 176 preexisting inventoried files unchanged, including playback/Practice UI, speed modules, reliability changes and ignored local MFA settings. `verification-summary.json`. |
| Git hygiene | `git diff --check`; `git diff --cached --name-only`; `git ls-files --unmerged` | Passed; empty index; no unresolved index conflicts. Existing dirty work preserved. |

The regression suite contains unit tests, controlled subprocess/model doubles, real temporary HTTP/SQLite integration, and production JS rendering scenarios. It is not universal pronunciation-accuracy evidence. The real-model smoke is a separate executed check; it uses an existing demo recording and temporary authorized accounts, not fresh human/browser acceptance. The application was not listening on port 7861 during inspection; no live browser check or shared service restart was performed.

## Performance assessment

No incoming runtime code was added, so this review introduced no new analysis-path work. Hash verification confirms that the existing reusable interpreter, bounded ten-minute retention, dictionary resource cache and independent graph-copy cache remain intact. Local flags remain `reuse_process=true`, `idle_sec=600`, `reuse_lexicon_graphs=true`; profiling/diagnostic capture remains off.

The real smoke measured the following server job times with its existing timers:

| Operation | Processing time | Interpretation |
| --- | ---: | --- |
| First I think so analysis in this isolated run | 16.794 s | First use in this test worker; includes model/resource initialization. Not a browser/new-human timing claim. |
| Repeated-word diagnostic analysis | 3.363 s | Reused worker, changed/mismatching confirmed text, inconclusive. Different work; cannot substitute for comparable warm/new-recording latency. |
| Contraction diagnostic analysis | 3.377 s | Same qualification as above. |
| Synthetic listening example | 0.787 s | Separate Windows TTS job, not analysis or voice-preserving conversion. |

These are smoke observations, not a new controlled before/after benchmark. Previously measured website prepared-analysis median of 8.19 seconds remains historical evidence, not a guaranteed current maximum. No claim of zero future slowdown or a ten-second service bound is justified.

Existing performance risks found in the actual integrated implementation:

- Preset analysis, confirmed analysis/transcription and generation share one bounded executor (`accounts/web.py`, `accounts/practice_jobs.py`). An active generation job can therefore queue analysis. This predates this review; no speculative concurrency change was made.
- The default web generation path uses the lightweight Windows backend, requested explicitly. Kokoro's Torch/spaCy model construction is not part of normal assessment and was not enabled/downloaded. Switching to it needs separate memory/latency testing.
- Cold model/process preparation and graph-cache memory use remain known costs; multiple-user throughput and worst-case latency remain unverified.
- American/Chinese experiments have not been benchmarked against this app and were not silently connected to its request path.

## Next integration action

The active accounts/generation deliverables are already integrated locally and the executed checks pass. No additional merge or conflict resolution is pending for those published payloads. If teammates have newer work, they need to push it or provide its exact commit; no message was sent to them.

Keep the current demo path. Complete fresh-human/browser acceptance and review existing uncommitted scopes before a separately authorized commit/push. Treat American-phoneme expansion and Mandarin calibration as explicit follow-up ports, with their own contract adaptation, tests and comparable performance measurements, rather than merging their older app snapshots into the demo build.
