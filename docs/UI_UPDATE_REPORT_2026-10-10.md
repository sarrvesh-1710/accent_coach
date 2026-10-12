# Accent Coach: interface update report

## What the app does now

The learner chooses a sentence, records or uploads up to five seconds of audio, and selects **Check my recording**. The app independently checks the words with Whisper, locates sounds with MFA, and compares the lesson's target sound using the phoneme model. **No reference recording is used by app_2.**

The supported target checks remain TH in **think**, IH in **ship**, and AE in **bad**. This update improves how results are communicated; it does not change model weights, scoring thresholds, or assessment accuracy.

## Changes delivered

1. **Simpler results.** A supported TH result now says “Your ‘th’ in ‘think’ sounded closer to the expected sound.” Uncertain results say “We're not sure about the sound in ‘think’ yet.” Alternative-sound results suggest practice and explain that the app may be mistaken. All retain the experimental-result limitation.
2. **Recognized words.** The result includes **We heard:** followed by the transcript whenever the content check returned one. It explicitly warns that recognition can be wrong. Technical failures or rejected audio may have no transcript.
3. **Clearer hints.** Sound controls say **Practice** and use plus/minus indicators to open and close written hints. They no longer resemble audio playback controls. Teal identifies the lesson focus, not a passing result.
4. **Playback at the result.** A **Listen to my recording** player appears with the result when a saved learner recording is available. **Record again** clears that recording and the old result so the learner can make another attempt using the input above. It does not automatically turn on the microphone.
5. **Actual processing stages.** The progress display receives notifications directly from the pipeline: checking recording, checking words, locating sounds, comparing the practice sound, and preparing feedback. There are no invented completion percentages. A sentence mismatch does not announce sound stages that were skipped.
6. **Stale-result protection.** Recording changes, sentence changes, and retry actions clear previous results and result playback. Controls are disabled during analysis. A failed display notification cannot break the underlying analysis.

## Verification

- **60 repository tests passed** in this update. Added checks cover stage ordering, skipped stages, display failures, result playback, and clearing old state.
- Opened the restarted app at `http://127.0.0.1:7861/` and verified that the new **Practice** control opens its written hint.
- The real-recording callback check is saved in `runs/ui_polish_check.json`; it records stage notifications, the result text, the saved recording path, and checks that result playback and the retry control are available.
- Browser microphone detection was visible, but a live microphone recording and a user's playback listening check were not performed during this update. No claim of new pronunciation accuracy is made.

## How to check the update

1. Refresh `http://127.0.0.1:7861/` to load the new screen.
2. Open **Practice th**. It should reveal a written hint, not play audio.
3. Upload or record “I think so” and select **Check my recording**. Watch the stage message while processing.
4. Check the **We heard** line and the result card. The wording should acknowledge uncertainty or model limitations.
5. Use **Listen to my recording** below the result, then **Record again**. Old playback and results should disappear.
6. Change the selected sentence. The practice hints should update and old results should stay cleared.

## Required team validation before grades

The human-validation recommendation remains outstanding: it requires real recordings and human listening judgments. Have several speakers record “I think so,” deliberate “sink”/“fink” variants, a different sentence, and noisy or unclear speech. Have reviewers label what was actually said, then compare those labels with model responses. Count incorrect judgments and uncertain outcomes separately. Use the existing evaluation manifest and tooling described in the implementation report.

Do not treat deliberate substitutions as guaranteed ground truth merely because the speaker intended them. Do not lower thresholds just to obtain more positive messages. Until this evaluation supports a grading rule, keep numerical grades and pronunciation pass/fail unavailable.

## Delivery status

Updated files: `app_2.py`, `pipeline.py`, associated tests, README, and this report. The app was restarted locally. Changes have not been committed or pushed to GitHub in this update. The interface remains English; translated instructions or spoken guidance would be a separate accessibility enhancement.
