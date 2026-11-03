# Combined local demo

Branch: `parth/demo-ready`. This combines the integrated team practice site,
Parth's profile improvements, and the isolated private Kokoro adapter. Teammate
branches and `main` are unchanged. This is a local presentation build.

## Country and language starter demo: November 3, 2026

Launch the sample demo as below and sign in as `demo_starter` with password
`demo-practice-403!`. This fresh account has no invented sound results. It starts
with Japan selected as an illustrative preference, not a claim about the presenter.

1. Open My profile and use **Change starting lessons**.
2. Select Japan, leave language at **Use country starter suggestion**, and save.
   The Japanese-language starter offers AE / bad first.
3. Change country to Mexico and save. The Spanish-language starter offers IH / ship.
4. Set language to Japanese while keeping Mexico: the explicit language wins.
5. Turn off **Use background to suggest starting lessons** to return to a balanced
   starter. All 12 lessons remain available in every case.
6. Choose a sound goal to override the starter tie-break. Record and analyze a
   lesson to begin personal feedback. Once there is current sound feedback,
   background ordering is completely removed; personal results guide practice.
7. Reload to show saved preferences. Clear country/language to remove them.

New users can make the same optional choices during signup. Existing accounts get
blank preferences without changing names, passwords, recordings or analysis.
The legacy profile API remains compatible: updates without a background field
preserve existing background preferences. Country data stays local and is not sent
to the pronunciation or synthesis models. Local database backups were saved under
ignored `runs/` before the new preferences table was initialized.

The initial researched starter catalog is deliberately limited to Spanish,
Japanese and Mandarin backgrounds. Certain country selections tentatively suggest
one of these packs; country is not treated as proof of language. All other
countries, explicit English/another-language choices and opt-out use the balanced
TH/IH/AE check. No country-specific error rates or individual probabilities are
estimated. This release changes lesson ordering only, not scores or model evidence.

See [starter design and sources](BACKGROUND_STARTERS.md) for coverage and expansion.
Verification: all 180 tests ran, 179 passed, one existing Windows symlink skip;
six new background tests and the focused profile checks passed. Browser checks
verified country changes, opt-out, saving, and persistence after reload.

## Show the personalized profile immediately

```powershell
powershell -ExecutionPolicy Bypass -File .\start_demo.ps1 -Demo
```

Open http://127.0.0.1:7864/profile. Sign in as `demo_learner` with password
`demo-practice-403!`. The dashboard starts with five clearly labeled illustrative
sample attempts. Show sound-specific feedback, the practice recommendation, and
recent activity links. The normal microphone, analysis and Kokoro features remain
real; new completed analyses update the profile. Return to My profile or press
Refresh my feedback. The page also refreshes on focus and every 30 seconds.

Use `demo_new` with the same password to demonstrate an empty starting profile.
Demo data persists under ignored `runs/profile_demo`, separate from personal
`private_data`. Re-launching preserves changes rather than resetting your demo.
Sample results are not measurements and must not be presented as accuracy evidence.

The coaching engine reads only the signed-in account's latest 100 non-deleted
recordings. Each sound uses up to five current completed analyses, counted once
per recording; the newest observation guides the recommendation. Recent possible
substitutions come first, then inconclusive checks, then unassessed sounds, with
selected goals breaking ties. A later expected-sound observation replaces earlier
practice advice for that sound. Failed, deleted and superseded results never count
as sound judgments. This is explainable practice guidance, not a learned clinical
assessment or a validated improvement score.

## Launch on this laptop

