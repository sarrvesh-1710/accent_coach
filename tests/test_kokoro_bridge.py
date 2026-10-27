import base64
import io
import json
import os
from pathlib import Path
import queue
import tempfile
import unittest
from unittest.mock import patch
import wave

from voice_generation.bridge import IsolatedKokoro, create_generator

ROOT=Path(__file__).resolve().parents[1]


def response():
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as audio:
        audio.setparams((1,2,24000,0,'NONE','not compressed'))
        audio.writeframes(b'\x01\x00'*240)
    return {'result':{'ok':True,'backend':'kokoro','type':'synthetic_example',
        'generated_audio_id':'synthetic-'+'a'*32,'timings_ms':{'model_load':0}},
        'audio_base64':base64.b64encode(buffer.getvalue()).decode()}


class FakeProcess:
    def __init__(self):self.stdin=io.BytesIO()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'runs').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)
        self.bridge=IsolatedKokoro(timeout_seconds=0)
        self.bridge.process=FakeProcess()
        self.bridge.responses=queue.Queue()
        self.start=self.enterContext(patch.object(self.bridge,'_start'))
        self.stop=self.enterContext(patch.object(self.bridge,'_stop'))

    def put(self,value):self.bridge.responses.put(json.dumps(value).encode())

    def test_private_output_and_reuse_without_importing_models(self):
        process=self.bridge.process
        for _ in range(2):
            self.put(response())
            result=self.bridge('I think so.',output_dir=self.output)
            self.assertTrue(result['ok'])
            self.assertEqual(result['backend'],'kokoro')
        self.assertIs(self.bridge.process,process)
        self.stop.assert_not_called()
        request=json.loads(process.stdin.getvalue().splitlines()[0])
        self.assertEqual(request['work_root'],str(self.output.resolve()))
        self.assertTrue((self.output/('synthetic-'+'a'*32+'.wav')).exists())

    def test_timeout_stops_process_and_returns_retryable_failure(self):
        result=self.bridge('Hi',output_dir=self.output)
        self.assertEqual(result['error']['code'],'TIMEOUT')
        self.assertTrue(result['error']['retryable'])
        self.stop.assert_called_once()
        self.assertEqual(list(self.output.iterdir()),[])

    def test_invalid_identity_or_wave_never_writes_files(self):
        for field,value in [('generated_audio_id','../../escape'),('type','learner_recording')]:
            payload=response();payload['result'][field]=value;self.put(payload)
            self.assertFalse(self.bridge('Hi',output_dir=self.output)['ok'])
        payload=response();payload['audio_base64']=base64.b64encode(b'not audio').decode();self.put(payload)
        self.assertFalse(self.bridge('Hi',output_dir=self.output)['ok'])
        self.assertEqual(list(self.output.iterdir()),[])

    def test_worker_failure_is_not_replaced_with_windows_voice(self):
        self.put({'result':{'ok':False,'error':{'code':'MODEL_UNAVAILABLE','user_message':'Unavailable','retryable':True}}})
        result=self.bridge('Hi',output_dir=self.output)
        self.assertEqual(result['error']['code'],'MODEL_UNAVAILABLE')
        self.assertNotIn('generated_audio_id',result)

    def test_shared_text_limits_and_accent_checked_before_start(self):
        for text in ('', 'x'*201, 'word '*13):
            self.assertEqual(self.bridge(text,output_dir=self.output)['error']['code'],'UNSUPPORTED_TEXT')
        self.assertEqual(self.bridge('Hi','en-GB',output_dir=self.output)['error']['code'],'UNSUPPORTED_ACCENT')
        self.start.assert_not_called()

    def test_default_factory_is_isolated_and_windows_is_explicit(self):
        with patch.dict(os.environ,{},clear=True):
            instance=create_generator()
            self.assertIsInstance(instance,IsolatedKokoro)
        with patch.dict(os.environ,{'ACCENT_COACH_GENERATION_BACKEND':'windows'}):
            self.assertEqual(create_generator().__module__,'voice_generation.generator')
        with patch.dict(os.environ,{'ACCENT_COACH_GENERATION_BACKEND':'unknown'}):
            with self.assertRaises(ValueError):create_generator()

    def test_missing_generation_environment_is_safe(self):
        bridge=IsolatedKokoro(python=self.output/'absent.exe')
        result=bridge('Hi',output_dir=self.output)
        self.assertFalse(result['ok'])
        self.assertNotIn(str(self.output),str(result))


if __name__=='__main__':unittest.main()
