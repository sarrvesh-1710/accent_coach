"""Trusted confirmed-text worker and storage integration seam, not a public API.

No persistent storage or authentication implementation lives here. Only server
code may construct a worker snapshot. See docs/DAY_2_PHASE_4.md for obligations.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import time
from typing import Protocol

import audio_io
from assessment import summarize_assessment
from phoneme_scoring.align_audio import align_audio, load_settings, prepare_audio
from phoneme_scoring.gop_score import score_phonemes
from pipeline import _LOCK, _validate_alignment, _validate_scores, json_safe
from transcript_input import prepare_transcript, sound_occurrences

CONTRASTS = {"TH": ["S", "T", "F"], "IH": ["IY"], "AE": ["EH"]}


class AnalysisStore(Protocol):
    """Proposed internal seam for Lucas; neither method is a browser API.

    Resolve must authenticate auth, authorize attempt/job/learner asset ownership,
    require explicit confirmation and an active processing analysis job, and check
    input_revision. Publication is a single atomic compare-and-set, including
    owner, job ID/kind/state, revision, text and asset identity. False rejects stale
    work. Raise PermissionError on unauthorized, deleted or missing resources.
    """
    def resolve_analysis_snapshot(self, auth, attempt_id, job_id, input_revision): ...
    def publish_analysis_if_current(self, auth, snapshot, result) -> bool: ...


def _error(code, message, **identity):
    return dict(ok=False, error=dict(code=code, user_message=message,
                                    retryable=code in {"MODEL_UNAVAILABLE", "TIMEOUT"}), **identity)


def _targets(alignment, prepared):
    words = alignment.get("words", [])
    tokens = prepared["tokens"]
    if (len(words) != len(tokens) or len({w["segment_id"] for w in words}) != len(words)
            or any(w["word"].lower().replace("\u2019", "'") != t["normalized_token"] for w, t in zip(words, tokens))):
        return [], "ALIGNMENT_WORD_MISMATCH"
    targets = []
    for word, token in zip(words, tokens):
        phones = [s for s in alignment["segments"] if s.get("word_id") == word["segment_id"]
                  and s["canonical_phone"].lower() not in {"sil", "sp", "", "<eps>"}]
        if not phones:
            return [], "ALIGNMENT_WORD_MISMATCH"
        try:
            occurrences = sound_occurrences(token, [s.get("original_phone", s["canonical_phone"]) for s in phones])
        except ValueError:
            return [], "UNSUPPORTED_CONTEXT"
        for seg, occurrence in zip(phones, occurrences):
            phone = seg["canonical_phone"]
            if phone in CONTRASTS:
                targets.append(dict(occurrence, word=token["normalized_token"], phone=phone,
                                    segment_id=seg["segment_id"], alternatives=CONTRASTS[phone]))
    return targets, None


def run_confirmed_attempt(snapshot, settings):
    """Analyze a server-resolved immutable snapshot; never accept browser payloads.

    Returns an unpublished result. Use execute_confirmed_analysis for guarded
    resolution/publication. Temporary audio and MFA artifacts are cleaned up.
    """
    snapshot = deepcopy(snapshot)
    identity = {k: snapshot.get(k) for k in ("attempt_id", "job_id", "input_revision", "learner_audio_id")}
    result = dict(ok=False, **identity, analysis_status="failed", sound_results=[],
                  limitations=[], timings={}, error=None)

    def fail(code, message, reason_code=None):
        return dict(result, ok=False, analysis_status="failed", sound_results=[],
                    error=_error(code, message)["error"], reason_code=reason_code)

    if (any(not isinstance(identity[k], str) or not identity[k] for k in ("attempt_id", "job_id", "learner_audio_id"))
            or type(identity["input_revision"]) is not int or identity["input_revision"] < 1):
        return fail("REVISION_CONFLICT", "A valid server-resolved attempt, job and revision are required.")
    if snapshot.get("target_accent") != "en-US-general-american":
        return fail("UNSUPPORTED_ACCENT", "Select General American English.")
    if snapshot.get("learner_audio_role") != "learner":
        return fail("INVALID_AUDIO", "Analysis requires the original learner recording, not generated audio.")
    if snapshot.get("transcript_confirmed") is not True or not snapshot.get("confirmed_text"):
        return fail("TRANSCRIPT_CONFIRMATION_REQUIRED", "Confirm the transcript before analysis.")
    try:
        settings = deepcopy(load_settings(settings))
        prepared = prepare_transcript(snapshot["confirmed_text"], settings)
        if not prepared["ok"]:
            return dict(result, error=prepared["error"], preparation=prepared)
        result["confirmed_text"] = snapshot["confirmed_text"]
        result["normalized_text"] = prepared["normalized_text"]
        source = Path(snapshot["learner_audio_path"])
        if audio_io.inspect_audio_file(source)["status"] != "ok":
            return fail("INVALID_AUDIO", "Use a readable learner WAV within five seconds and 10 MB.")
        raw = source.read_bytes()
        if len(raw) > audio_io.MAX_AUDIO_BYTES or hashlib.sha256(raw).hexdigest() != snapshot.get("source_audio_sha256"):
            return fail("INVALID_AUDIO", "The learner recording changed; attach and confirm it again.")
        result["source_audio_sha256"] = snapshot["source_audio_sha256"]
        queued = time.monotonic()
        with _LOCK, tempfile.TemporaryDirectory(prefix="accent_confirmed_") as work:
            started = time.monotonic()
            stages = {}
            def timed(name, function, *args):
                begin = time.monotonic()
                try:
                    return function(*args)
                finally:
                    stages[name] = (time.monotonic() - begin) * 1000
                    result["timings"]["analysis"] = dict(queue_ms=(started-queued)*1000,
                        processing_ms=(time.monotonic()-started)*1000, stages_ms=stages)
            path = Path(work) / "learner.wav"
            path.write_bytes(raw)
            audio = timed("audio", audio_io.prepare_audio, path, settings)
            if audio["status"] not in {"ok", "warning"}:
                return fail("INVALID_AUDIO", "The learner recording could not be prepared.")
            fingerprint = prepare_audio(path, settings)[2]
            result["audio_sha256"] = fingerprint
            asr = snapshot.get("transcription") or {}
            recognized = prepare_transcript(asr.get("recognized_text"), settings)
            content_match = (asr.get("status") == "completed" and asr.get("source_audio_sha256") == result["source_audio_sha256"]
                             and asr.get("audio_sha256") == fingerprint and bool(asr.get("model_id")) and bool(asr.get("model_revision"))
                             and recognized["ok"] and recognized["normalized_text"] == prepared["normalized_text"])
            result["transcription_provenance"] = {k: asr.get(k) for k in
                ("status", "recognized_text", "source_audio_sha256", "audio_sha256", "model_id", "model_revision")}
            alignment = timed("alignment", align_audio, str(path), prepared["normalized_text"], settings, work)
            if alignment.get("status") != "available":
                timed_out = "TimeoutExpired" in str(alignment.get("reason", ""))
                return fail("TIMEOUT" if timed_out else "MODEL_UNAVAILABLE",
                            "Alignment could not finish; check MFA and retry.", "ALIGNMENT_FAILED")
            try:
                _validate_alignment(alignment, audio["duration_sec"])
                if alignment.get("audio_sha256") != fingerprint:
                    raise ValueError("Wrong audio")
            except (ValueError, KeyError, TypeError):
                return fail("MODEL_UNAVAILABLE", "Alignment returned invalid recording boundaries or identity.", "INVALID_ALIGNMENT")
            targets, limitation = _targets(alignment, prepared)
            settings["_assessment_targets"] = targets
            scored = timed("phoneme_analysis", score_phonemes, str(path), alignment, settings)
            if scored.get("status") not in {"available", "uncertain", "partial"}:
                return fail("MODEL_UNAVAILABLE", "The phoneme model could not complete analysis.", "PHONEME_ANALYSIS_FAILED")
            if scored.get("audio_sha256") != fingerprint:
                return fail("INVALID_AUDIO", "Phoneme results belong to a different recording.")
            _validate_scores(scored, alignment)
            assessment = summarize_assessment(dict(prompt={"assessment_targets": targets}, phoneme_results=scored,
                learner_audio=audio, spoken_words_verification={"status": "match" if content_match else "unavailable"}))
            evidence = {r.get("segment_id"): r for r in assessment["targets"]}
            local = {r["segment_id"]: r for r in scored["segments"]}
            for spec in targets:
                row = evidence.get(spec["segment_id"], {})
                outcome = {"expected_supported": "supported", "alternative_favored": "practice"}.get(row.get("status"), "inconclusive")
                reason = None if outcome != "inconclusive" else "INSUFFICIENT_EVIDENCE"
                if local.get(spec["segment_id"], {}).get("status") == "unsupported":
                    outcome, reason = "inconclusive", "UNSUPPORTED_SOUND"
                result["sound_results"].append(dict(word=spec["word"], word_index=spec["word_index"],
                    phone_index=spec["phone_index"], occurrence_id=spec["occurrence_id"], expected_phone=spec["phone"],
                    alternative_phone=row.get("alternative_phone"), outcome=outcome, reason_code=reason,
                    message=row.get("reason") or "No reliable sound comparison is available."))
            if limitation:
                result["limitations"].append(limitation)
            elif not targets:
                result["limitations"].append("NO_SUPPORTED_TARGETS")
            if not content_match:
                result["limitations"].append("CONTENT_UNVERIFIED: confirmed text was aligned for diagnostics only.")
            result["limitations"].append("Experimental sound evidence, not a pronunciation grade or confirmed error.")
            result.update(ok=True, analysis_status="completed")
            return json_safe(result)
    except Exception:
        return fail("MODEL_UNAVAILABLE", "Analysis inputs or model output could not be processed; check configuration and retry.")


def execute_confirmed_analysis(auth, attempt_id, job_id, input_revision, *, store: AnalysisStore, settings):
    """Resolve through authorized storage and publish only through atomic CAS.

    This is a synchronous internal worker adapter, not submit_analysis or a queue.
    No result is returned to the caller after rejected publication.
    """
    try:
        snapshot = deepcopy(store.resolve_analysis_snapshot(auth, attempt_id, job_id, input_revision))
    except PermissionError:
        return _error("ATTEMPT_UNAVAILABLE", "This attempt is unavailable.")
    if any(snapshot.get(k) != v for k, v in
           (("attempt_id", attempt_id), ("job_id", job_id), ("input_revision", input_revision))):
        return _error("REVISION_CONFLICT", "This analysis request is no longer current.")
    result = run_confirmed_attempt(snapshot, settings)
    try:
        accepted = store.publish_analysis_if_current(auth, snapshot, result)
    except PermissionError:
        accepted = False
    if not accepted:
        return _error("REVISION_CONFLICT", "The attempt changed or was removed; this result was discarded.")
    return result
