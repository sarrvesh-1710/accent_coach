# Day 1: synthetic listening examples

This isolated starter proves text -> labeled playable WAV on Windows, using the
installed American English desktop voice (Microsoft Zira on this laptop).
It is not voice-preserving conversion or a validated General American reference.
No learner recording is read, uploaded, assessed, or replaced.
The bundled PowerShell script runs with a process-only execution-policy bypass;
no system or user execution-policy setting is changed.

From the feature checkout in PowerShell:

```powershell
# Environment already created here. To recreate it without package installation:
python -m venv --without-pip voice_generation/.venv
.\voice_generation\.venv\Scripts\python.exe -m voice_generation.benchmark
.\voice_generation\.venv\Scripts\python.exe -m voice_generation "I think so."
.\voice_generation\.venv\Scripts\python.exe -m unittest discover -s tests -p test_voice_generation.py -v
```

Open `runs/synthetic_examples/listen.html` to play all three examples.
WAVs and JSON sidecars are under ignored `runs/synthetic_examples/`, separate
from original recordings. Each sidecar includes supplied text, voice, asset
type, measured total/synthesis latency, and pending listening-review fields.
Listen to each clip and fill `review.words_match` and `review.pronunciation_notes`.
Generation success and a readable WAV do not prove correct spoken words.

Internal callable function:

```python
from voice_generation import generate_audio
result = generate_audio("I think so.", "en-US-general-american")
```

Success returns `generated_audio_id`, `type: synthetic_example`, completed status
and `timings_ms`. Failures return safe `error.code`, `user_message`, and
`retryable`. The function is synchronous, local, and not the team's queued job API.
Only the initial accent ID is accepted, with an explicit suitability limitation.

Before website integration, add `generate_example(auth_context, attempt_id,
input_revision)` through Lucas's storage layer: load authorized confirmed text,
check confirmation, store assets, and reject stale/deleted job results atomically.
The eventual UI must say **Synthetic example**, and generation failure must leave
completed assessment visible. Do not pass generated files into the learner pipeline.

See `FEASIBILITY.md` for the conversion investigation and next model experiment.

## Kokoro comparison

See [the Kokoro timing and listening runbook](KOKORO_RUNBOOK.md) for the neural backend, cold/warm measurements and review form.

## Day 2 playback component

Run the isolated Hear an example demo on localhost:8762. See [Day 2 launch and integration instructions](DAY2_RUNBOOK.md).
