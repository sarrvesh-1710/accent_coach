# Structured lesson plan

New learners first complete a three-sentence starting check, one per sound; see [the starting-check guide](STARTING_CHECK.md). Building a plan afterward orders the remaining nine sentences and keeps the three starting recordings in History. Skipping the check uses the full twelve-sentence catalog. Existing plans retain their sequence.

The full catalog contains three sound lessons with four sentences each. Sound
lesson order is chosen once when starting, using the user's current sound
recommendations and goals; a new learner can use the optional language starter.
The saved sequence stays fixed through the course. The user can still practice
any other sentence and use custom text/free speech.

## Sentence order inside each sound lesson

TH: I think so; I think we can; Please think again; We think it is fine.

IH: The ship is here; I see a ship; This ship is big; A ship is coming.

AE: That is a bad bed; It is a bad day; This is a bad plan; That was a bad idea.

The starting check displays a 0/3 counter. A personalized follow-up plan displays 0/9; a full course displays 0/12. Lesson and sentence counters reflect the saved sequence. The initial sound order can differ by language/goals/feedback.
The within-sound sequence above is preset for consistency; these sentences are
not a validated difficulty scale.

## Progress rules

- GET previews an unstarted course without saving it. Start is an authenticated,
  CSRF-protected POST and is idempotent for an existing active plan.
- Only newly recorded preset attempts after the start time can earn credit.
  Progress is published with Store.finish in the analysis transaction; the
  browser cannot mark a sentence complete itself.
- Completed analysis counts as practiced even if the sound comparison is
  inconclusive. Explicit model-stage unavailability, failed analysis, pending
  work and missing results do not earn credit. Practice credit is not a grade.
- Repeating a sentence does not inflate the count. Practicing ahead can earn credit
  for that sentence; Continue always chooses the first unpracticed available step.
- Deleting credited attempts removes their contribution; another retained
  credited recording for that sentence still counts. Other owners are excluded.
- Changing preferences does not reorder an active plan. Start a new plan applies
  the current goals and personal feedback with explicit confirmation. Old
  recordings remain in History and do not backfill the new plan. In-flight work
  created before a restart cannot fill the replacement course.
- After finishing the course, current practice/inconclusive sound results supply
  optional review links. No new sound mastery or whole-accent judgment is implied.

## Storage and catalog changes

The additive lesson_plans table stores the owner, plan ID, start time and sequence
snapshot; lesson_plan_steps stores credited attempt identities. They are in the
same private accounts.sqlite3 file as profiles and recordings, so server migration
uses the existing data-directory handoff. A regular app restart preserves credit.
Only starting a new plan resets it.

A renamed, removed or changed sentence in the catalog is shown unavailable for
that saved course. A new plan picks up the current catalog. Additional configured
sentences are included when rebuilding; default progress has twelve steps.

The UI uses content-versioned asset URLs to avoid stale scripts after deployment.
Course state refreshes on focus, at visible intervals, and after saved analysis.

## Verification

The full suite ran 196 tests: 195 passed and one existing Windows symlink check
was skipped. Ten lesson-plan tests cover order, idempotent start, account/CSRF
boundaries, recording-to-next-step HTTP/job publication, inconclusive versus failed
processing, duplicate/out-of-order practice, deleted recordings, persistence,
new-plan resets and end-of-course reviews. The HTTP speech test uses controlled
analysis output; it does not measure pronunciation accuracy. Browser checks showed
all twelve ordered sentences, saved course start after server restart, current
sentence selection, versioned scripts, and a 390px layout without horizontal
scrolling. Existing speech-model inference is unchanged.
