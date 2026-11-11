# RAM cleanup and actual-app speed retest

November 3, 2026, America/Chicago. Branch `feature/speed-free-speech`, starting HEAD `529e28e79fd996b228f8d8309a0642aee5caea6b`. Existing untracked presentation exports were preserved.

## Outcome

Three saved learner recordings were analyzed again through the running website after closing nonessential applications and connecting AC power. Their new server-side analysis jobs took **8.966, 8.339 and 9.934 seconds**: median **8.966 seconds**, range **8.339–9.934 seconds**, three completed, no observed failures or repeated jobs in this planned group. They reused previously completed transcription and are analysis-only reassessments, not newly recorded acceptance cases.

A subsequent fresh microphone recording completed independent transcription in **5.190 seconds** and analysis in **9.238 seconds**, totaling **14.428 seconds of server processing**. Its two queue waits add approximately 0.097 seconds. This sum excludes recording/upload, browser polling/rendering and the learner's transcript review/confirmation. It is not a browser stopwatch result or a complete under-ten-second workflow.

All four current analyses were below ten seconds server-side, but the longest was only about 0.066 seconds below the target. Browser-visible completion can exceed ten seconds. The sample does not establish a maximum, a reliable 95th percentile or a service guarantee.

## Cleanup and conditions

- Initial available physical memory was approximately **1.25 GiB** out of 15.70 GiB usable. The laptop was on battery.
- Under the user's explicit authorization, closed Adobe Creative Cloud and its UI/background helpers, WhatsApp, Phone Link, Photoshop Express, Postman Agent and Muse Hub. Sixteen matching processes were closed. No startup settings, security services, power settings or memory-clearing utilities were changed.
- Immediately afterward, a Windows snapshot showed approximately **2.67 GiB available**. Subsequent samples varied; observed available memory during the saved jobs was roughly **1.9–2.4 GiB**, and the fresh workflow sampled approximately **2.4–2.5 GiB**. WhatsApp automatically restarted later; it was observed rather than repeatedly killed during measurement.
- The user connected AC power, verified by battery-status snapshots. The power plan remained Balanced.
- Accent Coach, its loaded speech worker, Chrome, this chat and essential system processes were preserved. No application/service restart or competing analysis/model benchmark was started by the investigator. Initial stored queues had zero active jobs; the user ran tests sequentially and did not request generation.
- Application process PID 28840, speech worker PID 17316 and MFA PID 5996 were observed unchanged before/after the retest. MFA had been created earlier at 09:41:13 Central. This supports classifying these as prepared-process runs. It does not provide per-request graph-hit counters for the free-speech results.
- The model IDs/revisions, CPU configuration, private ownership, recording limits, text limits, locking, deadlines, cache settings and 600-second MFA idle retention were unchanged. SHA-256 checks of 13 protected code/settings files matched before and after.

## Method

Browser automation was unavailable in this session. The user operated the actual running website, opened the three specified saved Free speech sessions, clicked Analyze confirmed words once for each, and waited sequentially. The investigator observed existing saved job times and identities using read-only SQLite connections plus Windows memory/process readings. This is actual-model, user-operated website execution, not investigator-driven automated browser acceptance and not an isolated duplicate worker.

The saved clips were the existing I think so, The ship is here and That is a bad bed recordings, 48 kHz mono WAVs within five seconds/10 MB. Each qualified result required a **new analysis job ID** compared with the initial snapshot. Opening/confirming a session can update timestamps while retaining previous timings; those timestamp-only events are retained in the raw observer evidence and **excluded** from the new-run counts. The final three results were independently re-read and qualified by new job ID and terminal status.

No result cache was used to supply these timings. The current pipeline performs fresh alignment/scoring for each new job; only initialized models and dictionary resources are reused. Per-request MFA lock-wait, subprocess duration, graph hit/miss status and internal startup were not retained in these session snapshots and are therefore **not separately measured for the post-cleanup group**. No new application instrumentation was added or enabled to manufacture that breakdown.

## Saved-recording runs

Seconds except clip size. Transcription was **not rerun** in any of these rows; older transcription timings displayed in the saved sessions are not current measurements.

| Clip | Duration | WAV bytes | Analysis queue | Audio stage | Alignment operation | Phoneme analysis | Server analysis total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| I think so | 2.475 | 237,646 | 0.031 | 0.026 | 6.083 | 2.342 | **8.966** |
| The ship is here | 2.040 | 195,884 | 0.027 | 0.018 | 5.577 | 2.233 | **8.339** |
| That is a bad bed | 3.480 | 334,124 | 0.016 | 0.025 | 5.975 | 3.376 | **9.934** |

