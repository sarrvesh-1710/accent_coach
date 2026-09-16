# accent_coach
TAMU Capstone 403

## Sarrvesh: CPU audio analysis

Use Python 3.11–3.13. From this repository in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe compare_audio.py data/learner.wav data/reference.wav --output runs/comparison.json
```

Use two WAV recordings of **the same text**, each no longer than five seconds.
The loader converts recordings to 16 kHz mono without trimming timestamps.
Silence, invalid files and overlong clips return an explicit unavailable status.
The JSON contains pitch, exploratory F1/F2/F3 formants, duration ratio and
MFCC dynamic time warping (DTW) distance. Missing features are `null`.
Pitch contours are measured in semitones relative to each recording's median.
These measurements are not calibrated pronunciation scores; formants are not
normalized across speakers. Real speech validation and team integration remain.

### Integration contracts

- `audio_io.prepare_audio(path, settings=None)` returns audio metadata and a
  NumPy `samples` array. Exclude `samples` when serializing to JSON.
- `dsp_features.extract_features(audio, settings=None)` returns JSON-ready features.
- `compare_audio.compare_audio(learner_audio, reference_audio, learner_dsp,
  reference_dsp, settings=None)` returns JSON-ready comparisons.
- Every result has `status` (`ok`, `warning`, or `unavailable`), `reason`, and
  `warnings`. Check status before consuming features. Invalid settings raise
  `ValueError`. Settings are optional flat dictionaries; defaults are documented
  in each module. Optional `prompt_id` values in both audio dictionaries must match.

Lucas owns alignment/scoring; Parthiban owns the pipeline, feedback and UI.
The requirements currently cover only this DSP component. Add their tested
dependencies during integration. L2-ARCTIC evaluation and Rachel's English
resource links will be integrated by those components.

Keep recordings in `data/`, generated results in `runs/`, and downloaded models
in `models/`. These local folders are excluded from Git.
