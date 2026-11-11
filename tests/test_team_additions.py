"""Real HTTP/SQLite integration with controlled speech; no neural accuracy claims."""
from contextlib import closing
import re
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from site_server import create_site
from accounts.store import Store
from practice_guides import practice_guides, profile_guide


class TeamAdditionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.site = create_site(data_root=self.tmp.name)
        self.client = self.enterContext(TestClient(self.site, base_url='http://localhost'))

    def signup(self, client, name):
        client.get('/signup')
        response = client.post('/signup', data=dict(csrf=client.cookies['accent_login_csrf'],
            username=name, password='test-password-123', display_name=name))
        self.assertEqual(response.status_code, 200)
        return {'X-CSRF-Token': re.search('name="csrf-token" content="([^"]+)"', response.text).group(1)}

    def test_guides_are_private_draft_data_and_do_not_start_speech_or_generation(self):
        self.assertEqual(self.client.get('/api/practice-guides').status_code, 401)
        self.signup(self.client, 'alice')
        with patch.object(self.site.state.practice_jobs.speech, 'run', side_effect=AssertionError('Unexpected model pass')):
            guides = self.client.get('/api/practice-guides').json()
            self.assertEqual(len(guides['sentences']), 3)
            self.assertEqual(guides['profile']['id'], 'general')
            self.assertEqual(guides['generation']['backend'], 'windows')
            self.assertIn('Draft', guides['variation_note'].replace('draft', 'Draft'))
            self.assertIn('guide-sentence', self.client.get('/practice').text)
        altered = practice_guides(); altered['sentences'].clear()
        self.assertEqual(len(practice_guides()['sentences']), 3)

    def test_mandarin_profile_persists_is_private_and_does_not_change_target(self):
        headers = self.signup(self.client, 'alice')
        response = self.client.post('/api/profile', json=dict(display_name='Alice', goals=['TH'], learner_profile='chinese', user_id='other'), headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/me').json()['learner_profile'], 'chinese')
        guide = self.client.get('/api/practice-guides').json()['profile']
        self.assertEqual(guide['target_accent'], 'en-US-general-american')
        self.assertEqual(guide['calibration_status'], 'not_enabled_in_app')
        self.assertIn('guidance only', guide['limitation'])
        self.assertIn('Mandarin-speaking learner', self.client.get('/profile').text)
        with TestClient(create_site(data_root=self.tmp.name), base_url='http://localhost') as reopened:
            reopened.cookies.update(self.client.cookies)
            self.assertEqual(reopened.get('/api/me').json()['learner_profile'], 'chinese')
        with TestClient(self.site, base_url='http://localhost') as bob:
            self.signup(bob, 'bob')
            self.assertEqual(bob.get('/api/me').json()['learner_profile'], 'general')
            self.assertEqual(bob.get('/api/practice-guides').json()['profile']['id'], 'general')
        # Older clients that omit the optional field must preserve the saved preference.
        self.client.post('/api/profile', json=dict(display_name='Alice', goals=[]), headers=headers)
        self.assertEqual(self.client.get('/api/me').json()['learner_profile'], 'chinese')

    def test_bad_profile_is_rejected_atomically(self):
        headers = self.signup(self.client, 'alice')
        for bad in ('../../private', [], {'id': 'chinese'}, 'en-US-general-american'):
            response = self.client.post('/api/profile', json=dict(display_name='Changed', goals=['TH'], learner_profile=bad), headers=headers)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.get('/api/me').json()['display_name'], 'alice')
        with self.assertRaises(ValueError): profile_guide('../../private')

    def test_additive_preferences_table_opens_existing_database_without_data_loss(self):
        root = Path(self.tmp.name) / 'legacy'; root.mkdir()
        with closing(sqlite3.connect(root / 'accounts.sqlite3')) as db:
            db.execute("CREATE TABLE users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,display_name TEXT NOT NULL,goals TEXT NOT NULL DEFAULT '[]')")
            db.execute('INSERT INTO users VALUES (?,?,?,?,?)', ('old', 'olduser', 'existing-hash', 'Original', '[]'))
            db.commit()
        Store(root)
        with closing(sqlite3.connect(root / 'accounts.sqlite3')) as db:
            self.assertEqual(db.execute('SELECT * FROM users').fetchone(), ('old', 'olduser', 'existing-hash', 'Original', '[]'))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM practice_preferences').fetchone()[0], 0)


if __name__ == '__main__': unittest.main()
