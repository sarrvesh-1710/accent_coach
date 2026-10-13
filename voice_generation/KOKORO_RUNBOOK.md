# Kokoro comparison and the data to record

Run from the `accent_coach` repository root in PowerShell. Use the generation
environment, separate from the shared application's environment.

```powershell
# One-time installation/download; these times are excluded from synthesis:
.\voice_generation\.venv\Scripts\python.exe -m pip install -r voice_generation/requirements-kokoro.txt
.\voice_generation\.venv\Scripts\python.exe -m spacy download en_core_web_sm
.\voice_generation\.venv\Scripts\python.exe -m voice_generation.setup_kokoro

# Repeatable comparison: 3 sentences, 1 cold + 3 warm runs each:
.\voice_generation\.venv\Scripts\python.exe -m voice_generation.compare_voices --repeats 3

# After an interruption, retain completed sentences and finish missing trials:
.\voice_generation\.venv\Scripts\python.exe -m voice_generation.compare_voices --repeats 3 --resume

# Generate one new sentence:
.\voice_generation\.venv\Scripts\python.exe -m voice_generation "I think so." --backend kokoro
```

The initial experiment is CPU-only, with four PyTorch threads, American English
(`lang_code='a'`), voice `af_heart`, normal speed, 24 kHz mono PCM WAV.
The model revision and hashes are saved under ignored `models/kokoro/manifest.json`.
Runtime uses those local model and voice files; benchmark workers disable HF downloads.

## Automatic measurements

Open `runs/kokoro_examples/listen.html` to compare Kokoro with the saved Zira clips.
`comparison_results.json` preserves all twelve individual trials with:

- UTC run date, source commit, package versions, Python, operating system and CPU details.
- Sentence/category, exact supplied text, backend, voice, model revision and device.
- Cold/warm condition and repetition number.
- Model loading time, synthesis time, request time, and cold total time in milliseconds.
- Output duration in seconds, sample rate, generated asset ID, status and errors.
- Real-time factor: request seconds / audio duration seconds. Below 1 means generation
  is faster than the resulting clip plays; it is not a quality score.

The timer uses `time.perf_counter()`, so no stopwatch is needed. A fresh subprocess
loads the model for each sentence, then generates that sentence once cold and three
times warm. Cold total includes imports, model/voice loading, phonemization, synthesis,
WAV saving and WAV metadata verification. Interpreter launch and JSON sidecar writing
are outside the timing boundary. Warm request excludes the already completed model
load. Downloads/installations are setup work and excluded from both conditions.

Use the median of the three warm request times to summarize typical latency; keep
individual trials so variation stays visible. One cold trial per sentence is an
initial observation, not a stable cold-latency estimate. The original Zira timings
include a new speech process per call and have a different timing boundary, so compare
audio quality directly and describe timing conditions when reporting performance.

## What you record by listening

For each of the three Kokoro examples, enter your name and:

1. **Words match:** yes / no / unsure. Write the exact missing or changed words.
2. **Naturalness:** 1 very robotic, 2 mostly robotic, 3 mixed, 4 mostly natural,
   5 very natural. This is your subjective rating, not a validated model score.
3. **Accent suitability:** sounds suitable / unsure / needs improvement.
4. **Pronunciation notes:** TH in *think*, IH in *ship*, AE in *bad*; note any
   odd stress, pauses, clipped endings, noise or glitches. Mark sounds absent
   from a sentence as not applicable; uncertainty is not an error.

Click **Download my review** and retain `kokoro-listening-review.json` beside
`comparison_results.json`. Review fields are not automatically saved by the page.
The existing Zira feedback is recorded only as: words sounded correct, robotic;
no numerical naturalness or accent score was inferred.

## Scope

This backend is a reusable local Python object:

```python
from voice_generation.kokoro_backend import KokoroGenerator
generator = KokoroGenerator()  # Load once, then reuse.
result = generator.generate_audio("I think so.", "en-US-general-american")
```

It does not clone the learner's voice or connect to assessment/session storage.
Keep output labeled **Synthetic example**. Website wiring still needs the authorized
attempt snapshot and revision checks described in TEAM_INTERFACE.md.
Generation success does not establish correct words or suitable pronunciation.

Source usage and model licensing: https://huggingface.co/hexgrad/Kokoro-82M
