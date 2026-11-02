"""Opt-in reuse of MFA 3.3.7 dictionary artifacts, never recording/results.

Caller must hold the existing MFA process lock. Seed copies go into a fresh
request directory; MFA never writes directly to a published cache entry.
Unsupported installations or cache errors fall back to normal compilation.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

FILES = ('L.fst', 'L_align.fst', 'words.txt', 'phones.txt')
SCHEMA = 1


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def plan(cfg):
    """Return a private resource-cache plan for the inspected direct install."""
    location = cfg.get('dictionary_cache_directory')
    if not isinstance(location, str) or not Path(location).is_absolute():
        raise ValueError('Cache directory must be an absolute server-controlled path')
    command = cfg.get('command', [cfg.get('executable', '')])
    if len(command) != 1 or Path(command[0]).name.lower() != 'mfa.exe':
        raise ValueError('Dictionary cache experiment requires direct Windows MFA')
    prefix = Path(command[0]).resolve().parent.parent
    metadata = list((prefix / 'conda-meta').glob('montreal-forced-aligner-*.json'))
    if len(metadata) != 1 or json.loads(metadata[0].read_text(encoding='utf-8')).get('version') != '3.3.7':
        raise ValueError('Dictionary cache experiment supports installed MFA 3.3.7 only')
    environment = {**os.environ, **cfg.get('environment', {})}
    mfa_root = Path(environment.get('MFA_ROOT_DIR', '~/Documents/MFA')).expanduser().resolve()

    def resource(value, kind, suffix):
        candidate = Path(value).expanduser()
        if not candidate.is_file():
            if candidate.name != value or candidate.suffix:
                raise ValueError('Configured resource file is unavailable')
            candidate = mfa_root / 'pretrained_models' / kind / (value + suffix)
        candidate = candidate.resolve(strict=True)
        if not candidate.is_file():
            raise ValueError('Resource cache requires installed files')
        return candidate

    dictionary = resource(cfg['dictionary'], 'dictionary', '.dict')
    acoustic = resource(cfg['acoustic_model'], 'acoustic', '.zip')
    runtime = sorted(p for pattern in ('montreal-forced-aligner-*', 'kalpy-*', 'pynini-*', 'openfst-*', 'python-*')
                     for p in (prefix / 'conda-meta').glob(pattern + '.json'))
    config_file = mfa_root / 'global_config.yaml'
    identity = dict(schema=SCHEMA, prefix=str(prefix),
        dictionary=[str(dictionary), digest(dictionary)], acoustic=[str(acoustic), digest(acoustic)],
        runtime=[(p.name, digest(p)) for p in runtime],
        global_config=digest(config_file) if config_file.is_file() else None,
        settings={k: v for k, v in cfg.items() if k != 'dictionary_cache_directory'},
        profile=environment.get('MFA_PROFILE'))
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    root = Path(location).resolve()
    return dict(root=root, entry=root / key, key=key, dictionary=dictionary.stem)


def request_dictionary(cache, temporary):
    return Path(temporary) / 'extracted_models' / 'dictionary' / cache['dictionary']


def seed(cache, temporary):
    """Validate all four immutable files before copying; false means rebuild."""
    entry = cache['entry']
    target = request_dictionary(cache, temporary)
    try:
        if entry.is_symlink() or not entry.is_dir():
            return False
        manifest = json.loads((entry / 'manifest.json').read_text(encoding='utf-8'))
        if not isinstance(manifest, dict) or not isinstance(manifest.get('files'), dict):
            return False
        if manifest.get('key') != cache['key'] or set(manifest.get('files', {})) != set(FILES):
            return False
        for name in FILES:
            source = entry / name
            if source.is_symlink() or not source.is_file() or not source.stat().st_size:
                return False
            if digest(source) != manifest['files'][name]:
                return False
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.dictionary-seed-', dir=target.parent) as directory:
            staging = Path(directory).resolve()
            if staging.parent != target.parent.resolve() or not staging.is_relative_to(Path(temporary).resolve()):
                raise ValueError('Invalid request cache path')
            for name in FILES:
                shutil.copyfile(entry / name, staging / name)
                if digest(staging / name) != manifest['files'][name]:
                    raise ValueError('Cache copy changed')
            staging.replace(target)
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def publish(cache, temporary):
    """Atomically publish completed resources only; retain corrupt entries for review."""
    root, entry = cache['root'], cache['entry']
    source = request_dictionary(cache, temporary)
    if entry.exists() or entry.is_symlink():
        return False
    for name in FILES:
        path = source / name
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            return False
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.dictionary-build-', dir=root) as directory:
        staging = Path(directory).resolve()
        if staging.parent != root or entry.parent != root:
            raise ValueError('Invalid cache publication path')
        hashes = {}
        for name in FILES:
            shutil.copyfile(source / name, staging / name)
            hashes[name] = digest(staging / name)
        (staging / 'manifest.json').write_text(json.dumps(dict(key=cache['key'], files=hashes)), encoding='utf-8')
        staging.replace(entry)
    return True
