# How the user's profile develops

The profile is an explainable practice plan calculated from saved account data.
It does not train a separate speech model or assign a permanent ability level.

## 1. Start with user choices

Signup saves a display name and optional language background. Arabic, Hindi,
Japanese, Mandarin Chinese and Spanish have introductory lesson orders. Skipping,
multilingual and opting out use a balanced TH/IH/AE check. Users can choose their
own sound goals and change any preference later. Country is not collected or used.
Language only orders first exercises; it is never supplied as a scoring input.

## 2. Save what actually happened

Each recording belongs to its signed-in account. Preset lessons use their selected
sentence; custom/free speech requires the learner to review and confirm the words.
The existing speech pipeline records experimental TH/IH/AE observations as
practice suggested, expected sound favored, or inconclusive. Original audio,
results, status and timestamps persist in the account database. Kokoro playback is
a separate listening example and never counts as learner evidence.

## 3. Build a current coaching summary

`accounts/coaching.py` reads the latest 100 non-deleted recordings for that owner.
Empty drafts are excluded. Only current, completed analyses supply sound evidence.
Edited transcripts/recordings invalidate superseded results; deleted attempts and
another person's data never contribute. A failed analysis is not an incorrect
pronunciation. Each sound counts once per recording, even if repeated. Within one
recording, a possible substitution takes precedence over an uncertain or
expected-supported occurrence. Up to five recent observations are shown per sound.

## 4. Choose the next exercise

The latest observation guides each sound's current status. Recommendation priority
is practice suggested, inconclusive/recheck, untested, then expected sound favored.
Within those groups, selected goals come first. Language ordering only breaks ties
before any current personal sound feedback exists. Once personal evidence exists,
all language tie-breaks stop. A later expected-supported check changes the current
advice; it does not establish mastery. All lessons remain available in every case.

The page refreshes on opening, after saving preferences, on window focus, every
30 seconds while visible, or via Refresh my feedback. Practice also offers the same
recommended lesson links. Activity links reopen saved recordings/results.

## Persistence and moving servers

Users, Argon2 password hashes, login sessions, preferences, attempts, results and
private audio blobs live in `accounts.sqlite3` under `ACCENT_COACH_DATA_DIR`.
Moving the complete stopped application's data directory to persistent storage
preserves profiles and history. Users normally sign in again on the new domain.
Opening a new empty data directory creates an empty installation; it does not
transfer the old accounts automatically. See SERVER_DEPLOYMENT.md.

Observations and counts are experimental model evidence, not validated grades,
clinical assessments or proof of improvement. The starter research and its limits
are documented in BACKGROUND_STARTERS.md.