Open the actual `accent_coach` repository in VS Code, open its terminal, and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
```

Open http://127.0.0.1:7861/. Sign in with your existing local account or create a
new one. Keep that terminal open; Ctrl+C stops the app. The launcher uses the main
`.venv` and the separate `voice_generation/.venv` for Kokoro. It does not install
packages, download models, reset accounts or modify recordings. If the port is
occupied, use the existing app or deliberately choose `-Port 7864`.

## Presentation walkthrough

1. Sign up/sign in. Open **My profile**, change your display name, select TH/IH/AE,
   show Save and Discard, and reload to show that saved preferences persist.
2. Open **Practice**. Show the 12 preset lessons, the written hints and the example
   audio. Record a short sentence such as **I think so**, then check and save it.
   Results include recognized words, experimental sound feedback, original audio,
   processing details and the analysis download.
3. Select **My own sentence** or **Free speech**, record/upload up to five seconds,
   and save it. Review the recognized words, edit if needed, then **Confirm
   transcript**. Confirmation is required before either operation below.
4. Press **Analyze confirmed words**. Wait for analysis to finish. TH, IH and AE
   are supported contrasts. An unsupported sentence or uncertain evidence can
   correctly produce no assessment; **Hi my name is** is a poor target demo.
5. Press **Hear a synthetic example**, wait, and play the generated audio. This
   operation is separate from analysis. It uses Kokoro's General American example
   voice, not a conversion of the speaker's voice. Generate again to demonstrate
   the faster warm request. Model loading makes the first request slower.
6. Open **My history**, reopen the recording and its saved results/playback. Delete
   only a disposable attempt. Sign out to demonstrate account boundaries.

Rehearse with an actual microphone before presenting. Allow the first real
analysis and first generation to finish before the live walkthrough. Do not use
synthetic fixture results as evidence of human pronunciation accuracy.

## Other laptops

Use Python 3.12 (the version used for this combined build), create root `.venv`,
and install the declared main requirements:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-accounts.txt -r requirements-scoring.txt
```

Follow `voice_generation/KOKORO_RUNBOOK.md` for its separate environment and pinned
weights. Follow the README's MFA and speech-model setup, including
`tools/setup_content_model.py`, and configure machine-specific paths in ignored
`phoneme_scoring/settings.local.json`. Models and environments are not in Git.
This laptop's local MFA runtime and phoneme cache still reference the older nested
checkout: keep it until those assets are migrated and the new paths verified.

Optional explicit fallback, if Kokoro cannot be installed on a demo machine:

```powershell
$env:ACCENT_COACH_GENERATION_BACKEND = 'windows'
powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
```

The fallback uses the Windows desktop voice, so announce which backend is shown.
There is no automatic silent fallback. Remove that environment variable or set it
to `kokoro` to restore Kokoro.

## Verification and evidence

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe tools/check_combined_demo.py
.\.venv\Scripts\python.exe tools/release_snapshot.py
```

The combined rehearsal uses temporary accounts/storage and the repository's
public synthetic `think.wav` example. It exercises real Whisper, MFA, phoneme
analysis and cold/warm Kokoro, plus profile persistence, lessons/examples, private
playback, history, account isolation, deletion and sign-in after restart. It never
uses your account or recordings. Results are saved locally under ignored
`runs/combined_demo_smoke.json`; the source/dependency snapshot is
`runs/demo_release.json`. The automated suite covers input limits, failures,
stale revisions and account protection. The browser microphone still needs a
human rehearsal.

## Verified November 1, 2026

- Combined automated suite: 167 tests ran, 166 passed, one existing Windows
  symlink skip. JavaScript syntax and both Python dependency checks passed.
- Real combined rehearsal: all 46 checks passed, including actual Whisper,
  MFA/phoneme analysis, cold/warm Kokoro, persistence and private playback.
- Observed processing: analysis 64.4 seconds, first Kokoro generation 46.5 seconds,
  warm generation 0.9 seconds. These are one local run, not latency promises.
- The launch script started the site successfully on port 7861; health and the
  browser sign-in page were verified. Live microphone testing remains a rehearsal
  step for the presenter.

## Profile verification: November 2, 2026

- Full suite: 174 tests ran, 173 passed, one existing Windows symlink skip.
- Seven focused coaching checks cover empty profiles/goals, prioritization and
  uncertainty, deleted/other-owner exclusion, stale revisions, later supported
  observations, multiple occurrences per attempt, and authenticated API behavior.
- Expanded real-engine rehearsal: all 50 checks passed. A real completed analysis
  updates the profile; deletion removes it; another account sees no activity.
- Browser checks verified the populated dashboard, lesson selection, history
  deep links and persistence after server restart. A 390px mobile viewport had
  no horizontal overflow. Normal and sample-workspace health endpoints passed.
- Observed processing in this run: analysis 87.4 seconds, first Kokoro generation
  45.3 seconds, warm generation 1.0 seconds. Allow time for cold loading and MFA.
  These synthetic smoke measurements are not human accuracy or latency guarantees.

## Scope

Recordings: at most five seconds and 10 MB. Confirmed text: at most 12 words and
200 characters. Experimental feedback covers the configured TH/IH/AE contrasts;
it is not a validated grade or an assessment of an entire accent. Voice-preserving
conversion, other target accents, and public deployment are not implemented.
All audio/account data stays in local private storage. Use this branch for team
review and demo integration; it is not automatically merged into `main`.
