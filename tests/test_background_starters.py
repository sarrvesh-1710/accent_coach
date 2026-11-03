"""Optional onboarding must not constrain personal evidence or hide any lessons."""
import re
import tempfile
import unittest
from fastapi.testclient import TestClient
from accounts.store import Store
from accounts.coaching import profile_progress
from accounts.background import DEFAULT,COUNTRIES
from site_server import create_site

PROMPTS=[dict(id='think',text='I think so',target_phones=['TH']),dict(id='ship',text='The ship is here',target_phones=['IH']),dict(id='bad',text='It is bad',target_phones=['AE'])]


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name)
        self.owner=self.store.register('alice','background-test-403','Alice')
    def set_background(self,country='',language='',enabled=True,goals=None):
        self.store.profile(self.owner,'Alice',goals or [],background=dict(country=country,language=language,use_starters=enabled))
    def plan(self):return profile_progress(self.store,self.owner,PROMPTS)
    def test_country_starters_are_optional_and_language_can_override(self):
        self.set_background('JP');self.assertEqual(self.plan()['recommendations'][0]['phone'],'AE')
        self.set_background('MX');self.assertEqual(self.plan()['recommendations'][0]['phone'],'IH')
        self.set_background('CN');self.assertEqual(self.plan()['recommendations'][0]['phone'],'TH')
        self.set_background('JP','spanish');self.assertEqual(self.plan()['recommendations'][0]['phone'],'IH')
        self.set_background('JP','other');self.assertFalse(self.plan()['starter']['tailored'])
        self.set_background('JP',enabled=False);self.assertEqual(self.plan()['recommendations'][0]['phone'],'TH')
        self.set_background();self.assertEqual(self.store.background(self.owner),DEFAULT)
        self.set_background('IN');self.assertFalse(self.plan()['starter']['tailored'])
        self.assertGreater(len(COUNTRIES),200)
    def test_goals_override_starter_and_every_sound_remains_available(self):
        self.set_background('JP',goals=['TH'])
        data=self.plan();self.assertEqual(data['recommendations'][0]['phone'],'TH')
        self.assertEqual({s['phone'] for s in data['recommendations']},{'TH','IH','AE'})
        self.assertTrue(all(s['observations']==0 and s['practice']==0 for s in data['sounds']))
    def test_personal_results_remove_all_background_ordering(self):
        self.set_background('JP')
        identity=self.store.create_attempt(self.owner,PROMPTS[0],b'fixture')
        self.store.finish(self.owner,identity,dict(target_assessment=dict(targets=[dict(expected_phone='TH',status='alternative_favored')])))
        baseline=self.plan()
        self.set_background('MX')
        changed=self.plan()
        self.assertFalse(changed['starter']['active'])
        self.assertEqual(baseline['recommendations'],changed['recommendations'])
        self.assertEqual(changed['recommendations'][0]['phone'],'TH')
    def test_existing_accounts_migrate_and_legacy_profile_updates_preserve_background(self):
        with self.store.connect() as db:db.execute('DROP TABLE learning_preferences')
        migrated=Store(self.temp.name)
        self.assertEqual(migrated.background(self.owner),DEFAULT)
        self.assertEqual(migrated.login('alice','background-test-403'),self.owner)
        self.set_background('JP');self.store.profile(self.owner,'New name',['IH'])
        self.assertEqual(Store(self.temp.name).background(self.owner)['country'],'JP')
    def test_invalid_background_leaves_entire_profile_unchanged(self):
        for invalid in (dict(country='INVALID'),dict(language='INVALID'),dict(use_starters='yes')):
            with self.assertRaises(ValueError):self.store.profile(self.owner,'Changed',['TH'],background=invalid)
        self.assertEqual(self.store.background(self.owner),DEFAULT)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT display_name FROM users WHERE id=?',(self.owner,)).fetchone()[0],'Alice')
    def test_signup_persistence_validation_and_owner_isolation(self):
        app=create_site(data_root=self.temp.name,prompts=PROMPTS,analyzer=lambda *a,**k:None)
        with TestClient(app,base_url='http://localhost') as client:
            page=client.get('/signup');self.assertIn('Country of origin (optional)',page.text)
            response=client.post('/signup',data=dict(csrf=client.cookies['accent_login_csrf'],username='starter',password='background-test-403',display_name='Starter',country='JP',language='',use_starters='1'))
            self.assertEqual(response.status_code,200)
            token=re.search('name="csrf-token" content="([^"]+)"',response.text).group(1)
            plan=client.get('/api/profile/progress').json()
            self.assertEqual(plan['background']['country'],'JP');self.assertEqual(plan['recommendations'][0]['phone'],'AE')
            self.assertEqual(len(client.get('/api/lessons').json()),3)
            payload=dict(display_name='Starter',goals=[],background=dict(country='MX',language='',use_starters=True),user_id=self.owner)
            self.assertEqual(client.post('/api/profile',json=payload,headers={'X-CSRF-Token':token}).status_code,200)
            self.assertEqual(client.get('/api/profile/progress').json()['recommendations'][0]['phone'],'IH')
            self.assertEqual(self.store.background(self.owner),DEFAULT)
            payload['background']=None
            self.assertEqual(client.post('/api/profile',json=payload,headers={'X-CSRF-Token':token}).status_code,422)
            with TestClient(app,base_url='http://localhost') as other:
                other.cookies.update(client.cookies)
                self.assertEqual(other.get('/api/profile/progress').json()['background']['country'],'MX')


if __name__=='__main__':unittest.main()
