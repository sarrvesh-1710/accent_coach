"""MFA alignment, audio preparation, and TextGrid parsing (no training).

audio: WAV path, or (mono/multichannel float array in [-1,1], sample_rate).
settings: dictionary or JSON path. Relative paths are relative to settings.json.
Never trim or time-stretch: alignment and inference use identical 16 kHz PCM.
Dependencies: numpy, scipy. MFA must be installed separately in the active env.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly


def load_settings(settings):
    if isinstance(settings, (str, Path)):
        path = Path(settings).expanduser().resolve()
        result = json.loads(path.read_text(encoding="utf-8"))
        result["_settings_dir"] = str(path.parent)
        return result
    return dict(settings)


def config_path(value, settings):
    path = Path(value).expanduser()
    return path if path.is_absolute() else Path(settings.get("_settings_dir", Path(__file__).parent)) / path


def prepare_audio(audio, settings):
    """Return reproducible float32 mono audio, PCM16 hash, and sample rate."""
    settings = load_settings(settings)
    sr = int(settings["sample_rate_hz"])
    if sr != 16000 or settings.get("device") != "cpu":
        raise ValueError("Only 16000 Hz / CPU is supported")
    dsp = settings["dsp"]
    if any(dsp.get(k, False) for k in ("trim", "denoise", "pitch_shift")):
        raise ValueError("Time-preserving pipeline requires trim/denoise/pitch_shift disabled")
    if dsp.get("mono") != "channel_mean" or dsp.get("resampling") != "scipy.signal.resample_poly":
        raise ValueError("Unsupported DSP mode")
    if isinstance(audio, (str, Path)):
        source_sr, x = wavfile.read(str(audio))
    else:
        x, source_sr = audio
    x = np.asarray(x)
    if x.ndim not in (1, 2) or x.size == 0 or int(source_sr) != source_sr or source_sr <= 0:
        raise ValueError("Invalid audio shape/sample rate")
    source_sr = int(source_sr)
    if np.issubdtype(x.dtype, np.signedinteger):
        x = x.astype(np.float64) / float(2 ** (x.dtype.itemsize * 8 - 1))
    elif x.dtype == np.uint8:
        x = (x.astype(np.float64) - 128) / 128
    elif np.issubdtype(x.dtype, np.floating):
        x = x.astype(np.float64)
    else:
        raise ValueError("Unsupported audio dtype")
    if not np.isfinite(x).all() or np.max(np.abs(x)) > 1.001:
        raise ValueError("Audio must be finite and normalized to [-1,1]")
    if x.ndim == 2:
        x = x.mean(axis=1)
    if len(x) / source_sr > float(settings["max_duration_sec"]) + 1e-8:
        raise ValueError("Audio exceeds max_duration_sec; choose a shorter complete utterance")
    if source_sr != sr:
        divisor = math.gcd(source_sr, sr)
        x = resample_poly(x, sr // divisor, source_sr // divisor)
    if len(x) / sr < settings["dsp"]["min_duration_sec"]:
        raise ValueError("Audio is too short")
    pcm = np.rint(np.clip(x, -1, 32767 / 32768) * 32768).astype("<i2")
    x = pcm.astype(np.float32) / 32768
    if float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) < settings["dsp"]["min_rms"]:
        raise ValueError("Insufficient audio energy")
    return x, sr, hashlib.sha256(pcm.tobytes()).hexdigest()


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_QUOTED = r'"(?:[^\"]|\"\")*"'


def _unquote(value):
    return value[1:-1].replace('""', '"')


def parse_textgrid(path):
    """Parse Praat long/short text TextGrids; return all interval tiers.

    No sorting, clipping, or silent interval repair. Reject malformed/duplicate
    tiers. Point tiers are skipped; binary TextGrids are unsupported.
    """
    raw = Path(path).read_bytes()
    text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    if "TextGrid" not in text:
        raise ValueError("Not a text TextGrid")
    tiers = {}
    if re.search(r"item\s*\[\d+\]\s*:", text):
        blocks = re.split(r"item\s*\[\d+\]\s*:", text)[1:]
        for block in blocks:
            cls = re.search(r'class\s*=\s*(' + _QUOTED + ')', block)
            name = re.search(r'name\s*=\s*(' + _QUOTED + ')', block)
            if not cls or not name:
                raise ValueError("Malformed tier")
            if _unquote(cls[1]) != "IntervalTier":
                continue
            key = _unquote(name[1])
            count = re.search(r"intervals:\s*size\s*=\s*(\d+)", block)
            matches = re.findall(r"intervals\s*\[\d+\]\s*:\s*xmin\s*=\s*(" + _NUMBER +
                                 r")\s*xmax\s*=\s*(" + _NUMBER + r")\s*text\s*=\s*(" + _QUOTED + ")", block)
            if not count or len(matches) != int(count[1]) or key in tiers:
                raise ValueError("Malformed interval count or duplicate tier")
            tiers[key] = [(float(a), float(b), _unquote(c)) for a, b, c in matches]
    else:
        # Short format: file header, object class, xmin, xmax, exists, tiers.
        tokens = re.findall(_QUOTED + r"|<exists>|" + _NUMBER, text)
        position = next((i for i, token in enumerate(tokens) if token == '"TextGrid"'), None)
        if position is None:
            raise ValueError("Missing TextGrid object class")
        it = iter(tokens[position + 1:])
        try:
            float(next(it)); float(next(it))
            if next(it) != "<exists>":
                raise ValueError("Missing tiers")
            for _ in range(int(next(it))):
                cls, key = _unquote(next(it)), _unquote(next(it))
                float(next(it)); float(next(it))
                count = int(next(it))
                entries = []
                for _ in range(count):
                    start = float(next(it))
                    end = float(next(it)) if cls == "IntervalTier" else start
                    entries.append((start, end, _unquote(next(it))))
                if cls == "IntervalTier":
                    if key in tiers:
                        raise ValueError("Duplicate tier")
                    tiers[key] = entries
            if list(it):
                raise ValueError("Unexpected TextGrid trailing tokens")
        except (StopIteration, TypeError) as exc:
            raise ValueError("Malformed short TextGrid") from exc
    if not tiers:
        raise ValueError("No interval tiers")
    return tiers


def phone_tier(tiers, names=("phones",)):
    matches = [v for k, v in tiers.items() if k.lower() in {n.lower() for n in names}]
    if len(matches) != 1:
        raise ValueError("Expected exactly one phone tier; configure phone_tiers")
    return matches[0]


def split_phone(label):
    # Keep original separately, remove only known ARPA stress/position suffixes.
    base = re.sub(r"_(B|E|I|S)$", "", label.strip())
    match = re.fullmatch(r"([A-Za-z]+)([012])", base)
    return (match[1].upper(), int(match[2])) if match else (base, None)


def validate_segments(segments, duration, tolerance=1e-6):
    previous, ids = 0.0, set()
    for seg in segments:
        start, end = float(seg["start_sec"]), float(seg["end_sec"])
        if not math.isfinite(start + end) or start < 0 or end > duration or end <= start:
            raise ValueError("Invalid/out-of-recording boundaries")
        if start < previous - tolerance or seg["segment_id"] in ids:
            raise ValueError("Overlapping/unordered segments or duplicate segment_id")
        previous = end
        ids.add(seg["segment_id"])
    if not segments:
        raise ValueError("No segments")


def align_audio(audio, transcript, settings, run_dir) -> dict:
    """Invoke pretrained MFA and return available segments or unavailable.

    Each attempt has a fresh directory (stale TextGrids cannot be reused).
    run_dir must be writable. Input WAV/LAB and MFA logs are retained for audit.
    """
    result = {"status": "unavailable", "segments": [], "reason": None}
    try:
        settings = load_settings(settings)
        x, sr, fingerprint = prepare_audio(audio, settings)
        if not isinstance(transcript, str) or not transcript.strip():
            raise ValueError("Transcript is empty")
        root = Path(run_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="mfa_", dir=root))
        corpus, output = work / "corpus", work / "aligned.TextGrid"
        corpus.mkdir()
        wavfile.write(corpus / "clip.wav", sr, np.rint(x * 32768).astype(np.int16))
        (corpus / "clip.lab").write_text(transcript.strip() + "\n", encoding="utf-8")
        cfg = settings["mfa"]
        # align_one avoids the corpus-level export/multiprocessing path, which
        # can hang on Windows after lattice alignment for a one-file corpus.
        args = [cfg["executable"], "align_one", str(corpus / "clip.wav"),
                str(corpus / "clip.lab"), cfg["dictionary"], cfg["acoustic_model"],
                str(output), "--output_format", "long_textgrid", "--no_use_mp",
                "--temporary_directory", str(work / "temp")]
        result.update(run_dir=str(work), audio_sha256=fingerprint, duration_sec=len(x) / sr,
                      sample_rate_hz=sr, transcript=transcript, command=args)
        with (work / "mfa.log").open("w", encoding="utf-8") as log:
            process = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=cfg["timeout_sec"], check=False)
        if process.returncode:
            raise RuntimeError(f"MFA exited {process.returncode}; inspect {work / 'mfa.log'}")
        if not output.is_file() or output.stat().st_size == 0:
            raise ValueError("MFA output missing or empty")
        entries = phone_tier(parse_textgrid(output), cfg["phone_tiers"])
        segments = []
        for index, (start, end, label) in enumerate(entries):
            canonical, stress = split_phone(label)
            segments.append(dict(segment_id=f"p{index:04d}", canonical_phone=canonical,
                                 original_phone=label, stress=stress, start_sec=start, end_sec=end))
        validate_segments(segments, len(x) / sr)
        if not any(s["canonical_phone"].lower() not in ("", "sil", "sp", "spn", "<eps>") for s in segments):
            raise ValueError("No usable speech phones in alignment")
        result.update(status="available", segments=segments, textgrid_path=str(output))
    except Exception as exc:
        result.update(status="unavailable", segments=[], reason=f"{type(exc).__name__}: {exc}")
    return result
