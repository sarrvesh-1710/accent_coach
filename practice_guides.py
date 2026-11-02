"""Lucas-derived educational targets. Never imported by assessment workers."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

from accent_profiles import load_profile

ROOT = Path(__file__).resolve().parent
PROFILES = ('general', 'chinese')


def profile_guide(identity):
    if identity not in PROFILES:
        raise ValueError('Choose an available learner profile.')
    profile = load_profile(identity)
    return dict(id=identity, label='General practice' if identity == 'general' else 'Mandarin-speaking learner',
                target_accent='en-US-general-american',
                note=profile.get('description') or 'Practice General American English sounds.',
                calibration_status='not_enabled_in_app',
                limitation='The learner profile changes guidance only. It does not change sound judgments or provide a trained accent grade.')


@lru_cache(maxsize=1)
def _catalog():
    data = json.loads((ROOT / 'practice_targets.json').read_text(encoding='utf-8'))
    accent = data['accents']['general_american']
    return dict(label=accent['label'], sentences=accent['sentences'], variation_note=accent['variation_note'])


def practice_guides(identity='general'):
    return dict(profile=profile_guide(identity), profiles=[profile_guide(p) for p in PROFILES],
                **deepcopy(_catalog()))
