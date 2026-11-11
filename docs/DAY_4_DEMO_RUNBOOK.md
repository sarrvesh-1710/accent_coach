# Accent Coach: Day 4 demo runbook and rehearsal status

October 18, 2026. Branch `feature/speed-free-speech`, HEAD `e7f57d9ce37f95cb6c3cc30a870c8aae284656d7`.

## Readiness decision: BLOCKED for rehearsal sign-off

The backend has Phase 4 performance/correctness evidence, but this Phase 5 browser rehearsal could not start. Automatic approval review rejected the attempted local application launch with the stated reason "blocked by policy"; the launch command did not execute. The user agreed to start the app and sign in manually, but the subsequent checks still found no reachable local server. Opening the application in the in-app browser returned `net::ERR_CONNECTION_REFUSED`.

This is an environment/access blocker, not evidence of a pronunciation-engine failure. No live browser assessment, login, upload, transcript confirmation, playback or failed-job retry passed in this phase. No startup/preparation or browser wait time was measured. This runbook is ready to follow once manual startup/sign-in is complete; the demonstration itself has not been signed off.

No application code, UI, timeouts, persistent model settings or services were changed. The approved optimization remains opt-in and **disabled in the normal app configuration**. No previously saved result was presented as a new recording's result. The uncommitted Day 3 playback fix remains preserved. No staging, commits or pushes.

## 1. Sources and prerequisite checks

Read `README.md` (current account-site launch section), `docs/INTEGRATION_COMPLETION_REPORT.md`, `docs/ACCOUNTS_SETUP.md`, `docs/DEMO_RUNBOOK.md`, the Day 3 handoff and `docs/DAY_4_PHASE_4_VERIFICATION.md`.

The older DEMO_RUNBOOK and parts of ACCOUNTS_SETUP describe the previous Gradio/preset-only release. Use the current account-site instructions below. In particular, current free speech uses private sessions and explicit transcript confirmation. Do not follow historical shared-history or preset-only screen steps as though they describe today's UI. Do not rerun installation/model-download commands during rehearsal merely because the older runbook includes them.

Observed Phase 5 preflight:

| Check | Outcome | Scope |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -B -m pip check` | Passed: No broken requirements found | Dependency consistency, not inference |
| Pinned phoneme snapshot/weights | Present locally | File readiness only |
| Pinned Whisper runtime subset | Present locally | Existing setup/check patterns: `*.json`, `*.txt`, `model.safetensors`; local-only lookup resolved |
| Whole Whisper repository snapshot lookup | IncompleteSnapshotError | Broader check than installed runtime subset; not a demonstrated inference failure; no download attempted |
| MFA executable/version metadata | Executable present; 3.3.7 | Installed metadata, not an MFA job in Phase 5 |
| MFA dictionary/acoustic archive | Both present locally | Same installation successfully exercised in Phase 4 |
| Dictionary resource cache option | Absent/disabled | Optimized Phase 4 timings do not describe the current website configuration |
| Port 7861 / `/site-health` | No reachable service in subsequent checks | Blocks the browser rehearsal |
| Browser navigation | ERR_CONNECTION_REFUSED | No app screen reached |

Readiness details are in ignored `runs/day4-demo-readiness.json`. The whole-snapshot warning was investigated using the existing installation check's narrower file patterns; no files were repaired or downloaded. Successful real Whisper/MFA/phoneme inference belongs to Phase 4, not a new Phase 5 result.

Before presenting, have the existing local account available, the same tested Python/MFA environments and pinned model files, AC power, and allowed recordings. Run only one server against `private_data`. Avoid simultaneous benchmarks or external MFA commands and keep the laptop awake during the rehearsal. Do not change power policy or remove the MFA lock as a shortcut.

## 2. Exact startup procedure

From PowerShell:

```powershell
Set-Location 'C:\Users\sarrv\Documents\Codex\2026-09-15\re\accent_coach'
Get-NetTCPConnection -State Listen -LocalPort 7861 -ErrorAction SilentlyContinue
```

If a listener exists, check the existing instance instead of launching another or killing an unknown process:

```powershell
Invoke-RestMethod 'http://127.0.0.1:7861/site-health'
```

If no app is running, start the documented entry point and leave that terminal open:

```powershell
.\.venv\Scripts\python.exe app_2.py
```

`python site_server.py` is the other documented equivalent entry point; launch only one. Open `http://127.0.0.1:7861/`, sign in manually, and open Practice. Do not share passwords in a report or chat. Use localhost only; public hosting is outside this rehearsal.

