"""One bounded structured-output HTTP request; no SDK retries or model defaults."""
from dataclasses import dataclass,field
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .contract import explanations,output_schema

PROMPT=Path(__file__).with_name('prompts').joinpath('explain_v1.txt').read_text(encoding='utf-8')
PROMPT_DIGEST=hashlib.sha256(PROMPT.encode()).hexdigest()


class Unavailable(Exception):
    def __init__(self,code='unavailable'):self.code=code;super().__init__('Optional coaching unavailable')


@dataclass(frozen=True)
class Config:
    enabled: bool=False
    endpoint: str=''
    model: str=''
    api_key: str=field(default='',repr=False)
    timeout: float=5.0
    allow_external: bool=False

    @classmethod
    def from_env(cls):
        try:timeout=float(os.environ.get('ACCENT_COACH_AI_TIMEOUT_SEC','5'))
        except ValueError:timeout=0
        return cls(enabled=os.environ.get('ACCENT_COACH_AI_ENABLED')=='1',
                   endpoint=os.environ.get('ACCENT_COACH_AI_ENDPOINT',''),
                   model=os.environ.get('ACCENT_COACH_AI_MODEL',''),
                   api_key=os.environ.get('ACCENT_COACH_AI_API_KEY',''),timeout=timeout,
                   allow_external=os.environ.get('ACCENT_COACH_AI_ALLOW_EXTERNAL')=='1')

    @property
    def external(self):return urlsplit(self.endpoint).hostname not in {'localhost','127.0.0.1','::1'}

    @property
    def available(self):
        try:
            url=urlsplit(self.endpoint)
            return bool(self.enabled and self.model.strip() and len(self.model)<=128 and url.hostname and
                        url.path.endswith('/chat/completions') and not (url.username or url.password or url.query or url.fragment) and
                        (url.scheme=='https' or not self.external and url.scheme=='http') and
                        (not self.external or self.allow_external and self.api_key) and 0.1<=self.timeout<=5)
        except ValueError:return False

    @property
    def fingerprint(self):return hashlib.sha256(json.dumps([self.endpoint,self.model]).encode()).hexdigest()

    def public(self):
        from .contract import CONSENT_VERSION
        try:label=urlsplit(self.endpoint).hostname if self.available else None
        except ValueError:label=None
        return dict(available=self.available,external=self.external if self.available else False,
                    provider_label=label,consent_version=CONSENT_VERSION,provider_version=self.fingerprint,
                    language='en',timeout_ms=int(min(max(self.timeout,0),5)*1000) if self.timeout==self.timeout else 5000)


class Provider:
    def __init__(self,config,transport=None):
        self.config=config
        self.transport=transport
        self.client=None

    async def generate(self,evidence):
        if not self.config.available:raise Unavailable('disabled')
        if self.client is None:
            self.client=httpx.AsyncClient(timeout=self.config.timeout,follow_redirects=False,trust_env=False,
                transport=self.transport,limits=httpx.Limits(max_connections=2,max_keepalive_connections=2))
        # Escaping angle brackets prevents evidence strings from closing the delimiters.
        data=json.dumps(evidence.model_dump(mode='json'),ensure_ascii=True,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e')
        choices=json.dumps(explanations(evidence),ensure_ascii=True)
        payload=dict(model=self.config.model,store=False,max_completion_tokens=192,
            messages=[dict(role='system',content=PROMPT),dict(role='user',content='<EVIDENCE_JSON>\n'+data+'\n</EVIDENCE_JSON>\n<APPROVED_EXPLANATIONS>\n'+choices+'\n</APPROVED_EXPLANATIONS>')],
            response_format=dict(type='json_schema',json_schema=dict(name='accent_coach_explanation',strict=True,schema=output_schema(evidence))))
        headers={'Authorization':'Bearer '+self.config.api_key} if self.config.api_key else {}
        try:
            async with self.client.stream('POST',self.config.endpoint,json=payload,headers=headers) as response:
                if response.status_code==429:raise Unavailable('rate_limited')
                if response.status_code!=200:raise Unavailable()
                raw=bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw)>16384:raise Unavailable('invalid_output')
            value=json.loads(raw);choice=value['choices'][0];message=choice['message']
            if choice.get('finish_reason')!='stop' or message.get('refusal') or not isinstance(message.get('content'),str):
                raise Unavailable('invalid_output')
            return json.loads(message['content'])
        except (httpx.TimeoutException,TimeoutError):raise Unavailable('timeout') from None
        except Unavailable:raise
        except Exception:raise Unavailable() from None

    async def close(self):
        if self.client:await self.client.aclose()
