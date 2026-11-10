"""Project authoritative saved results into minimal coaching evidence, never audio."""
import hashlib
import json
import re

from speech_content import words
from .contract import Evidence


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True,allow_nan=False).encode()).hexdigest()


def _sound_projection(row):
    return [row.get(k) for k in ('word','expected_phone','status','outcome','reason_code','reason','message',
                                 'alternative_phone','word_index','phone_index','occurrence_id')]


def base_projection(data):
    """Cross-runtime array of strings/integers/nulls; no float serialization ambiguity."""
    if data.get('prompt_id'):
        result=data.get('result') or {};content=result.get('spoken_words_verification') or {}
        return [1,'preset',data.get('prompt_id'),data.get('status'),data.get('sentence'),content.get('transcript'),
                content.get('status'),result.get('run_id'),result.get('overall_status'),
                [_sound_projection(r) for r in result.get('target_assessment',{}).get('targets',[])],
                result.get('learner_audio',{}).get('warnings',[]),result.get('learner_audio',{}).get('reason')]
    return [1,'practice',data.get('input_revision'),data.get('learner_audio_id'),data.get('analysis_status'),
            data.get('confirmed_text'),data.get('recognized_text'),
            [_sound_projection(r) for r in data.get('sound_results',[])],data.get('limitations',[]),
            data.get('errors',{}).get('analysis',{}).get('code'),data.get('errors',{}).get('transcription',{}).get('code')]


def base_version(data):
    # Arrays have no object-key order to reconcile with browser JSON.stringify.
    return digest(base_projection(data))


