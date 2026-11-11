"""Versioned, bounded evidence and closed-world coaching validation."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EVIDENCE_VERSION = 'coach-evidence-v1'
PROMPT_VERSION = 'coach-prompt-v1'
CONSENT_VERSION = 'coach-text-consent-v1'
Category = Literal['expected_sound_favored','alternative_sound_favored','target_word_not_confirmed',
                   'insufficient_evidence','audio_quality_issue','processing_error']
Observation = Literal['expected_comparison','alternative_comparison','target_not_established',
                      'target_in_transcript_context_unverified','no_qualified_comparison',
                      'unsupported_coverage','empty_transcript','transcript_unavailable',
                      'detected_clipping','detected_silence','technical_failure']


class Evidence(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    schema_version: Literal['coach-evidence-v1'] = EVIDENCE_VERSION
    selected_sentence: str | None = Field(max_length=200)
    recognized_words: str | None = Field(max_length=200)
    target_word: str | None = Field(max_length=200)
    target_sound: Literal['TH','IH','AE'] | None
    target_word_index: int | None = Field(default=None,ge=0,le=11)
    result_category: Category
    reason_code: str = Field(min_length=1,max_length=64,pattern=r'^[A-Z_]+$')
    supported_observations: tuple[Observation,...] = Field(max_length=3)
    tested_alternatives: tuple[str,...] | None = Field(max_length=8)
    audio_quality_flags: tuple[Literal['possible_clipping','silent_audio'],...] = ()
    approved_tip_ids: tuple[str,...] = Field(max_length=3)
    approved_next_exercise_ids: tuple[str,...] = Field(max_length=3)
    exercise_context: Literal['starting_check','lesson_plan','general_practice']
    language: Literal['en'] = 'en'

    @model_validator(mode='after')
    def grounded(self):
        required={'expected_sound_favored':'expected_comparison',
                  'alternative_sound_favored':'alternative_comparison',
                  'target_word_not_confirmed':'target_not_established',
                  'processing_error':'technical_failure'}
        if self.result_category in required and required[self.result_category] not in self.supported_observations:
            raise ValueError('Category lacks supporting evidence')
        if self.result_category=='audio_quality_issue' and not self.audio_quality_flags:
            raise ValueError('Audio claims require measured flags')
        if self.result_category in {'expected_sound_favored','alternative_sound_favored'} and (not self.target_sound or self.audio_quality_flags):
            raise ValueError('Unsupported positive comparison')
        if self.tested_alternatives and any(not re.fullmatch(r'[A-Z]{1,5}',p) for p in self.tested_alternatives):
            raise ValueError('Invalid sound labels')
        return self


class CoachingOutput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    explanation: str = Field(min_length=1,max_length=400)
    practice_tip_id: str | None = Field(max_length=64)
    next_exercise_id: str | None = Field(max_length=64)


class CoachingRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_version: str=Field(pattern=r'^[0-9a-f]{64}$')
    language: Literal['en']='en'
    external_consent: bool=False
    consent_version: str | None=Field(default=None,max_length=64)
    provider_version: str | None=Field(default=None,pattern=r'^[0-9a-f]{64}$')


TIPS = {
 'sound-th-v1': ('TH', 'Let air flow gently with your tongue tip lightly between your teeth. This is general practice guidance.'),
 'sound-ih-v1': ('IH', 'Practice the short vowel in ship and compare it with the vowel in sheep. Listen before trying again.'),
 'sound-ae-v1': ('AE', 'Practice the vowel in bad and compare it with bed. This is general guidance, not a measured mouth position.'),
 'review-words-v1': (None, 'Replay your recording and compare the intended words with the transcript. Transcription can be mistaken.'),
 'mic-clipping-v1': (None, 'Move a little farther from the microphone and record again to reduce possible distortion.'),
 'mic-silence-v1': (None, 'Check that your microphone is selected and captures speech, then make a new short recording.'),
 'technical-retry-v1': (None, 'Keep your saved recording. Use the available retry action, or record again if retry is not offered.'),
}


def explanations(e: Evidence):
    """Reviewed choices, not arbitrary model prose. Never interpolate untrusted text."""
    if e.reason_code=='EMPTY_TRANSCRIPT':
        return ['No words were recognized, so the intended sound could not be established. Review the transcript or try another recording; this does not prove incorrect pronunciation.',
                'An empty transcription is a limit of this check, not a pronunciation judgment. Replay your recording before deciding what to try next.']
    if e.reason_code in {'CONTENT_UNVERIFIED','CONTEXT_NOT_VERIFIED','TRANSCRIPT_UNAVAILABLE'}:
        return ['Usable sound evidence has not been established for this check. Review the words and recording; recognizing a word does not prove its pronunciation.',
                'This result does not establish a sound comparison. Replay your recording and review the transcript before trying again.']
    if e.reason_code in {'UNSUPPORTED_SOUND','NO_SUPPORTED_TARGETS'}:
        return ['This check does not cover the requested sound or word. It has not been marked incorrect; an available sound exercise may offer a supported comparison.',
                'The current comparison has limited sound coverage. An unsupported sound is not evidence of incorrect pronunciation.']
    return {
      'expected_sound_favored': ['This is a limited comparison, not a whole-sentence grade. Another short exercise can let you practice the same sound in a new context.',
                                'The result favors the expected sound only within this comparison. You can repeat the sentence or explore the next eligible exercise.'],
      'alternative_sound_favored': ['A tested alternative was favored in this attempt, but that is not a confirmed error. Replay the word before trying the suggested practice.',
                                   'This comparison suggests a sound to explore, not a definitive mistake. Use one practice tip and listen again.'],
      'target_word_not_confirmed': ['The intended word was not established for this check. Compare the selected words with the transcript, then replay your recording before deciding whether to review the text or record again.',
                                    'The spoken words or the transcription may differ from the selected words. This does not establish a pronunciation error.'],
      'insufficient_evidence': ['This attempt does not establish a reliable sound comparison. Another short attempt may provide more evidence, but this result does not mean your pronunciation was wrong.',
                                'There is not enough qualified sound evidence to make this comparison. Replay the recording before deciding whether to try again.'],
      'audio_quality_issue': (['The app detected possible clipping, which limits this check. Move a little farther from the microphone and record again.',
                              'Possible distortion was detected in the recording. Try the approved microphone recovery tip before another attempt.'] if 'possible_clipping' in e.audio_quality_flags else
                             ['The app detected no usable speech in this recording. Check your microphone and make another short recording.',
                              'The recording did not provide usable speech for this check. Try the approved microphone recovery step.']),
      'processing_error': ['A technical step did not finish, so this check provides no pronunciation judgment. Keep your saved recording and use the available retry or recording action.',
                           'The analysis could not finish for a technical reason. This is not a finding about your pronunciation.'],
    }[e.result_category]


def output_schema(e):
    return dict(type='object',additionalProperties=False,
        properties=dict(explanation=dict(type='string',enum=explanations(e)),
                        practice_tip_id=dict(type=['string','null'],enum=[None,*e.approved_tip_ids]),
                        next_exercise_id=dict(type=['string','null'],enum=[None,*e.approved_next_exercise_ids])),
        required=['explanation','practice_tip_id','next_exercise_id'])


def validate_output(raw, e):
    result=CoachingOutput.model_validate(raw)
    text=result.explanation
    if len(re.findall(r"\b[\w']+\b",text))>45 or len([s for s in re.split(r'[.!?]+',text) if s.strip()])>2:
        raise ValueError('Explanation exceeds bounds')
    # Independent semantic compatibility checks as well as a strict response schema.
    if re.search(r'\b(heard|listened|perfect|nationality|diagnosis|improved|percent|score)\b|\d|%',text,re.I):
        raise ValueError('Unsupported claim')
    if not e.audio_quality_flags and re.search(r'\b(quiet|noisy|distortion|clipping)\b',text,re.I):
        raise ValueError('Unsupported audio claim')
    if text not in explanations(e):
        raise ValueError('Unreviewed or incompatible explanation')
    if result.practice_tip_id is not None and (result.practice_tip_id not in e.approved_tip_ids or result.practice_tip_id not in TIPS):
        raise ValueError('Unapproved tip')
    if result.next_exercise_id is not None and result.next_exercise_id not in e.approved_next_exercise_ids:
        raise ValueError('Unapproved exercise')
    return result
