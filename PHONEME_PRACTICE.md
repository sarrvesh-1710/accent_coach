# American phoneme practice

Start the separate app from the repository folder, in the same Python environment
used for the original app:

```powershell
python phoneme_practice.py
```

The existing `app.py`, `pipeline.py`, and `prompts.json` still behave as before.
This app uses `practice_targets.json` and needs **no reference WAVs or KNN-VC**.
It reuses the existing MFA and Wav2Vec2 setup, including
`phoneme_scoring/settings.local.json`. For a fresh environment, follow the full
local alignment/scoring setup in README.md. No new dependencies were added.

## Use it

1. Choose **American English** and a sentence. Read the draft phoneme target
   displayed under the selectors.
2. Record with the microphone or upload audio. Say the selected sentence once,
   without an introduction. Keep the whole recording under 15 seconds.
3. Click **Analyze phonemes**. The first model load may download the existing
   Wav2Vec2 checkpoint; subsequent attempts reuse it in the running process.
4. Open **Detected phonemes**. Green means experimental **Correct**, red means
   experimental **Incorrect**, and gray means **Uncertain**.
5. Play the sentence, then click any evidence-table row to hear that sound with
   40 ms of context on either side. The table includes its word, accepted target
   IPA, model's preferred sound, judgment, timing, evidence count, and reason.
6. Download `results.json` to inspect or share a test result. Recordings, clips,
   alignment logs, and results stay under `runs/phoneme_practice/` (Git-ignored).

## Draft targets

| Sentence | Broad General American target | Main contrast |
|---|---|---|
| I think so. | /aɪ θɪŋk soʊ/ | /θ/ and /ɪ/ |
| The bed is bad. | /ðə bɛd ɪz bæd/ | /ɛ/ versus /æ/ |
| The ship is here. | /ðə ʃɪp ɪz hɪɹ/ | /ʃ/, /ɪ/ versus /i/, and /ɹ/ |

Draft variants accept emphasized /ði/ for *the*, reduced /əz/ for *is*, and
an /i/ vowel before /ɹ/ in *here*. The eSpeak model writes /i/ as `iː`.
These alternatives are compared as an accepted set, so one accepted vowel
does not become an incorrect competitor to another. They are not an exhaustive
account of American allophones, regional accents, or connected speech.

## Timing

MFA aligns the **whole original recording** with the selected sentence, producing
word and phone intervals. The start of its first word interval is sentence time
zero. Each phone retains its original-file start/end and also receives
`sentence_start_sec = start_sec - sentence_onset_sec` (likewise for the end).
The first-word start is an alignment estimate, not an independently recognized
keyword. The app does not establish word identity from free-form speech.

The audio used for alignment and scoring is identical, with the existing hash
check. No time stretching or fixed time slots are used. Leading/trailing silence
is excluded only from **sentence playback**, after scoring. All internal pauses
remain. The original playback retains the original recording and timestamps.
Missing word tiers, unexpected word labels, crossing phone boundaries, or
invalid timing stop the attempt rather than inventing an onset. Unsupported
dictionary pronunciation variants produce uncertain phone judgments.

## What the labels mean

These are **uncalibrated model judgments for user testing**, not measured
pronunciation accuracy. The existing CTC acoustic scorer pools evidence inside
each aligned phone interval. A manual expected-phone list cannot itself determine
what the speaker produced, and forced alignment does not verify spoken text.

- **Correct:** at least two qualified evidence frames, the scorer's quality
  checks pass, the winner is accepted, and its signed margin over the strongest
  nonaccepted alternative is at least **1.0 natural-log unit**.
- **Incorrect:** the same evidence checks pass and a nonaccepted sound wins by
  at least **1.0 natural-log unit** over the strongest accepted target.
- **Uncertain:** weak, sparse, ambiguous, missing, unsupported, or intermediate
  evidence. Model/load/alignment failures never become red pronunciation errors.

The 1.0 margin is an explicit **starting heuristic**, not a calibrated threshold
or a percentage. CTC evidence frames are not independent votes. MFA can force the
wrong sentence onto audio, and short sounds, unreleased stops, rhotics, or model
tokenization can cause misleading or uncertain judgments. Do not use this mode
for extra words, omitted words, or free speech. It is an offline analysis after
recording, not live streaming phoneme recognition.

For controlled experiments, the practice margin can be changed locally without
changing the original app's evidence display:

```json
{
  "practice": {"decision_margin_nats": 1.0}
}
```

Merge that section into `phoneme_scoring/settings.local.json`; preserve existing
MFA/model configuration. Restart the app after changing settings or code.

## Verification

```powershell
python -m unittest discover -s tests -p "test_phoneme_practice.py" -v
python phoneme_scoring/gop_score.py --self-test
```

Tests use synthetic audio/evidence and mocked MFA/model calls. They check silence
offsets, natural pauses, word/phone association, accepted variants, sparse/ambiguous
evidence, failed attempts, saved playback, and UI callbacks. They do **not** measure
accuracy on real speakers. To evaluate that, record these sentences naturally and
with deliberate sound substitutions, retain human labels, and check the saved
phone intervals before adjusting any decision threshold.
