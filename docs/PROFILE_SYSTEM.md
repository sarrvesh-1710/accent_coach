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

Recording previews stay in the browser until explicitly confirmed. Confirmed recordings belong to the signed-in account. Discarded previews never contribute to the profile or lesson progress. Preset lessons use their selected
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

## Structured sentence plan

My profile and Practice also offer a three-lesson, twelve-sentence course.
Before starting, its order previews the current recommendations. Starting saves a
snapshot of that order. Personal feedback and selected goals determine the sound
order when available; otherwise the optional language starter supplies the order.
Each sound has four preset sentence variations. The sequence stays fixed while
practicing, so it does not jump around after each new result. Optional review
recommendations continue adapting separately. All sentences remain freely usable.

Plan progress is recorded in the same transaction as a completed preset analysis.
Inconclusive but completed sound analysis counts as practice, not mastery. Failed
or unavailable processing does not advance. Only new recordings made after plan
start count. Free-speech/custom-text jobs, generated examples, old attempts and
other users do not fill the preset course. Removing all credited recordings for a
sentence removes its credit. Starting a new plan explicitly resets its progress,
applies current preferences/feedback, and retains recording History.

The additional lesson_plans and lesson_plan_steps tables live in the same private
SQLite database and move with the account data. No browser-local progress or
server-specific path is used. See LESSON_PLAN.md for the demonstration.
