"""Single-source lesson validation; no reference waveform is required."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def validate_lessons(entries, *, require_practice=False):
    if not isinstance(entries, list) or not entries:
        raise ValueError('Expected a nonempty lesson list.')
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Each lesson must be an object.')
        for key in ('id', 'text'):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError(f'Every lesson needs {key}.')
        if not re.fullmatch(r'[a-z0-9_]+', entry['id']) or entry['id'] in seen:
            raise ValueError('Invalid or duplicate lesson ID.')
        seen.add(entry['id'])
        tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", entry['text'].lower())
        if not 1 <= len(tokens) <= 12:
            raise ValueError('Lessons must contain 1–12 words for this short-recording prototype.')
        if entry.get('reference_wav') is not None and not isinstance(entry['reference_wav'], str):
            raise ValueError('Optional reference_wav must be a string.')
        for key in ('target_words', 'target_phones', 'lesson_links'):
            entry.setdefault(key, [])
            if not isinstance(entry[key], list):
                raise ValueError(f'{key} must be a list.')
        for link in entry['lesson_links']:
            if not isinstance(link, dict) or not isinstance(link.get('title'), str) or urlparse(link.get('url', '')).scheme != 'https':
                raise ValueError('Lesson links require a title and HTTPS URL.')
        targets = entry.get('assessment_targets', [])
        if not isinstance(targets, list):
            raise ValueError('assessment_targets must be a list.')
        identities = set()
        for target in targets:
            if not isinstance(target, dict) or not all(isinstance(target.get(k), str) and target[k] for k in ('word', 'phone')):
                raise ValueError('Target needs word and phone.')
            alternatives = target.get('alternatives')
            if not isinstance(alternatives, list) or not alternatives or not all(isinstance(a, str) and a for a in alternatives):
                raise ValueError('Target needs alternative phones.')
            identity = (target['word'].lower(), target['phone'])
            if identity in identities or tokens.count(identity[0]) != 1:
                raise ValueError('Each target must identify one unique word occurrence.')
            if target['phone'] in alternatives or len(set(alternatives)) != len(alternatives):
                raise ValueError('Alternative phones must be distinct from the expected phone.')
            identities.add(identity)
        alternatives = entry.get('content_alternatives', {})
        if not isinstance(alternatives, dict) or any(k not in tokens or not isinstance(v, list) or not all(isinstance(w, str) and re.fullmatch(r"[a-z]+(?:'[a-z]+)?", w) for w in v) for k, v in alternatives.items()):
            raise ValueError('Content alternatives must map sentence words to single lowercase words.')
        if require_practice or 'practice_words' in entry:
            if not isinstance(entry.get('practice_tip'), str) or not entry['practice_tip'].strip():
                raise ValueError('Lesson needs a practice tip.')
            practice = entry.get('practice_words')
            if not isinstance(practice, list) or not practice:
                raise ValueError('Lesson needs practice words.')
            displayed = set()
            for word in practice:
                if not isinstance(word, dict) or word.get('word', '').lower() not in tokens or not isinstance(word.get('sounds'), list):
                    raise ValueError('Practice words must occur in the sentence and contain sounds.')
                for sound in word['sounds']:
                    if not isinstance(sound, dict) or not all(isinstance(sound.get(k), str) and sound[k] for k in ('phone', 'label', 'hint')):
                        raise ValueError('Each sound needs phone, label, and hint.')
                    displayed.add((word['word'].lower(), sound['phone']))
            if not identities or not identities <= displayed:
                raise ValueError('Every assessment target must have a practice hint.')
    return entries


def load_lessons(path, *, require_practice=False):
    return validate_lessons(json.loads(Path(path).read_text(encoding='utf-8')), require_practice=require_practice)