Expected health response: `service: accent-coach`, `status: ready`, `public_launch: false`. This proves HTTP readiness, not that models have loaded or inference succeeded. MFA is an on-demand CLI subprocess, not a persistent alignment daemon. Model loading occurs on first use of the app's speech worker.

Do not add `dictionary_cache_directory` or restart any shared service as part of following this runbook. Activation needs a separate approved configuration step. Do not run installation, upgrade or setup/download commands on demo day unless separately planned.

### Measure preparation independently

Start one stopwatch when launching the command and stop it at the first successful health response. Record that as **server preparation**. Separately note sign-in/manual file selection time. Start a new measurement when submitting a recording. If making a practice request beforehand to load models, log its complete cost and identify it openly as rehearsal preparation; do not subtract it from a claimed first-use latency. No preload/prewarm request was executed in Phase 5.

## 3. Recordings and consent

- Prefer a fresh, consented human recording of up to five seconds. Speaker/microphone permission is required before capture; prior permission for saved test attempts does not establish microphone consent. Microphone tests remain deferred here.
- Engineering fallback fixtures: `web_assets/examples/think.wav` (1.730 s), `ship.wav` (1.905 s), `bad_bed.wav` (2.010 s). These are synthetic engineering fixtures, not fresh human speech and not pronunciation-accuracy labels. Select them manually in the normal upload control if automated upload remains restricted.
- Additional available fixture not used in the Phase 4 planned series: `web_assets/examples/think_can.wav`, "I think we can", 2.025 s, 64,846 bytes. It is distinct from those three clips. Do not call it globally "never assessed" without checking its history; no assessment of it was performed in Phase 5.
- A genuinely previously unassessed human recording must be supplied/recorded with consent. Do not generate a new synthetic voice and describe it as human acceptance testing.
- Never use an app-generated listening-example asset as a learner upload. Generated examples are a separate listening aid and cannot serve as a substitute for the speaker's original recording.

## 4. Presenter steps: free speech

1. Open the signed-in **Practice** page. Select **Free speech** from Practice mode. Explain: "You can speak a short phrase without choosing a preset. You review the recognized words before the app checks supported sounds."
2. Choose an allowed WAV in the upload control, or obtain explicit permission and record up to five seconds. Replay the local preview and confirm the intended file/voice is selected. Do not assume a previous preview became a new recording when changing modes.
3. Press **Save and transcribe my recording** once. Start the transcription stopwatch at this click. Observe the saving message followed by transcription state. Stop at a completed/failed transcription with recognized words visible; record the outcome and time. Do not include an editing pause in analysis latency.
4. Compare **Recognized words** with what was actually said. In **What you meant to say**, correct recognition errors only as needed. Limits are 1–12 normalized words, up to 200 characters; dictionary-missing words receive coverage guidance. Correcting text does not prove the recording contains those words.
5. Press **Confirm transcript**. Check that the intended original recording remains available and **Analyze confirmed words** is enabled. Unconfirmed/unsaved edits must disable analysis and clear displayed results.
6. Press **Analyze confirmed words** once and start the analysis stopwatch. Observe `queued`/`processing` and the disabled analysis button, then the terminal `completed`/`failed` state. Current source polls at 1.5-second intervals; record visible wait, not just a server processing figure. These indicators are source expectations until observed in a browser rehearsal.
7. Review each sound outcome. **Supported** means the model favored the expected sound; **Practice** means a tested alternative was favored; **Inconclusive** means insufficient trustworthy evidence. None is a validated overall accent grade. No eligible targets means no supported coverage, not perfect pronunciation.
8. Replay **Your original recording**. Check that it is the selected learner clip, not any generated listening example. Open **My history** and the same attempt to verify saved state/playback.
9. For a repeated assessment, use **Analyze confirmed words** again only after completion. Label it as a fresh assessment of the same already-used recording in a warm worker. It must run a new job; a saved display is not a new assessment.
10. Return to Practice and upload a different allowed recording into a new free-speech attempt. Recheck its preview, recognition and confirmation. Time transcription and analysis separately. This tests different recording identity, rather than merely reopening history.
11. If relevant, choose **Hear a synthetic example** after analysis finishes. Label its output as generated speech, not voice-preserving conversion or a scoring reference. Do not overlap this generation job with speed measurements.

