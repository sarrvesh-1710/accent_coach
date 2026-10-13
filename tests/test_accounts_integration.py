"""Real HTTP account/storage flow with a deterministic speech-worker substitute.

These tests verify application wiring, not neural-model pronunciation accuracy.
"""
import io
import json
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
import wave

from fastapi.testclient import TestClient
from site_server import create_site

PROMPTS = [{'id': 'think', 'text': 'I think so', 'practice_tip': 'Practice TH.'}]


def audio():
    out = io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(b'\x01\x00' * 1600)
    return out.getvalue()


def analyzer(path, prompt, **kwargs):
    assert Path(path).read_bytes() == audio()
    assert kwargs['compare_reference'] is False
    assert Path(kwargs['output_root']).parent == Path(path).parent  # job-private output
    kwargs['progress_callback']('Checking words')
    return {'overall_status': 'partial', 'spoken_words_verification': {'transcript': 'I think so'},
            'target_assessment': {'targets': [{'word': 'think', 'expected_phone': 'TH', 'status': 'alternative_favored'}]},
            'results_path': '/secret/results.json', 'settings': {'command': '/private/tool'},
            'stage_statuses': {'alignment': {'status': 'ok'}}}


class AccountIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = create_site(data_root=self.tmp.name, analyzer=analyzer, prompts=PROMPTS)
        self.client = TestClient(self.site, base_url='http://localhost')
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.tmp.cleanup()

    def signup(self, client, name):
        client.get('/signup')
        response = client.post('/signup', data={'csrf': client.cookies['accent_login_csrf'], 'username': name,
                            'password': 'test-password-123', 'display_name': name.title()})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('Practice English pronunciation.', response.text)
        csrf = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text).group(1)
        return {'X-CSRF-Token': csrf}

    def attempt(self, client, headers):
        response = client.post('/api/attempts?prompt_id=think', content=audio(), headers={**headers, 'Content-Type': 'audio/wav'})
        self.assertEqual(response.status_code, 202, response.text)
        identity = response.json()['attempt_id']
        for _ in range(100):
            result = client.get('/api/attempts/' + identity).json()
            if result['status'] not in {'queued', 'processing'}:
                return identity, result
            time.sleep(.01)
        self.fail('Analysis did not finish')

    def test_signup_profile_analysis_history_playback_logout_login(self):
        h = self.signup(self.client, 'alice')
        self.assertIn('My profile', self.client.get('/profile').text)
        self.assertEqual(self.client.post('/api/profile', json={'display_name': 'Alice Updated', 'goals': ['TH']}, headers=h).status_code, 200)
        identity, result = self.attempt(self.client, h)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['result']['spoken_words_verification']['transcript'], 'I think so')
        self.assertEqual(self.client.get(f'/api/attempts/{identity}/audio').content, audio())
        self.assertEqual(self.client.get('/api/suggestions').json(), {'phones': ['TH']})
        download = self.client.get(f'/api/attempts/{identity}/result')
        self.assertNotIn('secret', download.text)
        self.assertNotIn('settings', download.json())
        self.assertEqual(len(self.client.get('/api/attempts').json()['attempts']), 1)
        token = self.client.cookies['accent_session']
        self.client.post('/logout', data={'csrf': h['X-CSRF-Token']})
        self.assertEqual(self.client.get(f'/api/attempts/{identity}/audio').status_code, 401)
        self.assertIsNone(self.site.state.store.session(token))
        self.client.get('/login')
        self.client.post('/login', data={'csrf': self.client.cookies['accent_login_csrf'], 'username': 'ALICE', 'password': 'test-password-123'})
        self.assertEqual(self.client.get('/api/me').json()['display_name'], 'Alice Updated')
        self.assertEqual(self.client.get(f'/api/attempts/{identity}/audio').content, audio())
        with self.site.state.store.connect() as db:
            hashed = db.execute('SELECT password FROM users').fetchone()[0]
            self.assertTrue(hashed.startswith('$argon2id$'))

    def test_second_user_cannot_read_play_download_or_delete_first_users_attempt(self):
        ah = self.signup(self.client, 'alice')
        identity, _ = self.attempt(self.client, ah)
        bob = TestClient(self.site, base_url='http://localhost')
        bh = self.signup(bob, 'bob')
        self.assertEqual(bob.get('/api/attempts').json()['attempts'], [])
        for suffix in ('', '/audio', '/result'):
            self.assertEqual(bob.get('/api/attempts/' + identity + suffix).status_code, 404)
        self.assertEqual(bob.delete('/api/attempts/' + identity, headers=bh).status_code, 404)
        self.assertEqual(self.client.get('/api/attempts/' + identity).status_code, 200)
        for path in ('/gradio_api/file=/tmp/anything', '/file=/tmp/anything', '/private_data/accounts.sqlite3', '/runs/example/learner.wav'):
            self.assertEqual(bob.get(path).status_code, 404)

    def test_restart_keeps_profile_audio_and_results(self):
        h = self.signup(self.client, 'alice')
        identity, _ = self.attempt(self.client, h)
        app2 = create_site(data_root=self.tmp.name, analyzer=analyzer, prompts=PROMPTS)
        with TestClient(app2, base_url='http://localhost') as client2:
            client2.cookies.update(self.client.cookies)
            self.assertEqual(client2.get('/api/me').json()['username'], 'alice')
            self.assertEqual(client2.get(f'/api/attempts/{identity}/audio').content, audio())
            self.assertEqual(client2.get(f'/api/attempts/{identity}/result').status_code, 200)

    def test_csrf_credentials_and_invalid_audio_rejected(self):
        self.client.get('/signup')
        self.assertEqual(self.client.post('/signup', data={'username': 'alice', 'password': 'test-password-123', 'display_name': 'Alice'}).status_code, 403)
        h = self.signup(self.client, 'alice')
        self.assertEqual(self.client.post('/api/profile', json={'display_name': 'Other', 'goals': []}).status_code, 403)
        self.assertEqual(self.client.post('/api/profile', headers={**h, 'Origin':'https://attacker.example'}, json={'display_name':'Other','goals':[]}).status_code, 403)
        self.assertEqual(self.client.post('/api/attempts?prompt_id=think', headers={**h,'Content-Type':'audio/wav'}, content=b'bad').status_code, 422)
        self.assertEqual(self.client.post('/api/attempts?prompt_id=unknown', headers={**h,'Content-Type':'audio/wav'}, content=audio()).status_code, 422)
        self.assertEqual(self.client.get('/api/attempts').json()['attempts'], [])
        self.client.get('/login')
        response = self.client.post('/login', data={'csrf': self.client.cookies['accent_login_csrf'], 'username':'alice','password':'wrong-password'})
        self.assertEqual(response.status_code, 401)

    def test_delete_during_processing_rejects_late_result(self):
        started, resume = threading.Event(), threading.Event()
        def slow(*args, **kwargs):
            started.set(); resume.wait(timeout=5)
            return analyzer(*args, **kwargs)
        self.site.state.jobs.analyzer = slow
        h = self.signup(self.client, 'alice')
        response = self.client.post('/api/attempts?prompt_id=think', content=audio(), headers={**h,'Content-Type':'audio/wav'})
        identity = response.json()['attempt_id']
        self.assertTrue(started.wait(timeout=5))
        try:
            self.assertEqual(self.client.delete('/api/attempts/' + identity, headers=h).status_code, 200)
            self.assertEqual(self.client.get(f'/api/attempts/{identity}/audio').status_code, 404)
        finally:
            resume.set()
        self.site.state.jobs.pool.submit(lambda: None).result(timeout=5)
        self.assertEqual(self.client.get('/api/attempts/' + identity).status_code, 404)
        with self.site.state.store.connect() as db:
            row = db.execute('SELECT audio,result,deleted FROM attempts WHERE id=?', (identity,)).fetchone()
            self.assertEqual(tuple(row), (None, None, 1))
        self.assertEqual(list((Path(self.tmp.name) / 'work').iterdir()), [])

    def test_analysis_failure_keeps_recording_and_stores_status(self):
        def fail(*args, **kwargs):
            raise TimeoutError('test timeout')
        self.site.state.jobs.analyzer = fail
        h = self.signup(self.client, 'alice')
        identity, result = self.attempt(self.client, h)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(self.client.get(f'/api/attempts/{identity}/audio').content, audio())
        self.assertEqual(self.client.get(f'/api/attempts/{identity}/result').status_code, 409)


if __name__ == '__main__':
    unittest.main()
