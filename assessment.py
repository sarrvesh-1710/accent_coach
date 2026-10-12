"""Apply recording/content safeguards to experimental target evidence."""
from copy import deepcopy


def summarize_assessment(result):
    specs = result.get("prompt", {}).get("assessment_targets", [])
    sequence = result.get("phoneme_results", {}).get("sequence_evidence", {})
    rows = deepcopy(sequence.get("targets", []))
    if not rows:
        rows = [dict(word=s["word"], expected_phone=s["phone"], status="insufficient_evidence",
                     reason=sequence.get("reason", "Target comparison unavailable.")) for s in specs]
    content = result.get("spoken_words_verification", {}).get("status")
    blocked = None
    if result.get("learner_audio", {}).get("status") not in {"ok", "warning"}:
        blocked = "Recording is unavailable or unusable."
    elif "possible_clipping" in result.get("learner_audio", {}).get("warnings", []):
        blocked = "Recording may be distorted; record again."
    elif content not in {"match", "target_variant"}:
        blocked = "Sentence check did not confirm usable content; no sound judgment is shown."
    for row in rows:
        if blocked:
            row.update(status="insufficient_evidence", reason=blocked)
    return dict(status="available" if rows and not blocked and sequence.get("status") == "available" else "limited",
                targets=rows, grade=None, calibrated=False,
                scope="Target sounds only; not a whole-sentence grade.",
                reason=blocked, content_status=content)
