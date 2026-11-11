"""Optional independent request path; never uses the speech worker or job pool."""
import asyncio
import time

from .contract import CONSENT_VERSION,PROMPT_VERSION,TIPS,validate_output
from .evidence import build_evidence,digest
from .provider import Config,Provider,PROMPT_DIGEST,Unavailable
from .repository import Repository,StaleEvidence


class CoachingService:
    def __init__(self,store,catalog,config=None,provider=None):
        self.repository=Repository(store);self.catalog=catalog
        self.config=config or Config.from_env();self.provider=provider or Provider(self.config)
        self.active=set();self.lock=asyncio.Lock()

    def cache_key(self,snapshot,evidence):
        return digest([snapshot['owner'],snapshot['attempt_id'],snapshot['base_version'],
            evidence.model_dump(mode='json'),PROMPT_VERSION,PROMPT_DIGEST,self.config.fingerprint,evidence.language,
            TIPS,{k:self.catalog[k] for k in evidence.approved_next_exercise_ids},snapshot['plan']])

    def response(self,output,evidence,version,*,cached,started):
        tip=output.practice_tip_id;exercise=output.next_exercise_id
        return dict(status='completed',cached=cached,base_version=version,
            evidence_version=digest(evidence.model_dump(mode='json')),prompt_version=PROMPT_VERSION,
            focus=dict(word=evidence.target_word,sound=evidence.target_sound,word_index=evidence.target_word_index),
            coaching=dict(explanation=output.explanation,
                          practice_tip=dict(id=tip,text=TIPS[tip][1]) if tip else None,
                          next_exercise=dict(id=exercise,sentence=self.catalog[exercise]['text']) if exercise else None),
            timings=dict(coaching_ms=round((time.monotonic()-started)*1000,3)))

    async def explain(self,token,identity,expected_version,*,language='en',external_consent=False,consent_version=None,provider_version=None):
        started=time.monotonic();key=None
        try:
            # The deadline includes storage, validation and the provider, not just socket reads.
            async with asyncio.timeout(min(max(self.config.timeout,0.1),5)):
                snapshot=await asyncio.to_thread(self.repository.snapshot,token,identity)
                if snapshot['base_version']!=expected_version:raise StaleEvidence()
                evidence=build_evidence(snapshot['data'],self.catalog,snapshot['plan'],language)
                key=self.cache_key(snapshot,evidence)
                cached=await asyncio.to_thread(self.repository.cached,token,identity,key,expected_version,digest(snapshot['plan']))
                if cached is not None:
                    validated=validate_output(cached,evidence)
                    return self.response(validated,evidence,expected_version,cached=True,started=started)
                if not self.config.available:raise Unavailable('disabled')
                if self.config.external and not (external_consent is True and consent_version==CONSENT_VERSION and provider_version==self.config.fingerprint):
                    raise Unavailable('consent_required')
                async with self.lock:
                    if key in self.active:raise Unavailable('busy')
                    if len(self.active)>=2:raise Unavailable('busy')
                    # Recheck after serialization: two near-simultaneous cache misses
                    # must not turn into two generations after a very fast first call.
                    cached=await asyncio.to_thread(self.repository.cached,token,identity,key,expected_version,digest(snapshot['plan']))
                    if cached is not None:
                        return self.response(validate_output(cached,evidence),evidence,expected_version,cached=True,started=started)
                    self.active.add(key)
                try:
                    raw=await self.provider.generate(evidence)
                    validated=validate_output(raw,evidence)
                    await asyncio.to_thread(self.repository.publish,token,snapshot,key,validated.model_dump(),digest(snapshot['plan']))
                    return self.response(validated,evidence,expected_version,cached=False,started=started)
                finally:
                    async with self.lock:self.active.discard(key)
        except PermissionError:raise
        except StaleEvidence:return dict(status='stale',code='stale')
        except (TimeoutError,asyncio.TimeoutError):return dict(status='unavailable',code='timeout')
        except Unavailable as exc:return dict(status='disabled' if exc.code=='disabled' else 'unavailable',code=exc.code)
        except Exception:return dict(status='unavailable',code='unavailable')

    async def close(self):await self.provider.close()