For an inconclusive outcome, say: "The app is withholding a judgment here. We keep uncertain evidence separate from a possible substitution." Do not correct the result orally into a pass/fail or claim sponsor speech was wrong based only on these experimental outputs.

## 5. Timing expectations and recording sheet

**No Phase 5 startup or browser timing has been measured.** Current app configuration uses the baseline path. Previous Phase 4 backend measurements can inform scheduling, but must not be relabeled as browser rehearsal results:

| Prior Phase 4 condition | Transcription | Analysis | Backend sum | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Current/default path, first think pair | 11.251 s | 20.684 s | 31.934 s | Fresh worker for ASR, then same worker for analysis |
| Current/default path, ship pair | 0.710 s | 25.365 s | 26.075 s | Reused worker; different recording |
| Current/default path, bad_bed pair | 0.993 s | 26.600 s | 27.593 s | Reused worker; different recording |
| Optimized experimental path, first think pair | 12.371 s | 10.716 s | 23.087 s | Existing dictionary resources; option not enabled in website |
| Optimized experimental path, ship pair | 0.821 s | 9.816 s | 10.638 s | Reused worker/resources; option not enabled in website |
| Optimized experimental path, bad_bed pair | 0.666 s | 9.098 s | 9.764 s | Reused worker/resources; option not enabled in website |

The optimized experiment's first dictionary-build preset request took 46.749 s; even optimized fresh-worker resource hits took 31.336–32.111 s. All six warm optimized preset requests took 10.364–15.021 s. This is not a current-browser below-20-second promise. No model-preparation cost was moved outside requests in Phase 4.

Honest presenter expectation until browser measurement: "Our latest default-backend engineering tests took about 26–32 seconds for transcription plus confirmed-text analysis; first-use preset requests took about 45–47 seconds. Browser upload, queueing, polling and editing are additional. The faster path has been benchmarked separately but is not enabled in this running configuration."

Reserve at least a minute in the presentation agenda for a fresh request as a planning allowance, not a measured guarantee. Use the wait to explain the workflow. Do not claim a percentage timer or force a successful result by changing timeouts.

| Phase 5 case | State | Preparation | Visible transcription wait | Confirmation/edit time | Visible analysis wait | Outcome |
| --- | --- | --- | --- | --- | --- | --- |
| Server start to HTTP-ready | Blocked | Not measured | n/a | n/a | n/a | Automatic launch denied; manual startup pending |
| First free-speech fixture | Blocked | No model preparation executed | Not measured | Not measured | Not measured | Server unreachable |
| Repeated same recording / warm worker | Not tested | Not measured | Not measured | Not measured | Not measured | Browser prerequisite blocked |
| Different allowed recording | Not tested | Not measured | Not measured | Not measured | Not measured | Browser prerequisite blocked |
| Previously unassessed human clip | Blocked | n/a | Not measured | Not measured | Not measured | Fresh consented clip not supplied |
| Failed analysis, retry and stale display | Not tested through browser | n/a | n/a | Not measured | Not measured | No legitimate browser job failure observed |

When filling this sheet, retain slow runs/failures and record attempt ID, revision, selected filename, recognition, confirmed text, worker restart evidence and terminal state. Do not assume fresh/warm state from speed alone. Resource-cache hits are not possible under the current disabled setting; model-object reuse is a separate kind of cache. Do not clear caches, restart the server or inject settings to produce a preferred demonstration time.

## 6. Retry, stale results and recovery

Source inspection establishes the intended backend behavior: retry begins a new job ID for the current revision, clears old analysis sound results/error, deduplicates an already-active submission, and accepts publication only if job/revision/audio/text remain current. Transcript changes invalidate results. Phase 4 regression evidence covers revision/stale publication, ownership, role separation and timeout/cleanup. **It does not replace a Phase 5 browser failure-and-retry check.**

For a legitimate failed analysis observed during rehearsal:

