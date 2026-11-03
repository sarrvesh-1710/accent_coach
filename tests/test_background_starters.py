"""Language-only onboarding stays optional and yields to personal evidence."""
import re
import tempfile
import unittest
from fastapi.testclient import TestClient
from accounts.store import Store
from accounts.coaching import profile_progress
from accounts.background import DEFAULT,PACKS
from site_server import create_site

PROMPTS=[dict(id='think',text='I think so',target_phones=['TH']),dict(id='ship',text='The ship is here',target_phones=['IH']),dict(id='bad',text='It is bad',target_phones=['AE'])]


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name)
        self.owner=self.store.register('alice','background-test-403','Alice')
    def set_background(self,language='',enabled=True,goals=None):
        self.store.profile(self.owner,'Alice',goals or [],background=dict(language=language,use_starters=enabled))
    def plan(self):return profile_progress(self.store,self.owner,PROMPTS)
    def test_five_languages_skip_multilingual_and_opt_out(self):
        self.assertEqual(set(PACKS),{'arabic','hindi','japanese','mandarin','spanish'})
        for language,first in [('japanese','AE'),('spanish','IH'),('mandarin','TH'),('hindi','TH'),('arabic','IH')]:
            self.set_background(language)
            data=self.plan();self.assertEqual(data['recommendations'][0]['phone'],first)
            self.assertTrue(data['starter']['tailored'])
            self.assertEqual({s['phone'] for s in data['recommendations']},{'TH','IH','AE'})
        self.set_background('other');self.assertFalse(self.plan()['starter']['tailored'])
        self.set_background('japanese',enabled=False);self.assertEqual(self.plan()['recommendations'][0]['phone'],'TH')
        self.set_background();self.assertEqual(self.store.background(self.owner),DEFAULT)
    def test_legacy_country_is_never_used_and_is_cleared_on_save(self):
        with self.store.connect() as db:
            db.execute("UPDATE learning_preferences SET country='JP',language='',use_starters=1 WHERE user_id=?",(self.owner,))
        self.assertFalse(self.plan()['starter']['tailored'])
        self.assertNotIn('country',self.plan()['background'])
        self.assertNotIn('country_label',self.plan()['starter'])
        self.set_background('spanish')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT country FROM learning_preferences WHERE user_id=?',(self.owner,)).fetchone()[0],'')
    def test_goals_override_starter_without_manufacturing_feedback(self):
        self.set_background('japanese',goals=['TH'])
        data=self.plan();self.assertEqual(data['recommendations'][0]['phone'],'TH')
        self.assertTrue(all(s['observations']==0 and s['practice']==0 for s in data['sounds']))
    def test_personal_results_remove_all_language_ordering(self):
        self.set_background('japanese')
        identity=self.store.create_attempt(self.owner,PROMPTS[0],b'fixture')
        self.store.finish(self.owner,identity,dict(target_assessment=dict(targets=[dict(expected_phone='TH',status='alternative_favored')])))
        baseline=self.plan()
        self.set_background('spanish')
        changed=self.plan()
        self.assertFalse(changed['starter']['active'])
        self.assertEqual(baseline['recommendations'],changed['recommendations'])
        self.assertEqual(changed['recommendations'][0]['phone'],'TH')
    def test_existing_accounts_and_legacy_updates_preserve_language(self):
        with self.store.connect() as db:db.execute('DROP TABLE learning_preferences')
        migrated=Store(self.temp.name)
        self.assertEqual(migrated.background(self.owner),DEFAULT)
        self.assertEqual(migrated.login('alice','background-test-403'),self.owner)
        self.set_background('japanese');self.store.profile(self.owner,'New name',['IH'])
        self.assertEqual(Store(self.temp.name).background(self.owner)['language'],'japanese')
    def test_invalid_background_leaves_entire_profile_unchanged(self):
        for invalid in (dict(language='INVALID'),dict(use_starters='yes')):
            with self.assertRaises(ValueError):self.store.profile(self.owner,'Changed',['TH'],background=invalid)
        self.assertEqual(self.store.background(self.owner),DEFAULT)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT display_name FROM users WHERE id=?',(self.owner,)).fetchone()[0],'Alice')
    def test_signup_persistence_validation_and_owner_isolation(self):
        app=create_site(data_root=self.temp.name,prompts=PROMPTS,analyzer=lambda *a,**k:None)
        with TestClient(app,base_url='http://localhost') as client:
            page=client.get('/signup');self.assertIn('Language of origin (optional)',page.text);self.assertNotIn('origin-country',page.text)
            response=client.post('/signup',data=dict(csrf=client.cookies['accent_login_csrf'],username='starter',password='background-test-403',display_name='Starter',language='japanese',use_starters='1'))
            self.assertEqual(response.status_code,200)
            token=re.search('name="csrf-token" content="([^"]+)"',response.text).group(1)
            plan=client.get('/api/profile/progress').json()
            self.assertEqual(plan['background']['language'],'japanese');self.assertEqual(plan['recommendations'][0]['phone'],'AE')
            self.assertEqual(len(client.get('/api/lessons').json()),3)
            payload=dict(display_name='Starter',goals=[],background=dict(language='spanish',use_starters=True),user_id=self.owner)
            self.assertEqual(client.post('/api/profile',json=payload,headers={'X-CSRF-Token':token}).status_code,200)
            self.assertEqual(client.get('/api/profile/progress').json()['recommendations'][0]['phone'],'IH')
            self.assertEqual(self.store.background(self.owner),DEFAULT)
            payload['background']=None
            self.assertEqual(client.post('/api/profile',json=payload,headers={'X-CSRF-Token':token}).status_code,422)
            with TestClient(app,base_url='http://localhost') as other:
                other.cookies.update(client.cookies)
                self.assertEqual(other.get('/api/profile/progress').json()['background']['language'],'spanish')


if __name__=='__main__':unittest.main()
