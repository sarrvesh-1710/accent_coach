"""Bounded SQLite/service wiring benchmark with a 20ms FAKE provider.

Never invokes speech models, reads real accounts, or calls an AI service.
Browser timings and actual model latency must be reported separately.
"""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from accounts.store import Store
from ai_coaching.contract import explanations
from ai_coaching.evidence import base_version
from ai_coaching.provider import Config
from ai_coaching.service import CoachingService


class FixtureProvider:
    def __init__(self):self.calls=0
    async def generate(self,evidence):
        self.calls+=1;await asyncio.sleep(.02)
        return dict(explanation=explanations(evidence)[0],practice_tip_id=None,next_exercise_id=None)
    async def close(self):pass


async def main():
    catalog={p['id']:p for p in json.loads((ROOT/'prompts.json').read_text(encoding='utf-8'))}
    fixture=json.loads((ROOT/'contracts/evaluations/coaching_v1.json').read_text(encoding='utf-8'))['projection_cases'][0]['data']
    report=dict(scope='Private temporary SQLite, 20ms fake provider. Not live AI, speech inference, or audio playback.',runs=[])
    with tempfile.TemporaryDirectory(prefix='accent_coach_explanation_benchmark_') as root:
        store=Store(root);owner=store.register('fixtureuser','fixture-password-123','Fixture');token=store.new_session(owner)
        provider=FixtureProvider();started=time.monotonic()
        service=CoachingService(store,catalog,Config(enabled=True,endpoint='http://127.0.0.1:9999/v1/chat/completions',model='fake-only'),provider)
        report['service_preparation_ms']=(time.monotonic()-started)*1000
        for case in range(1,6):
            identity=store.create_attempt(owner,catalog['think'],b'fixture-not-a-real-recording')
            store.finish(owner,identity,fixture['result']);saved=store.get_attempt(owner,identity)
            version=base_version(saved)
            for mode in ['uncached_fake','owned_cache']:
                started=time.monotonic();value=await service.explain(token,identity,version)
                report['runs'].append(dict(case=case,mode=mode,elapsed_ms=(time.monotonic()-started)*1000,
                    status=value['status'],cached=value.get('cached'),service_timings=value.get('timings')))
        report['provider_calls']=provider.calls;await service.close()
    destination=ROOT/'output/ai-coaching-service-benchmark.json';destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':asyncio.run(main())
