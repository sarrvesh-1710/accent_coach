# Microphone level and recording confirmation

The browser shows live input level while microphone recording is active. It can
report incoming sound, very quiet input, and very loud input. This measures sound
level, not speech recognition, pronunciation correctness or calibrated loudness.
The meter runs locally and is never connected to speaker output. Live transcripts
are not implemented in this phase; existing transcription happens after the user
confirms a recording.

## User flow

1. Press Record my voice (or Record again from review) and grant microphone access.
   The level meter and elapsed time appear during capture. Recording stops after
   about five seconds; the encoded WAV is capped at five seconds.
2. Stop recording or let it finish. Listen using the Review your recording player.
   Nothing has been uploaded or saved to History yet. Uploaded WAV files use the
   same local review step.
3. Record again replaces the draft only after a new recording succeeds. If access
   is denied, the previous draft remains available. Discard removes the preview
   and releases its object URL without making an API request.
4. For preset lessons, Confirm and analyze saves the recording and queues its
   existing analysis. Lesson credit still requires the existing completed-analysis
   rules. For custom text/free speech, Confirm recording and transcribe saves the
   recording and starts transcription; the words must still be explicitly
   confirmed before sound analysis or synthetic generation.
5. Saving freezes input controls and prevents duplicate confirmations. A failed
   upload preserves the local draft for retry. A successful save clears the draft.
   Selecting another lesson or mode discards the old local draft to prevent
   attaching it to an unrelated exercise.

Browser microphone access requires permission and HTTPS or localhost. Unsupported
or unavailable microphones give recovery instructions and retain WAV upload as an
option. Capture stops when the page is hidden. Leaving the page disposes its
microphone, animation loop and audio context. Canceling a pending access request
invalidates it; if a stream is granted later, its tracks are stopped. No discarded
or unconfirmed recording counts toward account activity or course progress.

Unconfirmed drafts are in memory only and are lost on a full page reload or exit.
They are not persisted in browser storage. No new server service, streaming API,
external transcription provider, or Node runtime dependency is required.

## Verification

```powershell
node --test tests/test_microphone.cjs tests/test_recording_review.cjs
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Sixteen client tests passed using simulated audio and a minimal browser fixture.
They exercise level classification, automatic stopping, WAV format/duration,
permission denial/cancellation, late-stream and cleanup races, page exit, draft
review/discard, duplicate submission prevention, failed-upload retry and the
separate custom-text transcript confirmation. The full Python suite ran 196 tests:
195 passed with one existing Windows symlink skip.

The browser check used the repository's public synthetic ship.wav example to
verify playback review, Confirm/Record again/Discard controls, a local blob URL,
and a 390px layout without horizontal overflow. The sample account remained at
zero saved attempts before, during and after review/discard. The test draft was
removed. Physical microphone capture was not opened by the agent; the presenter
should grant permission and try speaking on the actual device before a demo.
Node is required only for the client tests, not for the deployed Python app.

## Practice page guidance

The page uses a compact lesson plan above one shared workspace. The selected sentence is displayed prominently during recording. Sentence and mode selection, WAV upload, and full plan options are expandable so the main path stays clear. Stop appears only during capture or a microphone request; a local draft replaces the initial Record action with review actions. Analysis then replaces capture controls within the same workspace. Incoming recordings scroll to the review area and focus confirmation, without submitting it.

## Inline analysis results

Confirming a preset recording immediately opens its processing panel. It refreshes automatically and brings completed feedback into view, including recording quality, understood words, target-sound evidence, and Retry/Next actions beneath the analysis with the completed/total sentence count. Completed uncertain sound feedback counts as practice, not mastery. Failed processing does not advance the plan. Existing in-plan uncertain analyses omitted by older progress rules are counted on the next plan read; pre-plan history remains excluded. Saved attempts can also be opened at `/practice?attempt=ATTEMPT_ID`.

## Unified practice workspace

Practice has two main areas: a compact lesson plan at the top, followed by one shared workspace for speaking, local review, processing, and feedback. During result review the capture controls are hidden. Sentence/mode selection, listening examples, uploads, technical details, deletion, and optional sound reviews are expandable rather than competing with the main action.

Before upload, the microphone meter can report detected sound or loud peaks; it cannot establish that speech was understood. The local review says what was detected and asks the learner to listen before confirmation. Uploaded files are labeled selected, with quality checks still pending.

After analysis, the feedback separates recording quality, recognized words (including expected versus recognized differences), and target-sound evidence. Silence, saturation warnings, unavailable quality checks, unconfirmed content, and inconclusive model evidence never become confirmed pronunciation errors. A possible sound substitution is shown only when usable recording quality, confirmed content, and a separate alternative-favored target assessment are all present. Supported evidence concerns the target sound, not the entire word or sentence.

Retry and Next appear below the analysis. A learner may skip forward after an unclear result; the button explicitly says skip for now and the sentence remains incomplete. The learner is returned to unfinished sentences later. Starting-check completion still requires three analyzed starting sentences; skipping the entire starting check remains available in plan options. Custom/free-speech feedback uses the same recording and word checks but does not award preset lesson progress.

Confirmed analysis publishes only status, reason, and warning codes for recording quality, plus a content-verification status. These metadata are cleared whenever the recording/transcript revision changes or analysis restarts. Original audio, model scoring, and Sarvesh’s alignment optimizations are unchanged.
