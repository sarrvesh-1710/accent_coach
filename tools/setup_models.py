"""Explicit one-time public model download. Never sends learner audio."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phoneme_scoring.align_audio import load_settings, config_path

if __name__ == '__main__':
    from huggingface_hub import snapshot_download
    settings = load_settings(ROOT / 'phoneme_scoring/settings.json')
    for key, id_key in (('model', 'id'), ('content_check', 'model_id')):
        cfg = settings[key]
        print(snapshot_download(cfg[id_key], revision=cfg['revision'],
            cache_dir=str(config_path(cfg['cache_dir'], settings)),
            allow_patterns=['*.json', '*.txt', 'model.safetensors', 'pytorch_model.bin']))
