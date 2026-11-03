import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from server_config import load_server_config
from site_server import create_site


class HostedConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.env=dict(ACCENT_COACH_MODE='hosted',ACCENT_COACH_ALLOWED_HOSTS='coach.example.com',
            ACCENT_COACH_PUBLIC_URL='https://coach.example.com',ACCENT_COACH_DATA_DIR=self.temp.name,
            FORWARDED_ALLOW_IPS='127.0.0.1')
    def test_local_defaults_and_platform_port(self):
        config=load_server_config({})
        self.assertFalse(config.hosted);self.assertEqual(config.bind_host,'127.0.0.1')
        self.assertIn('localhost',config.allowed_hosts)
        self.assertEqual(load_server_config({'PORT':'8080'}).port,8080)
        self.assertEqual(load_server_config({'PORT':'8080','GRADIO_SERVER_PORT':'8764'}).port,8764)
        self.assertEqual(load_server_config({**self.env,'PORT':'8080','GRADIO_SERVER_PORT':'8764'}).port,8080)
    def test_hosted_configuration_is_explicit(self):
        config=load_server_config(self.env)
        self.assertTrue(config.hosted);self.assertEqual(config.data_dir,Path(self.temp.name).resolve())
        for key in ('ACCENT_COACH_ALLOWED_HOSTS','ACCENT_COACH_PUBLIC_URL','ACCENT_COACH_DATA_DIR'):
            invalid=dict(self.env);invalid.pop(key)
            with self.assertRaises(ValueError):load_server_config(invalid)
        for key,value in [('ACCENT_COACH_DATA_DIR','relative-folder'),('ACCENT_COACH_PUBLIC_URL','http://coach.example.com'),
                          ('ACCENT_COACH_PUBLIC_URL','https://other.example.com'),('ACCENT_COACH_ALLOWED_HOSTS','*'),
                          ('FORWARDED_ALLOW_IPS','*'),('FORWARDED_ALLOW_IPS','0.0.0.0/0'),('ACCENT_COACH_DEMO','1')]:
            with self.assertRaises(ValueError):load_server_config({**self.env,key:value})
    def app(self):
        with patch.dict(os.environ,self.env,clear=True):
            return create_site(prompts=[],analyzer=lambda *a,**k:None)
    def test_https_domain_login_profile_and_secure_cookies_persist(self):
        app=self.app()
        with TestClient(app,base_url='https://coach.example.com') as client:
            signup=client.get('/signup')
            self.assertIn('Secure',signup.headers['set-cookie'])
            response=client.post('/signup',data=dict(csrf=client.cookies['accent_login_csrf'],username='hosted_user',
                password='hosted-test-password-403',display_name='Hosted learner',language='hindi',use_starters='1'))
            self.assertEqual(response.status_code,200)
            self.assertTrue(any('Secure' in cookie and 'HttpOnly' in cookie for r in response.history for cookie in r.headers.get_list('set-cookie') if cookie.startswith('accent_session=')))
            csrf=re.search('name="csrf-token" content="([^"]+)"',response.text).group(1)
            saved=client.post('/api/profile',headers={'X-CSRF-Token':csrf,'Origin':'https://coach.example.com'},json=dict(display_name='Moved learner',goals=['TH'],background=dict(language='spanish',use_starters=True)))
            self.assertEqual(saved.status_code,200)
            blocked=client.post('/api/profile',headers={'X-CSRF-Token':csrf,'Origin':'https://other.example.com'},json=dict(display_name='Bad',goals=[]))
            self.assertEqual(blocked.status_code,403)
            self.assertEqual(client.get('/api/profile/progress').json()['background']['language'],'spanish')
            cookies=dict(client.cookies)
        with TestClient(self.app(),base_url='https://coach.example.com') as restarted:
            restarted.cookies.update(cookies)
            self.assertEqual(restarted.get('/api/me').json()['display_name'],'Moved learner')
    def test_untrusted_host_is_rejected_and_http_redirects(self):
        app=self.app()
        with TestClient(app,base_url='http://coach.example.com') as client:
            self.assertEqual(client.get('/login',follow_redirects=False).status_code,307)
            self.assertEqual(client.get('/login',headers={'Host':'evil.example.com'},follow_redirects=False).status_code,400)
    def test_only_trusted_proxy_can_establish_https(self):
        app=ProxyHeadersMiddleware(self.app(),trusted_hosts=['127.0.0.1'])
        for address,status in [('127.0.0.1',200),('198.51.100.22',307)]:
            with TestClient(app,base_url='http://coach.example.com',client=(address,50000)) as client:
                response=client.get('/login',headers={'X-Forwarded-Proto':'https'},follow_redirects=False)
                self.assertEqual(response.status_code,status)


if __name__=='__main__':unittest.main()
