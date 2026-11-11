# Speed demo runbook, October 27, 2026

## What can be claimed

The final graph-resource optimization reduced the actual website's median prepared analysis from 12.03 to 8.19 seconds across six paired runs on three recordings. Five of six optimized analyses were below ten seconds; one took 11.48 seconds. A new microphone clip completed analysis in 7.86 seconds server-side and 9.35 seconds through the browser. Transcription was a separate 4.01-second job. **A maximum ten-second combined workflow is not established.** First use is slower and must be shown separately from prepared processing.

## Start the existing local build

In PowerShell:

```powershell
Set-Location 'C:\Users\sarrv\Documents\Codex\2026-09-15\re\accent_coach'
.\.venv\Scripts\python.exe app_2.py
```

Open http://127.0.0.1:7861/practice and sign in. If port 7861 is occupied, check the already-running app rather than launching another instance or stopping an unrelated process. Do not reinstall dependencies or download models immediately before a demonstration.

The local ignored settings currently include:

```json
"mfa_execution": {"reuse_process": true, "idle_sec": 600, "reuse_lexicon_graphs": true}
```

This is machine-specific configuration for the inspected Windows MFA 3.3.7 runtime, not an approved portable server deployment. The original 120-second idle default remains when `idle_sec` is absent. `reuse_lexicon_graphs: false` disables the new memory cache; `reuse_process: false` uses the previous CLI path. Each flag is an independent safe fallback, not a speed claim. Diagnostics and profiling are disabled and should stay off for the normal demonstration. Do not replace the whole local settings file with this snippet; its existing model and MFA paths must be preserved.

## Preparation, visibly separate from the live test

1. Use AC power and save/close unneeded programs yourself. Current measurements used the existing Balanced plan. Closing Chrome increased available memory but did not establish a ten-second result.
2. Run one complete ordinary workflow: record a consented short clip, Save and transcribe, inspect the recognized words, confirm the intended text, then Analyze confirmed words.
3. Wait for the actual completion or error message. This initializes transcription and analysis components in their normal order. Reopening an old result initializes neither; reanalyzing an old confirmed session alone may not initialize transcription.
4. Record preparation cost as preparation. Observed first-use analysis reached 57.57 seconds and separate first transcription reached about 28 seconds in this session. These values came from different jobs and must not be summed as one measured startup time. The graph cache also needs its first resource read; that preparation is not an assessment-result cache hit.
5. Keep the app running. MFA can be retained for ten idle minutes in this local configuration; failure, timeout, worker restart or its 32-request retirement can require initialization again. Retention is not indefinite and does not change alignment deadlines.

## Present a genuinely new attempt

1. Click Start new practice, choose Free speech, and record the speaker with permission. Keep it within five seconds, 10 MB, twelve words and 200 characters.
2. Save and transcribe. Read the actual recognized words, then correct them if needed and Confirm transcript. Do not silently replace recognized text in the explanation.
3. Start the analysis timer when pressing Analyze confirmed words. Keep the processing indicator visible. Human review time is separate from machine processing.
4. On completion, review the sound findings and original recording in Practice. Open Analysis details to read saved server durations if needed. Browser wait includes network, queue and polling; it is not identical to the server timer.
5. Use View in History to show that the same attempt is retained. An old recording or rerun is labeled as such and is never presented as a new recording.
6. Say that supported/practice/inconclusive findings are experimental evidence, not a validated grade. Corrected text that disagrees with recognition can lead to CONTENT_UNVERIFIED and inconclusive findings.

## Slow or failed run

- Keep the real loading state visible. Do not promise ten seconds. Prepared optimized website analyses ranged from 7.79 to 11.48 seconds in the paired series, and initialization could be much slower.
- Do not start duplicate analyses. If status retrieval fails, use Check status again; it reads the existing job. If the analysis itself fails, use its explicit retry control after checking the message.
- After a timeout, recovery may use a fresh worker and take longer. Controlled tests verify cleanup/recovery; a deliberate live outage was not introduced in this rehearsal.
- If a live result is unavailable, open a clearly labeled earlier completed demonstration from History and explain when it was recorded. Replay its original recording. Do not claim it is the result of the current microphone input.
- If timing is poor, demonstrate recording, transcript confirmation and private History honestly, then explain that live MFA execution remains the speed bottleneck. No bypass of validation, stale-result checks, ownership or unsupported-sound handling is permitted.

## Before claiming the ten-second target

Resolve the actual site's MFA execution gap, then repeat paired tests with new human clips and stable conditions. Report first-use, prepared, idle-expired and retry runs separately. Verify the whole combined machine workflow if making a whole-workflow claim; analysis alone excludes transcription. Test the upper recording/text limits and queue/load conditions before calling the target a maximum.

See SPEED_COMPLETION_REPORT_2026-10-27.md for the final decision and SPEED_HANDOFF_2026-10-27.md for preserved earlier measurements. Current readiness: **demo ready with timing and validation caveats; typical prepared analysis is below ten seconds, but a ten-second maximum remains unproven**.
