"""Public information pages retain only the current authenticated identity."""
import tempfile
import unittest
from fastapi.testclient import TestClient
from site_server import create_site
class InformationHeaderTests(unittest.TestCase):
    def test_information_pages_keep_authenticated_menu_and_revoke_it_on_logout(self):
        with tempfile.TemporaryDirectory() as folder:
            with TestClient(create_site(data_root=folder,prompts=[],analyzer=lambda *a,**k:None),base_url='http://localhost') as client:
                for path in ['/help','/privacy','/terms']:
                    response=client.get(path)
                    self.assertEqual(response.status_code,200)
                    self.assertNotIn('class="account-menu"',response.text)
                client.get('/signup')
                response=client.post('/signup',data={'csrf':client.cookies['accent_login_csrf'],'username':'header_user','password':'header-test-password','display_name':'Header Learner'})
                self.assertEqual(response.status_code,200)
                import re
                for path in ['/help','/privacy','/terms']:
                    response=client.get(path)
                    self.assertIn('Signed in as Header Learner',response.text)
                    self.assertIn('action="/logout"',response.text)
                    self.assertIn('no-store',response.headers['cache-control'])
                csrf=re.search('name="csrf" value="([^"]+)"',response.text).group(1)
                client.post('/logout',data={'csrf':csrf})
                self.assertNotIn('Signed in as Header Learner',client.get('/privacy').text)
