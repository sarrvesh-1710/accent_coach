# Day 2 Phase 3: transcript preparation

Implemented October 13, 2026 on `feature/speed-free-speech`.

## Delivered

`transcript_input.prepare_transcript(text, settings)` is an independent preflight helper. Settings may be the existing settings dictionary or settings-file path (including existing local overrides). It requires no lesson ID, UI, authenticated session, learner audio, or persistent store. It does not confirm a transcript or start analysis.

Successful output contains `ok: true`, `original_text`, `normalized_text`, `normalization_version`, `transcript_sha256`, `character_count`, `word_count`, `tokens`, dictionary name/hash, an empty `missing_words` array, and null error. Each token includes its original spelling, normalized spelling, zero-based `word_index`, source offsets, occurrence ID, and dictionary pronunciation candidates. Candidates are not automatically selected or graded.

Failures use the approved `{ok: false, error: {code, user_message, retryable}}` structure with internal `reason_code` details:

- Invalid type, empty input, limits, unsupported characters, or dictionary-missing words: `UNSUPPORTED_TEXT`.
- Missing/unreadable dictionary, invalid configuration, empty dictionary, or malformed requested ARPA entry: `MODEL_UNAVAILABLE`.
- Each missing word retains its original spelling, normalized spelling, word index, offsets, and occurrence ID. Missing vocabulary is never a mispronunciation result.

## Supported input and deterministic counting

- Between 1 and 12 normalized English words; contractions count as one token, including multiple internal apostrophes.
- At most 200 Python Unicode code points in the **original** input, including whitespace and punctuation, before normalization.
- ASCII English letters; internal straight or right-curly apostrophes. Lowercase for lookup and convert right-curly apostrophes to straight ones. No spelling correction or expansion.
- Spaces, tabs, CR/LF and `. , ! ? ; :` plus double/curly-double quotes and parentheses separate words. Normalize the resulting word sequence to single spaces.
- Reject digits, emoji, markup, hyphens, standalone apostrophes, accented letters, other symbols and other whitespace explicitly. Preserve their source position in the error. The user must rewrite these inputs intentionally.
- Source offsets are half-open Unicode code-point indices into the exact original text, not UTF-8 byte or browser UTF-16 offsets.

These rules implement the design's 1–12 normalized-word policy. Existing preset `speech_content.words` remains unchanged. Storage and future custom-text comparison/alignment adapters must use this same versioned preparation rule rather than copying the older permissive regex.

## Occurrence identities

Word IDs combine the normalization version/original-text SHA-256 with the zero-based word index. Identical input is stable; even a case/punctuation edit changes the fingerprint so stale positional data cannot appear current. Repeated spellings receive distinct IDs.

`sound_occurrences(token, phones)` adds a pronunciation-sequence fingerprint and phone index. Repeated phones and different pronunciation candidates remain distinct. The helper takes a supplied ARPA sequence and strips stress only for the canonical `expected_phone`; original phones are retained. It does not select a dictionary variant, map MFA words, or decide sound support.

Callers must scope IDs by attempt/input revision and verify alignment word correspondence first. These hashes do not replace the approved ownership, revision, or active-job checks.

## Actual dictionary lookup

The current configuration selects `english_us_arpa`. Inspection of the installed MFA source confirmed the named dictionary location: `MFA_ROOT_DIR/pretrained_models/dictionary`, defaulting to `~/Documents/MFA/pretrained_models/dictionary`. The module follows that lookup without downloading or writing anything. Explicit existing file paths are accepted; relative file paths resolve against the process working directory, matching the current MFA invocation. Settings overrides use the existing loader.

The parser handles the installed tab/whitespace-delimited dictionary and optional numeric probability columns before ARPA phones. It preserves pronunciation variants, reads the dictionary fresh, and reports its content hash. No dictionary or pronunciation-model changes were made. Remote/custom MFA wrappers with a different environment/root require explicit resolver integration before use.

## Tests and evidence

- 12 focused tests passed, including valid/empty/invalid text, capitalization/punctuation, contractions, repeated words/phones, missing entries, 12/13 words, 200/201 characters, offsets, stable IDs, dictionary changes, and actionable failures.
- Full suite: 103 tests, 102 passed, one existing Windows symlink test skipped; no failures. After this run, an explicit empty-dictionary guard was added and all 12 focused tests passed again.
- Actual installed dictionary checks passed for the three preset sentences, a repeated-word sentence, and a curly-apostrophe contraction. A deliberately unknown word returned `UNSUPPORTED_TEXT` with its original token and position.
- Installed dictionary SHA-256: `e8c6c7b036ae2b7c78d2768b8dc6b1f9359175b842956d00b48c53c9c332e6b0`.
- Local evidence: `runs/day2-phase3-focused.log`, `runs/day2-phase3-regression.log`, `runs/day2-phase3-dictionary-check.json` (ignored by Git).

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_transcript_input.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
```

## Remaining integration and limitations

This phase adds only the module, focused tests, and this report. Existing Phase 2 edits remain in the working tree. Preset workflow, MFA execution, dictionaries, generated audio and UI are untouched.

Next: wire preparation into explicit transcript confirmation, verify MFA's ordered word correspondence (especially contractions), then plan aligned sound occurrences. Dictionary coverage does not establish model sound support or pronunciation correctness. Authentication, persistence, stale-job publication, and ASR-disagreement guards remain required integration work. No new real alignment or pronunciation-accuracy test was performed here.
