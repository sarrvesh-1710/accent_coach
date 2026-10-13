"""Conservative English transcript preflight; no alignment or pronunciation grading."""
import hashlib
import os
from pathlib import Path
import re

from phoneme_scoring.align_audio import load_settings

NORMALIZATION_VERSION = "english-v1"
MAX_WORDS = 12
MAX_CHARACTERS = 200
WORD = re.compile(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)*")
SEPARATORS = set(".,!?;:\"()\u201c\u201d")


def _dictionary_path(settings):
    """Mirror local MFA named-model lookup; relative explicit paths use MFA's cwd."""
    value = settings["mfa"]["dictionary"]
    if not isinstance(value, str) or not value:
        raise ValueError("Missing dictionary configuration")
    path = Path(value).expanduser()
    if path.is_file():
        return path.resolve()
    if path.suffix or path.is_absolute() or "/" in value or "\\" in value:
        raise FileNotFoundError("Configured dictionary file is unavailable")
    root = Path(os.environ.get("MFA_ROOT_DIR", "~/Documents/MFA")).expanduser()
    return (root / "pretrained_models" / "dictionary" / (value + ".dict")).resolve()


def _dictionary_entries(path, requested):
    raw = path.read_bytes()
    if not raw.strip():
        raise ValueError("Configured dictionary is empty")
    entries = {word: [] for word in requested}
    for line in raw.decode("utf-8-sig").splitlines():
        fields = line.split()
        if not fields or fields[0].lower() not in entries:
            continue
        # MFA dictionaries may prepend pronunciation/silence probabilities.
        index = 1
        while index < len(fields):
            try:
                float(fields[index])
            except ValueError:
                break
            index += 1
        phones = fields[index:]
        if not phones or any(not re.fullmatch(r"[A-Za-z]+[012]?", p) for p in phones):
            raise ValueError("Unsupported or malformed ARPA dictionary entry")
        variants = entries[fields[0].lower()]
        if phones not in variants:
            variants.append(phones)
    return entries, hashlib.sha256(raw).hexdigest()


def sound_occurrences(token, phones):
    """Address a supplied pronunciation, not an inferred/selected pronunciation.

    Caller must verify aligned word correspondence before using these identities.
    Scope IDs with attempt/input_revision in storage; hashes are not authorization.
    """
    if not phones or any(not isinstance(p, str) or not re.fullmatch(r"[A-Za-z]+[012]?", p) for p in phones):
        raise ValueError("Provide a nonempty ARPA pronunciation")
    variant = hashlib.sha256(" ".join(phones).encode()).hexdigest()
    return [dict(word_index=token["word_index"], phone_index=i,
                 original_phone=p, expected_phone=re.sub(r"[012]$", "", p),
                 occurrence_id=f'{token["occurrence_id"]}:{variant}:p{i}')
            for i, p in enumerate(phones)]


def prepare_transcript(text, settings):
    """Return a preflight dictionary, not a session, confirmation, or job result.

    Offsets are half-open Python Unicode code-point indices into original_text.
    No spelling correction, number expansion, G2P fallback, or dictionary writes.
    """
    result = dict(ok=False, original_text=text if isinstance(text, str) else None,
                  normalized_text=None, normalization_version=NORMALIZATION_VERSION,
                  transcript_sha256=None, tokens=[], word_count=0,
                  character_count=len(text) if isinstance(text, str) else None,
                  missing_words=[], dictionary=None, error=None, reason_code=None)

    def fail(code, reason, message, retryable=False):
        return dict(result, reason_code=reason,
                    error=dict(code=code, user_message=message, retryable=retryable))

    if not isinstance(text, str):
        return fail("UNSUPPORTED_TEXT", "INVALID_TYPE", "Enter the transcript as text.")
    if len(text) > MAX_CHARACTERS:
        return fail("UNSUPPORTED_TEXT", "TOO_MANY_CHARACTERS", "Use at most 200 characters, including spaces and punctuation.")
    if not text.strip():
        return fail("UNSUPPORTED_TEXT", "EMPTY_TEXT", "Enter between 1 and 12 English words.")
    matches = list(WORD.finditer(text))
    covered = set(i for m in matches for i in range(m.start(), m.end()))
    for i, char in enumerate(text):
        if i not in covered and char not in SEPARATORS and char not in " \t\r\n":
            result["invalid_character"] = dict(character=char, source_start=i, source_end=i + 1)
            return fail("UNSUPPORTED_TEXT", "UNSUPPORTED_CHARACTER", "Use English letters and sentence punctuation; spell out numbers and rewrite symbols or hyphenated words explicitly.")
    result["word_count"] = len(matches)
    if not 1 <= len(matches) <= MAX_WORDS:
        return fail("UNSUPPORTED_TEXT", "WORD_LIMIT", "Use between 1 and 12 words; contractions count as one word.")
    fingerprint = hashlib.sha256((NORMALIZATION_VERSION + "\0" + text).encode("utf-8")).hexdigest()
    result["transcript_sha256"] = fingerprint
    for i, m in enumerate(matches):
        original = m.group()
        result["tokens"].append(dict(original_token=original, normalized_token=original.replace("\u2019", "'").lower(),
                                     word_index=i, source_start=m.start(), source_end=m.end(),
                                     occurrence_id=f"{fingerprint}:w{i}", pronunciations=[]))
    result["normalized_text"] = " ".join(t["normalized_token"] for t in result["tokens"])
    try:
        cfg = load_settings(settings)
        path = _dictionary_path(cfg)
        entries, digest = _dictionary_entries(path, {t["normalized_token"] for t in result["tokens"]})
        result["dictionary"] = dict(configured_name=cfg["mfa"]["dictionary"], sha256=digest)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return fail("MODEL_UNAVAILABLE", "DICTIONARY_UNAVAILABLE", "The configured MFA dictionary could not be read. Ask the project team to check its installation and configuration.", True)
    for token in result["tokens"]:
        token["pronunciations"] = entries[token["normalized_token"]]
        if not token["pronunciations"]:
            result["missing_words"].append({k: token[k] for k in
                                           ("original_token", "normalized_token", "word_index", "source_start", "source_end", "occurrence_id")})
    if result["missing_words"]:
        return fail("UNSUPPORTED_TEXT", "MISSING_DICTIONARY_WORDS", "Some words are not in the configured dictionary. Check their spelling or choose supported words; this is not a pronunciation error.")
    return dict(result, ok=True)