def build_evidence(data,catalog,plan=None,language='en'):
    preset=bool(data.get('prompt_id'));result=data.get('result') or {} if preset else data
    selected=data.get('sentence') if preset else data.get('confirmed_text')
    content=result.get('spoken_words_verification') or {} if preset else {}
    recognized=content.get('transcript') if preset else data.get('recognized_text')
    rows=result.get('target_assessment',{}).get('targets',[]) if preset else data.get('sound_results',[])
    def outcome(row):return row.get('outcome') or {'expected_supported':'supported','alternative_favored':'practice'}.get(row.get('status'),'inconclusive')
    row=max(rows,key=lambda r:{'practice':3,'inconclusive':2,'supported':1}.get(outcome(r),0),default={})
    prompt=catalog.get(data.get('prompt_id') or data.get('lesson_id'),{})
    spec=next(iter(prompt.get('assessment_targets',[])),{})
    word=row.get('word') or spec.get('word');sound=row.get('expected_phone') or spec.get('phone')
    sound=sound if sound in {'TH','IH','AE'} else None
    status=data.get('status') if preset else data.get('analysis_status')
    if status not in {'completed','failed'}:raise ValueError('No completed or failed result to explain')
    flags=tuple(f for f in ('possible_clipping','silent_audio') if f in result.get('learner_audio',{}).get('warnings',[]) or f==result.get('learner_audio',{}).get('reason'))
    heard=words(recognized.replace('’',"'")) if isinstance(recognized,str) else []
    expected=words(selected.replace('’',"'")) if isinstance(selected,str) else []
    limits=result.get('limitations',[])
    content_unverified=any(str(s).startswith('CONTENT_UNVERIFIED') for s in limits)
    token_difference=bool(heard and expected and heard!=expected)
    # This explains the existing guard; mere string inequality never creates a sound error.
    unavailable=content.get('status')=='unavailable' or content_unverified
    difference=content.get('status')=='mismatch' or (token_difference and content.get('status') not in {'match','target_variant'})
    code=result.get('errors',{}).get('transcription',{}).get('code')
    if flags:category,reason,obs='audio_quality_issue',('DETECTED_CLIPPING' if 'possible_clipping' in flags else 'SILENT_AUDIO'),('detected_clipping' if 'possible_clipping' in flags else 'detected_silence')
    elif status=='failed':category,reason,obs='processing_error','PROCESSING_FAILED','technical_failure'
    elif code=='TRANSCRIPTION_EMPTY' or isinstance(recognized,str) and not heard:
        category,reason,obs='insufficient_evidence','EMPTY_TRANSCRIPT','empty_transcript'
    elif recognized is None:category,reason,obs='insufficient_evidence','TRANSCRIPT_UNAVAILABLE','transcript_unavailable'
    elif difference or unavailable:
        if heard==expected and content.get('status')=='mismatch':category,reason,obs='insufficient_evidence','CONTENT_UNVERIFIED','no_qualified_comparison'
        elif word and str(word).lower() in heard:category,reason,obs='insufficient_evidence','CONTEXT_NOT_VERIFIED','target_in_transcript_context_unverified'
        elif word and heard and difference:category,reason,obs='target_word_not_confirmed','TARGET_NOT_CONFIRMED','target_not_established'
        else:category,reason,obs='insufficient_evidence','CONTENT_UNVERIFIED','no_qualified_comparison'
    elif not sound or row.get('reason_code') in {'UNSUPPORTED_SOUND','MISSING_DICTIONARY_WORD','DICTIONARY_MISSING'}:category,reason,obs='insufficient_evidence','UNSUPPORTED_SOUND','unsupported_coverage'
    elif outcome(row)=='supported':category,reason,obs='expected_sound_favored','EXPECTED_COMPARISON','expected_comparison'
    elif outcome(row)=='practice':category,reason,obs='alternative_sound_favored','ALTERNATIVE_COMPARISON','alternative_comparison'
    else:category,reason,obs='insufficient_evidence',('NO_SUPPORTED_TARGETS' if not rows else 'NO_QUALIFIED_SOUND_EVIDENCE'),'no_qualified_comparison'
    if category=='audio_quality_issue':tips=['mic-clipping-v1' if 'possible_clipping' in flags else 'mic-silence-v1']
    elif category=='processing_error':tips=['technical-retry-v1']
    elif category=='target_word_not_confirmed' or reason in {'EMPTY_TRANSCRIPT','CONTENT_UNVERIFIED','CONTEXT_NOT_VERIFIED','TRANSCRIPT_UNAVAILABLE'}:tips=['review-words-v1']
    elif sound and reason!='UNSUPPORTED_SOUND':tips=['sound-'+sound.lower()+'-v1']
    else:tips=[]
    context='general_practice';eligible=[]
    if plan and plan.get('started'):
        context='starting_check' if plan.get('kind')=='assessment' else 'lesson_plan'
        current=data.get('prompt_id') or data.get('lesson_id')
        if current in plan['completed'] and category not in {'target_word_not_confirmed','audio_quality_issue','processing_error'} and reason not in {'CONTEXT_NOT_VERIFIED','CONTENT_UNVERIFIED','EMPTY_TRANSCRIPT','TRANSCRIPT_UNAVAILABLE'}:
            next_id=next((s['lesson_id'] for s in plan.get('steps',[]) if s['lesson_id'] in catalog and s['lesson_id'] not in plan['completed']),None)
            if next_id:eligible=[next_id]
    elif category in {'expected_sound_favored','alternative_sound_favored','insufficient_evidence'} and sound and reason not in {'EMPTY_TRANSCRIPT','TRANSCRIPT_UNAVAILABLE','CONTENT_UNVERIFIED','CONTEXT_NOT_VERIFIED','UNSUPPORTED_SOUND'}:
        candidates=[p['id'] for p in catalog.values() if sound in p.get('target_phones',[]) and p['id']!=(data.get('prompt_id') or data.get('lesson_id'))]
        eligible=candidates[:2]
    alternative=row.get('alternative_phone')
    position=row.get('word_index')
    return Evidence(selected_sentence=selected,recognized_words=recognized,target_word=word,target_sound=sound,
        target_word_index=position if type(position) is int and 0<=position<12 else None,
        result_category=category,reason_code=reason,supported_observations=(obs,),
        tested_alternatives=(alternative,) if isinstance(alternative,str) and re.fullmatch('[A-Z]{1,5}',alternative) else None,
        audio_quality_flags=flags,approved_tip_ids=tuple(tips),approved_next_exercise_ids=tuple(eligible),
        exercise_context=context,language=language)
