"""Optional external-runtime tests; controlled transport/backend, no Kokoro weights."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from voice_generation.runtime import ExternalKokoro, configured_generator, generation_capabilities
from voice_generation.generator import generate_audio, TARGET_ACCENT
from voice_generation.external_worker import serve


class GenerationRuntimeTests(unittest.TestCase):
    def test_default_is_exact_existing_callable_and_no_neural_import_or_process(self):
        with patch.dict(os.environ, {}, clear=True), patch('subprocess.Popen', side_effect=AssertionError('Eager process')):
            self.assertIs(configured_generator(), generate_audio)
            self.assertEqual(generation_capabilities()['backend'], 'windows')
            self.assertNotIn('kokoro', sys.modules)

    def test_missing_optional_runtime_is_actionable_and_not_silent_fallback(self):
        with patch.dict(os.environ, {'ACCENT_COACH_EXAMPLE_BACKEND': 'kokoro', 'ACCENT_COACH_KOKORO_PYTHON': ''}):
            self.assertFalse(generation_capabilities()['assets_present'])
            generator = configured_generator()
            with tempfile.TemporaryDirectory() as folder:
                result = generator('I think so', output_dir=folder)
                self.assertFalse(result['ok']); self.assertEqual(result['error']['code'], 'MODEL_UNAVAILABLE')
                self.assertEqual(list(Path(folder).iterdir()), [])
            generator.close()

    def test_worker_reuses_backend_and_rejects_invalid_inputs_before_loading(self):
        calls=[]
        class Fake:
            def __init__(self): calls.append('load')
            def generate_audio(self, *args, **kwargs): calls.append(args[0]); return {'ok': True}
        requests = [dict(text='word '*13, target_accent=TARGET_ACCENT, output_dir='ignored'),
                    dict(text='I think so', target_accent='en-GB', output_dir='ignored')]
        sink=io.StringIO(); serve(io.StringIO('\n'.join(map(json.dumps, requests))+'\n'), sink, Fake)
        self.assertEqual(calls, [])
        requests=[dict(text='I think so', target_accent=TARGET_ACCENT, output_dir='ignored')]*2
        sink=io.StringIO(); serve(io.StringIO('\n'.join(map(json.dumps, requests))+'\n'), sink, Fake)
        self.assertEqual(calls, ['load', 'I think so', 'I think so'])
        self.assertEqual(len(sink.getvalue().splitlines()), 2)

    def test_transport_reuses_owned_process_validates_output_and_cleans_up(self):
        script = """import sys,json,pathlib,uuid,wave
for line in sys.stdin:
 r=json.loads(line); asset='synthetic-'+uuid.uuid4().hex
 with wave.open(str(pathlib.Path(r['output_dir'])/(asset+'.wav')),'wb') as wav:
  wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(b'\\x01\\x00'*24)
 print(json.dumps(dict(ok=True,generated_audio_id=asset,type='synthetic_example')),flush=True)
"""
        generator=ExternalKokoro(sys.executable, command=[sys.executable, '-u', '-c', script])
        self.addCleanup(generator.close)
        with tempfile.TemporaryDirectory() as folder:
            first=generator('I think so', output_dir=folder); pid=generator.process.pid
            second=generator('The ship is here', output_dir=folder)
            self.assertTrue(first['ok']); self.assertTrue(second['ok'])
            self.assertNotEqual(first['generated_audio_id'], second['generated_audio_id'])
            self.assertEqual(generator.process.pid, pid)
        child=generator.process; generator.close(); self.assertIsNotNone(child.poll())

    def test_invalid_text_does_not_spawn_and_timeout_releases_process(self):
        generator=ExternalKokoro(sys.executable, timeout=.1,
                                command=[sys.executable, '-u', '-c', 'import time;time.sleep(30)'])
        self.addCleanup(generator.close)
        with tempfile.TemporaryDirectory() as folder:
            for text in ('', 'word '*13, 'x'*201):
                self.assertEqual(generator(text, output_dir=folder)['error']['code'], 'UNSUPPORTED_TEXT')
                self.assertIsNone(generator.process)
            result=generator('I think so', output_dir=folder)
            self.assertEqual(result['error']['code'], 'TIMEOUT'); self.assertIsNone(generator.process)

    def test_malformed_response_is_failed_and_new_partial_outputs_removed(self):
        script = "import sys,json,pathlib; r=json.loads(sys.stdin.readline()); (pathlib.Path(r['output_dir'])/'synthetic-partial.wav').write_bytes(b'x');print('invalid',flush=True)"
        generator=ExternalKokoro(sys.executable, command=[sys.executable,'-u','-c',script]); self.addCleanup(generator.close)
        with tempfile.TemporaryDirectory() as folder:
            old=Path(folder)/'synthetic-existing.wav';old.write_bytes(b'keep')
            result=generator('I think so',output_dir=folder)
            self.assertEqual(result['error']['code'],'MODEL_UNAVAILABLE')
            self.assertEqual(list(Path(folder).iterdir()),[old])

    def test_success_envelope_cannot_publish_malformed_waveform(self):
        script="import sys,json,pathlib; r=json.loads(sys.stdin.readline()); a='synthetic-'+'a'*32; (pathlib.Path(r['output_dir'])/(a+'.wav')).write_bytes(b'bad audio'); print(json.dumps(dict(ok=True,generated_audio_id=a,type='synthetic_example')),flush=True)"
        generator=ExternalKokoro(sys.executable,command=[sys.executable,'-u','-c',script]); self.addCleanup(generator.close)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(generator('I think so',output_dir=folder)['error']['code'],'MODEL_UNAVAILABLE')
            self.assertEqual(list(Path(folder).iterdir()),[])


if __name__ == '__main__': unittest.main()
