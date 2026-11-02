# Day 5, Phase 3: Fresh human-recording tests

October 21, 2026. **Partial report: one case collected; five awaiting recordings.**

## Scope and prerequisites

- Phase 1 established the existing implementation and model assets. Phase 2 remains partially verified; no complete browser acceptance sign-off is implied here.
- The user chose to record manually through the normal learner workflow. The assistant has not activated the microphone or substituted synthetic recordings for human cases.
- Case 1 is the newest attempt the user identified after replying "case 1 saved". It was already confirmed and analyzed when inspected. Recognition, confirmation, and analysis submission were not observed live by the assistant, and no duplicate job was submitted.
- Evidence: actual signed-in browser History/result panel, DOM-backed original-audio source/duration, and an exact-attempt read-only SQLite query for existing job IDs, timings, and asset role/size. No unrelated account records, credentials, raw audio, or personal profile fields were extracted.
- Only this evidence report is being added. Application code, models, dictionary, settings, alignment logic and thresholds are unchanged. No staging, committing or pushing.

## Six-case status

| Case | Required fresh utterance / target | Recognized text | Confirmed text | Outcome |
| --- | --- | --- | --- | --- |
| 1. Intended correct supported sound | Say "I think so" naturally; TH in think | I think so. | I think so. | Processing completed; TH inconclusive, IH supported experimentally. No independent human correctness label established. |
| 2. Deliberate substitution | Say "I sink so"; intended assessment text "I think so" | Not collected | Not collected | BLOCKED awaiting fresh recording. ASR disagreement may legitimately withhold sound judgments. |
| 3. Repeated words | Say "I think, I think so" | Not collected | Not collected | BLOCKED awaiting fresh recording. Separate repeated-word/sound occurrence identities remain unverified on human speech. |
| 4. Contraction | Say "I don't think so" | Not collected | Not collected | BLOCKED awaiting fresh recording. |
| 5. Dictionary-missing word | Say "I keep doomscrolling"; missing token doomscrolling | Not collected | Not collected | Dictionary absence verified; spoken workflow BLOCKED awaiting recording. |
| 6. Silence / unusable input | Record up to five seconds without speech | Not collected | Not applicable until observed | BLOCKED awaiting recording. Do not supply invented text to force analysis. |

## Case 1: detailed evidence

**Source:** fresh manually recorded human audio as supplied by the user for Case 1. Intended correct production is the test condition, not an independently verified phonetic label.

- Attempt: `1411ea4ea5ab4191a8dd2bc052121c1f`.
- Created: October 21, 2026, 15:04:59 America/Chicago.
- Input mode: `free_speech`.
- Original learner asset: `0e98c3c86435494ab42f7bf41a46fe8c`, role `learner`, attached at revision 2.
- Browser audio duration: **1.920 seconds**; stored asset size **184,364 bytes**. Within the five-second/10 MiB limits.
- Recognized text retained separately: `I think so.`
- Confirmed text: `I think so.` (three words, within text limits).
- Current input revision: **3**.
- Transcription job: `ba96b0d81fb348c78e70dff9ced27ad1`, revision 2, completed.
- Analysis job: `d8362af5ff8f476aa9f890cc7ab72a44`, revision 3, completed.
- Generation: not started. The displayed player points to this attempt's learner asset, not a generated example.
- Errors: none stored.

### Sound findings

| Word occurrence | Phone occurrence | Expected sound | Outcome | Reason |
| --- | --- | --- | --- | --- |
| think, word_index 1 | phone_index 0 | TH | inconclusive | INSUFFICIENT_EVIDENCE: sequence comparison too close under the experimental rule |
| think, word_index 1 | phone_index 1 | IH | supported | Experimental model evidence; not a confirmed pronunciation judgment |

Both results retain distinct occurrence IDs with the same word index and different phone indices. This verifies separation of these two sounds in one word, **not** repeated-word handling, which requires Case 3. TH's diagnostic alternative is T; its inconclusive outcome does not establish a T substitution.

**Interpretation:** successful processing with inconclusive evidence on the target TH and an interpretable experimental finding for IH. No pipeline failure is recorded. This is neither a pronunciation pass nor a pronunciation failure.

### Existing instrumentation

| Measurement | Observed seconds |
| --- | ---: |
| Transcription queue | 0.0199 |
| Transcription processing | 2.3156 |
| Analysis queue | 0.0253 |
| Analysis processing | 39.0535 |
| Analysis audio stage | 6.4871 |
| Analysis alignment stage | 27.0194 |
| Analysis phoneme stage | 5.0010 |

Stage durations are nested inside analysis, not additional durations to add to it. Transcription plus analysis processing sums to **41.3691 seconds**, excluding upload, human review/confirmation, browser polling and queues. This is not a newly timed end-to-end browser measurement. Worker/model first-use state and dictionary cache hit status were not captured for this attempt; do not label it cold or warm. No precise MFA lock/subprocess split is persisted in this session snapshot.

Alignment's standalone status and TextGrid are not exposed in the saved session metadata inspected here. The alignment stage has a recorded duration and the job completed with a supported IH finding; direct alignment artifacts/boundaries were not independently audited for this case.

### UI observation

On initial inspection the History card still read "processing" while the opened session panel read analysis "completed". This is an observed status discrepancy, potentially a stale list snapshot. It is not evidence that the job failed. Refresh/reproduction of the list-update behavior has not been performed as part of this case, and no fix was attempted.

## Case 5: dictionary preflight evidence

The currently configured dictionary is `english_us_arpa`, resolved to the installed MFA `pretrained_models/dictionary/english_us_arpa.dict` under the user's MFA directory. Dictionary SHA-256:

`e8c6c7b036ae2b7c78d2768b8dc6b1f9359175b842956d00b48c53c9c332e6b0`

A read-only, case-folded first-token lookup found **doomscrolling absent** and **i/keep present**. No pronunciation was added. A future preflight rejection must be reported as missing dictionary coverage, not incorrect pronunciation. No fresh recording or actual rejection has yet been observed for this case.

## Remaining collection and limitations

Record each remaining case manually within five seconds, save/transcribe it, and preserve the recognized words before correction. For Case 2 deliberately speak sink while retaining think as the intended assessment target. Do not call an inconclusive result a missed/confirmed error without checking the content safeguard and acoustic evidence.

For Case 6 retain the actual rejection or recognition failure; do not invent confirmed words for silence. Record any missing attempt/job identity explicitly if rejection occurs before saving.

Until the remaining recordings are provided, no substitution sensitivity, repeated-word reliability, contraction behavior, spoken dictionary-gap handling, or silence safety result is established by this Phase 3 report. No human accuracy percentage or overall acceptance sign-off is supported by one recording.
