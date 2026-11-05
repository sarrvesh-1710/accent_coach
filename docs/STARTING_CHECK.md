# Three-sentence starting check

New learners begin with TH (I think so), IH (The ship is here), and AE (That is a bad bed). All three sounds are checked for every learner. Optional language background sets only the initial order, frozen when the check starts. Country is not collected.

The learner records, reviews, and confirms one sentence at a time. Results appear inline and show 0/3 through 3/3 starting sentences complete. Completed uncertain sound feedback counts as practice and remains inconclusive in the profile. Failed or unavailable processing does not advance progress. Skipping is available under plan options; no audio is required to skip.

At 3/3, Build my lesson plan uses the learner’s current personal sound feedback and goals to order the remaining nine sentences. The three starting prompts are omitted, so completing the starting check does not immediately require repeating them. The nine-sentence plan begins at 0/9; the starting recordings remain in History and inform the profile. Plan completion is practice progress, not mastery. The learner can voluntarily revisit a starting sentence.

The current coaching priorities place possible substitutions first, followed by inconclusive, untested, then supported sounds. This is an initial model-informed snapshot, not a validated pronunciation diagnosis. Subsequent practice updates the profile. A saved course remains stable until the learner explicitly starts a new plan.

Existing saved courses retain their sequence and progress. No migration resets a learner’s history. New accounts receive this starting flow. The sample demo account demo_assessment, with the usual sample password, is available to inspect it without resetting existing demo users.

Implementation reuses owner-scoped lesson_plans with kind=assessment or practice. Earlier snapshots without kind remain practice. Server-side completion derives only from valid completed post-start preset attempts with matching sentence and prompt. Start/build/skip require login and CSRF. Build refuses incomplete checks and is idempotent after success. No browser request can directly mark a sentence complete.
