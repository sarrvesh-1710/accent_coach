from pathlib import Path
import re
import tempfile
import unittest

from fastapi.testclient import TestClient
from site_server import create_site

ROOT=Path(__file__).resolve().parents[1]


class ProfilePreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app=create_site(data_root=self.temp.name,analyzer=lambda *args,**kwargs:None,prompts=[])
        self.client=self.enterContext(TestClient(self.app,base_url='http://localhost'))
        self.headers=self.signup(self.client,'profile_alice')

    def signup(self,client,name):
        client.get('/signup')
        response=client.post('/signup',data={'csrf':client.cookies['accent_login_csrf'],
            'username':name,'password':'profile-test-password-123','display_name':'Alice'})
        self.assertEqual(response.status_code,200)
        return {'X-CSRF-Token':re.search('name="csrf-token" content="([^"]+)"',response.text).group(1)}

    def test_save_returns_canonical_profile_and_survives_new_client(self):
        response=self.client.post('/api/profile',json={'display_name':'  Alice New  ','goals':['TH','TH','AE']},headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['profile'],{'username':'profile_alice','display_name':'Alice New','goals':['TH','AE']})
        with TestClient(self.app,base_url='http://localhost') as other:
            other.cookies.update(self.client.cookies)
            self.assertEqual(other.get('/api/me').json(),response.json()['profile'])

    def test_general_practice_is_saved_with_no_selected_sounds(self):
        response=self.client.post('/api/profile',json={'display_name':'Alice','goals':[]},headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['profile']['goals'],[])

    def test_invalid_profile_preserves_saved_values(self):
        before=self.client.get('/api/me').json()
        for payload in ({'display_name':'   ','goals':['TH']},{'display_name':'x'*61,'goals':[]},{'display_name':'Changed','goals':['INVALID']}):
            response=self.client.post('/api/profile',json=payload,headers=self.headers)
            self.assertEqual(response.status_code,422)
            self.assertEqual(self.client.get('/api/me').json(),before)

    def test_updates_use_signed_in_owner_and_require_csrf(self):
        before=self.client.get('/api/me').json()
        response=self.client.post('/api/profile',json={'display_name':'Blocked','goals':[]})
        self.assertEqual(response.status_code,403)
        bob=TestClient(self.app,base_url='http://localhost')
        self.addCleanup(bob.close)
        headers=self.signup(bob,'profile_bob')
        response=bob.post('/api/profile',json={'display_name':'Bob','goals':['IH'],'user_id':'profile_alice'},headers=headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(bob.get('/api/me').json()['display_name'],'Bob')
        self.assertEqual(self.client.get('/api/me').json(),before)

    def test_profile_page_escapes_name_and_exposes_accessible_form(self):
        self.client.post('/api/profile',json={'display_name':'<script>alert(1)</script>','goals':['IH']},headers=self.headers)
        response=self.client.get('/profile')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',response.text)
        self.assertNotIn('<script>alert(1)</script>',response.text)
        self.assertIn('Sounds I want to practice',response.text)
        self.assertIn('Discard changes',response.text)
        self.assertIn('/site-assets/profile.js',response.text)
        self.assertIn('aria-live="polite"',response.text)


if __name__=='__main__':unittest.main()
