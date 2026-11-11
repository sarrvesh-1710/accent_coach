"""Alignment-only timing study. Synthetic fixtures, not learner assessment.

Serial fixed cases, three rounds, then one deliberately contended real file-lock
case. No cache eviction, model downloads, parameter changes, or automatic retry.
"""
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import platform
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phoneme_scoring.align_audio import align_audio, load_settings
from phoneme_scoring.process_lock import alignment_lock
from lesson_catalog import load_lessons


def hold_lock(ready):
    with alignment_lock(Path.home() / ".accent_coach/mfa.lock"):
        ready.set()
        time.sleep(2)


def main():
    root = ROOT / "runs" / ("day2-phase5-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    root.mkdir(parents=True)
    settings = load_settings(ROOT / "phoneme_scoring/settings.json")
    prompts = {p["id"]: p for p in load_lessons(ROOT / "prompts.json")}
    report = dict(python=platform.python_version(), platform=platform.platform(),
        scope="align_audio only; synthetic fixtures; warm installed model files; serial calls in one Python process; each call launches a new MFA subprocess and fresh temporary directory",
        source_sha256={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ["phoneme_scoring/align_audio.py", "phoneme_scoring/process_lock.py", "tools/benchmark_mfa.py"]},
        settings_sha256=hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest(),
        retries=0, cases=[])
    print(str(root), flush=True)

    def case(lesson, repeat, condition):
        path = ROOT / "web_assets/examples" / (lesson + ".wav")
        start = time.monotonic()
        r = align_audio(path, prompts[lesson]["text"], settings, root / f"{lesson}-{repeat}-{condition}")
        row = dict(case=lesson, repeat=repeat, condition=condition, status=r["status"],
                   audio_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), duration_sec=r.get("duration_sec"),
                   timings_sec=r["timings_sec"], outer_elapsed_sec=time.monotonic()-start)
        report["cases"].append(row)
        (root / "measurements.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(row), flush=True)
        return r["status"] == "available"

    for repeat in range(1, 4):
        for lesson in ("think", "ship", "bad_bed"):
            if not case(lesson, repeat, "serial"):
                return 1
    context = mp.get_context("spawn")
    ready = context.Event()
    holder = context.Process(target=hold_lock, args=(ready,))
    holder.start()
    try:
        if not ready.wait(20):
            raise RuntimeError("Controlled lock holder did not become ready")
        if not case("think", 4, "controlled_2s_lock_holder"):
            return 1
    finally:
        holder.join(timeout=10)
        if holder.is_alive():
            holder.terminate()
            holder.join()
        holder.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