1. Record the exact displayed message, attempt and current confirmed text. Keep old results out of the current-results area; inspect the failed state rather than calling it a pronunciation failure.
2. Wait for the terminal state. If the input remains valid and the error is transient, click **Analyze confirmed words** once to retry the same current revision. Observe old sound results cleared and a new queued/processing state.
3. If audio is unusable, return to Practice and make a new permitted recording; verify the new preview, recognition and confirmation before analysis. Repeating invalid audio is not recovery.
4. If text is edited, confirm the new text and ensure previous sound results/generated links are invalidated. An unsent edit must not leave a previous assessment displayed as current.
5. Record whether recovery completed. If no operational failure arises naturally, mark failed-job browser retry **not tested**. Do not kill workers, corrupt caches, edit configuration or fabricate a failure to check this box without separate authorization.

| Failure mode | Safe response |
| --- | --- |
| Connection refused / no health endpoint | Confirm the local launch terminal is running. No live inference can be shown until it is reachable. Do not call it an assessment failure. |
| Port already in use | Check the existing instance's health/address. Do not launch another server or stop an unrelated process. |
| Signed out / expired session | Sign in manually and reopen the relevant attempt. Never put credentials into slides/logs/chat. |
| Microphone denied/unavailable | Use a permitted prerecorded WAV through the ordinary control. Do not secretly change browser permissions. |
| Upload too large/long or invalid WAV | Use a genuine readable recording within five seconds and 10 MiB. Do not bypass validation or silently claim a clipped recording represents the original full utterance. |
| Missing dictionary word | Explain missing vocabulary coverage; select a supported phrase or have the speaker genuinely record revised words. It is not proof of mispronunciation. |
| ASR disagreement | Review/correct intended text; keep resulting diagnostic evidence inconclusive if content remains unverified. Do not force it into a positive judgment. |
| Busy / queued | Wait for the active job. Avoid repeated clicks or parallel benchmarks. |
| Slow processing | Leave the request running while explaining the workflow. Do not reuse an old result as its outcome. |
| MFA/worker timeout | Preserve the displayed failure and recording. Existing MFA limit is 120 s and worker deadline 180 s plus cleanup. Retry only after terminal failure; do not remove locks or change limits. |
| Model unavailable | Show the honest unavailable state and use the fallback. Investigate setup after the presentation; do not download/install during it without a separate plan. |

## 7. Practical fallback for the sponsor

If live analysis is slow, continue describing recognized-text review, original playback and privacy while the actual job runs. If it fails or the app cannot start:

1. Explicitly state: "The live assessment is unavailable right now. This is a previously measured engineering example, not a result for the recording we just made."
2. If the website is accessible, open a clearly identified completed earlier attempt in **My history**, state its date/recording, and explain its experimental outcomes. Do not transfer those labels to the current speaker or silently replace the active job's result.
3. If the website is unavailable, open `docs/DAY_4_PHASE_4_VERIFICATION.md` locally to show the actual measured timings and test scope. Its evidence is three synthetic fixtures, not a live sponsor assessment. Raw audit evidence is in `runs/day4-phase4-20261018T194539Z/measurements.json`.
4. Explain that supported/practice/inconclusive are experimental sound findings and overall grading/human accuracy remain unvalidated. Generated listening examples are not converted user voices.

This fallback uses real prior evidence with explicit provenance. No synthetic input, screenshot or cached assessment is represented as a fresh human result.

## 8. Remaining sign-off checks

- [ ] App reachable at localhost with correct HTTP health, and presenter signed in.
- [ ] Server launch-to-ready preparation measured separately.
- [ ] First, repeated and different-recording free-speech browser flows timed end to end.
- [ ] Selected original recording, recognized/confirmed text and current attempt identity verified.
- [ ] Loading states, completion/error messages and original playback observed.
- [ ] Transcript edit clears/invalidates previous results in this build's live browser.
- [ ] A legitimate failed-job retry checked safely, or explicitly left untested.
- [ ] Fresh consented human correct/substitution/repetition/contraction/unknown-word/unusable-audio cases completed separately from synthetic engineering rehearsal.
- [ ] Presenter can explain the disabled-cache/current-speed distinction and demonstrate the honest fallback.

Until the manual launch and browser workflow are observed, the evidence supports a tested backend and a prepared runbook, **not a completed live-demo rehearsal**.
