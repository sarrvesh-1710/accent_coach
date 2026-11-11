"""Website routes, useful messages, metadata, and navigation contracts."""
from html.parser import HTMLParser
import json
import unittest
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient
import app_2
from site_pages import contact_links, load_site_config, row_cards
from site_server import create_site


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {'a', 'link'} and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'img' and attrs.get('src'):
            self.links.append(attrs['src'])


class WebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.client = TestClient(create_site(data_root=cls.temp.name), base_url='http://localhost')
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.temp.cleanup()

    def test_pages_have_titles_descriptions_contact_and_working_local_links(self):
        titles = set()
        import re
        for path in ('/help', '/privacy', '/terms'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            content = response.text
            self.assertIn('name="description"', content)
            self.assertIn('name="viewport"', content)
            self.assertIn('lang="en"', content)
            self.assertIn('mailto:sarrveshm@tamu.edu', content)
            self.assertIn('Accent coach #3', content)
            self.assertNotIn('tel:', content)
            self.assertNotIn('\u2014', content)
            titles.add(re.search('<title>(.*?)</title>', content).group(1))
            links = Links(); links.feed(content)
            for link in links.links:
                if link.startswith('/'):
                    self.assertEqual(self.client.get(link).status_code, 200, link)
        self.assertEqual(len(titles), 3)

    def test_custom_404_retains_status_code_and_api_errors_remain_json(self):
        response = self.client.get('/page-that-does-not-exist', headers={'accept': 'text/html'})
        self.assertEqual(response.status_code, 404)
        self.assertIn('Back to practice', response.text)
        self.assertIn('Page not found | Accent Coach', response.text)
        api = self.client.get('/gradio_api/not-a-real-route', headers={'accept': 'text/html'})
        self.assertEqual(api.status_code, 404)
        self.assertIn('application/json', api.headers['content-type'])

    def test_favicon_and_styles_serve_without_large_image_payloads(self):
        icon = self.client.get('/favicon.ico')
        self.assertEqual(icon.status_code, 200)
        self.assertTrue(icon.content.startswith(b'\x00\x00\x01\x00'))
        self.assertLess(len(icon.content), 10_000)
        css = self.client.get('/site-assets/site.css', headers={'accept-encoding': 'gzip'})
        self.assertEqual(css.status_code, 200)
        self.assertEqual(css.headers.get('content-encoding'), 'gzip')
        self.assertIn('prefers-reduced-motion', css.text)

    def test_root_requires_sign_in_and_private_pages_redirect(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sign in | Accent Coach', response.text)
        self.assertIn('name="description"', response.text)
        for path in ('/practice', '/profile', '/history'):
            self.assertEqual(self.client.get(path, follow_redirects=False).headers['location'], '/login')
        self.assertEqual(self.client.get('/robots.txt').text, 'User-agent: *\nDisallow: /\n')

    def test_contact_links_are_explicit_and_phone_is_optional(self):
        config = load_site_config()
        self.assertIsNone(config['phone'])
        self.assertIsNone(config['public_url'])
        self.assertNotIn('tel:', contact_links(config))
        # Example number is only a formatting test, never public page content.
        self.assertIn('tel:+15555550123', contact_links({'phone': '+1 (555) 555-0123'}))

    def test_responsive_evidence_escapes_model_text_and_preserves_values(self):
        content = row_cards(['Sound', 'Details', 'Margin'], [['TH', '<script>alert(1)</script>', 2.34567]])
        self.assertNotIn('<script>', content)
        self.assertIn('2.346', content)
        self.assertIn('&lt;script&gt;', content)
        self.assertNotIn('<table', content)

    def test_history_empty_and_deletion_confirmation_have_actionable_messages(self):
        with patch('attempt_history.list_attempts', return_value=[]):
            self.assertIn('No saved attempts', app_2.refresh_history('think')[1])
        with patch('attempt_history.delete_attempt') as delete:
            values = app_2.remove_history('anything', False, 'think')
            delete.assert_not_called()
            self.assertIn('confirmation', values[1])

    def test_listening_examples_are_complete_and_labeled(self):
        import io
        import wave
        from pipeline import load_prompts
        for prompt in load_prompts():
            self.assertTrue(prompt['practice_ipa'])
            self.assertNotIn('?', prompt['practice_ipa'])
            markup = app_2.sentence_html(prompt)
            self.assertIn('Synthetic English example', markup)
            self.assertIn('not used for scoring', markup)
            response = self.client.get('/site-assets/examples/' + prompt['id'] + '.wav')
            self.assertEqual(response.status_code, 200)
            with wave.open(io.BytesIO(response.content)) as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getframerate(), 16000)
                self.assertGreater(audio.getnframes(), 0)

    def test_sentence_markup_escapes_text_and_rejects_unsafe_example_paths(self):
        markup = app_2.sentence_html({'id': '../private', 'text': 'think <script>alert(1)</script>',
                                     'target_words': ['think'], 'practice_ipa': '<unsafe>'})
        self.assertNotIn('<script>', markup)
        self.assertNotIn('data-example=', markup)
        self.assertIn('&lt;unsafe&gt;', markup)
        self.assertIn('<mark class="target-sound">th</mark>ink', markup)


if __name__ == '__main__':
    unittest.main()
