"""Local attempt storage. Refuse path traversal, symlinks, and Windows junctions."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import stat

ROOT = Path(__file__).resolve().parent / 'runs'
RUN_ID = re.compile(r'\d{8}T\d{6}_[a-f0-9]{12}')


def _plain(path):
    details = path.lstat()
    if path.is_symlink() or getattr(details, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
        raise ValueError('Linked files/directories cannot be used for history.')


def run_folder(run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError('Choose a saved attempt.')
    _plain(ROOT)
    folder = ROOT / run_id
    _plain(folder)
    if folder.resolve().parent != ROOT.resolve() or not folder.is_dir():
        raise ValueError('Attempt is outside the recordings folder.')
    return folder


def read_attempt(run_id):
    folder = run_folder(run_id)
    source = folder / 'results.json'
    _plain(source)
    if source.stat().st_size > 20_000_000:
        raise ValueError('Saved attempt is too large.')
    result = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(result, dict) or result.get('run_id') != run_id:
        raise ValueError('Saved attempt identity does not match.')
    audio = folder / 'learner.wav'
    if audio.exists():
        _plain(audio)
        audio_path = str(audio)
    else:
        audio_path = None
    return result, audio_path


def list_attempts(prompt_id=None, limit=50):
    if not ROOT.exists():
        return []
    _plain(ROOT)
    rows = []
    for folder in sorted(ROOT.iterdir(), key=lambda p: p.name, reverse=True):
        if not RUN_ID.fullmatch(folder.name):
            continue
        try:
            result, _ = read_attempt(folder.name)
        except (ValueError, OSError):
            continue
        if prompt_id and result.get('prompt_id') != prompt_id:
            continue
        stamp = datetime.strptime(folder.name[:15], '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
        rows.append((f"{stamp:%Y-%m-%d %H:%M:%S} UTC · {result.get('prompt', {}).get('text', result.get('prompt_id', 'Attempt'))}", folder.name))
        if len(rows) >= limit:
            break
    return rows


def delete_attempt(run_id):
    """Called only after the learner explicitly confirms deletion in the UI."""
    folder = run_folder(run_id)
    # A result identifies a finished attempt. Do not delete an in-progress run.
    read_attempt(run_id)
    for path in folder.rglob('*'):
        _plain(path)
        if not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError('Unsafe path in saved attempt.')
    shutil.rmtree(folder)


def history_view(run_id):
    if not run_id:
        return 'Choose an attempt to review.', None
    result, audio = read_attempt(run_id)
    recognized = result.get('spoken_words_verification', {}).get('transcript', 'Unavailable')
    lines = [f"Sentence: {result.get('prompt', {}).get('text', result.get('prompt_id', ''))}",
             f'Recognized words: {recognized}', 'Experimental outcomes, not grades:']
    for target in result.get('target_assessment', {}).get('targets', []):
        lines.append(f"{target['word']} / {target['expected_phone']}: {target['status'].replace('_', ' ')}")
    lines.append('Changes between attempts do not establish improvement.')
    return '\n'.join(lines), audio
