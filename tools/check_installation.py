"""Read-only local setup checks. No model download and no recording upload."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lesson_catalog import load_lessons
from phoneme_scoring.align_audio import load_settings, config_path


def main():
    checks = []
    def record(name, action):
        try:
            detail = action()
            checks.append(dict(check=name, status='ok', detail=str(detail)))
        except Exception as exc:
            checks.append(dict(check=name, status='unavailable', detail=str(exc)))
    record('lessons', lambda: f'{len(load_lessons(ROOT / "prompts.json", require_practice=True))} valid lessons')
    for package in ('numpy', 'scipy', 'soundfile', 'librosa', 'praat-parselmouth', 'gradio', 'torch', 'transformers', 'huggingface-hub', 'phonemizer'):
        record(package, lambda p=package: importlib.metadata.version(p))
    settings = load_settings(ROOT / 'phoneme_scoring/settings.json')
    from huggingface_hub import snapshot_download
    for key, id_key in (('model', 'id'), ('content_check', 'model_id')):
        cfg = settings[key]
        record(key + '_cache', lambda c=cfg, k=id_key: snapshot_download(c[k], revision=c['revision'],
            cache_dir=str(config_path(c['cache_dir'], settings)), local_files_only=True,
            allow_patterns=['*.json', '*.txt', 'model.safetensors']))
    def mfa():
        cfg = settings['mfa']
        response = subprocess.run([*cfg.get('command', [cfg['executable']]), 'version'], capture_output=True,
                                  text=True, timeout=45, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if response.returncode:
            raise RuntimeError(response.stderr[-500:])
        return response.stdout.strip()
    record('mfa_command', mfa)
    report = dict(checks=checks, ready=all(c['status'] == 'ok' for c in checks),
                  note='Cache presence does not establish pronunciation accuracy. Run an actual demo attempt as well.')
    (ROOT / 'runs').mkdir(exist_ok=True)
    (ROOT / 'runs/setup_check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