The stage columns do not sum exactly to the outer job total; remaining validation, text preparation, IPC and adapter work are not separately assigned invented times. Mean analysis time was 9.080 seconds. These are server timings rather than click-to-visible-completion timings.

For all three: attempt identity, original learner-audio identity, confirmed text, input revision and source recording SHA-256 matched the initial snapshot. Word/sound occurrence identities and outcome/reason categories matched previous results. Think and ship retained their supported findings; bad-bed retained three inconclusive findings. Completed processing and outcome consistency do not establish pronunciation accuracy.

## Fresh microphone workflow

The user selected Start new practice, recorded I think so through Free speech, saved/transcribed, reviewed/confirmed the words and analyzed. The recording was **3.180 seconds**, **305,324 bytes**, 48 kHz mono WAV. Its bytes differ from all 14 distinct earlier saved learner waveforms inspected before the new workflow. The user explicitly confirmed completing the test.

| Measurement | Seconds |
| --- | ---: |
| Transcription queue | 0.063 |
| Independent transcription processing | **5.190** |
| Analysis queue | 0.035 |
| Analysis audio stage | 0.025 |
| Analysis alignment operation | 5.540 |
| Analysis phoneme stage | 3.149 |
| Analysis total | **9.238** |
| Transcription plus analysis processing | **14.428** |

Recognized text and separately confirmed text were both `I think so.` The recording has learner role, its hash matches the transcription provenance, the analysis job/revision matches the confirmed session, both jobs completed, and generation was not requested. Recording/text limits were satisfied. The resulting TH and IH findings were both **inconclusive / INSUFFICIENT_EVIDENCE**; they were not relabeled as correct or incorrect. This is one fresh human timing/processing case, not completion of the six-case human accuracy protocol.

## Startup context and comparison limits

Before cleanup, today's first saved preset assessment took **111.640 seconds before saving**, with 68.343 seconds content checking, 7.255 seconds audio preparation, 29.848 seconds alignment and 5.853 seconds phoneme scoring. Its MFA metadata reported a compiled dictionary hit, a new MFA process, zero graph hits/two misses, 9.719 seconds interpreter startup, 28.171 seconds subprocess duration and 0.0012 seconds lock wait. Those startup and subprocess figures overlap and must not be added together. The preset's overall result was partial, not a claim of perfect pronunciation.

That earlier preset is **not a paired before/after RAM experiment**: the later group used confirmed sessions, reused transcription/models/graphs, and ran on AC power. The fresh complete workflow also has a different waveform and warm resources. The improvement in current responsiveness is observed, but the number of seconds caused by RAM cleanup versus power, initialization and other conditions cannot be isolated from this series.

No forced fresh-worker restart was introduced: the point was to preserve the loaded application for a practical demo retest. Existing saved initial timings supply startup context, not a newly controlled cold-start comparison. Windows still sampled page-ins after cleanup; sufficient headroom on every future request is not proven.

## Conclusions and next step

The current prepared **analysis-only** path met ten seconds in these four executions. The fresh transcription-plus-analysis path did **not** meet ten seconds. Alignment remains the largest named stage within analysis (about 5.5–6.1 seconds); independent transcription added 5.190 seconds in the one new workflow. Phoneme analysis added about 2.2–3.4 seconds in this group. Queue waiting was negligible.

For a demo, keep this prepared process available, use AC power, close unneeded apps after saving work and display real processing states. Allow at least the measured roughly 14.4 seconds of server work plus review/browser overhead for the demonstrated new workflow; do not turn one run into a universal wait estimate. A restart, ten-minute MFA idle exit, resource pressure or longer input can change results. If a strict ten-second complete workflow is required, further measured work on the remaining stages is necessary before claiming completion.

No application/model/configuration fix was made in this task. No regression suite was rerun because no application source changed; prior suite results remain dated historical evidence. The checks executed here were the real-model runs, job/audio/revision/outcome comparisons, protected-source hashes, read-only queue/health checks and OS-resource observations. Public hosting, wider accuracy validation and the other acceptance cases remain separate work.

Evidence is in ignored `runs/ram-retest-20261103/`: `measurements.json`, `initial-observer.json`, `identity-verification.json`, `fresh-workflow.json`, `before-cleanup-saved-assessment.json`, process snapshots and source-hash manifests. Raw recording bytes, passwords and login tokens were not written into these reports. Original audio remains in the existing private account store. Results were updated only by the user's normal website actions. This new report is uncommitted; no commit or push was made in this retest.
