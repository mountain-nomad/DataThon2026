"""Exercise login against the local frontend, without videos or existing job results."""
import json
from pathlib import Path
import unittest
import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:3000'
CREDENTIALS = json.loads((ROOT / 'local/access.json').read_text())

class LoginTests(unittest.TestCase):
    def setUp(self):
        self.client = httpx.Client(base_url=BASE, timeout=10)
        self.addCleanup(self.client.close)

    def login(self, **extra):
        return self.client.post('/api/auth/login', data={**CREDENTIALS, 'next':'/ru/demo-inference', **extra})

    def test_page_shows_login_without_challenge(self):
        r=self.client.get('/ru/demo-inference')
        self.assertEqual(r.status_code,200)
        self.assertIn('action="/api/auth/login"',r.text)
        self.assertNotIn('www-authenticate',r.headers)

    def test_api_and_upload_require_login(self):
        self.assertEqual(self.client.get('/api/jobs/nonexistent-login-test/pipeline').status_code,401)
        self.assertEqual(self.client.post('/api/v1/analyze').status_code,401)

    def test_incorrect_password_fails(self):
        self.assertEqual(self.login(password='wrong').status_code,401)
        self.assertFalse(self.client.cookies)

    def test_login_sets_http_only_cookie_and_opens_page(self):
        r=self.login()
        self.assertEqual(r.status_code,303)
        self.assertEqual(r.headers['location'],'/ru/demo-inference')
        self.assertIn('HttpOnly',r.headers['set-cookie'])
        r=self.client.get('/ru/demo-inference')
        self.assertEqual(r.status_code,200)
        self.assertNotIn('action="/api/auth/login"',r.text)

    def test_tampered_cookie_fails(self):
        self.login()
        self.client.cookies.clear()
        self.client.cookies.set('datathon_session','9999999999.invalid')
        self.assertEqual(self.client.get('/api/jobs/nonexistent-login-test/pipeline').status_code,401)

    def test_external_return_url_rejected(self):
        self.assertEqual(self.login(next='//example.com').headers['location'],'/ru/demo-inference')

    def test_cross_origin_login_rejected(self):
        r=self.client.post('/api/auth/login',data=CREDENTIALS,headers={'origin':'https://example.com'})
        self.assertEqual(r.status_code,403)

class ApiKeyTests(unittest.TestCase):
    def setUp(self):
        from dotenv import dotenv_values
        self.key=dotenv_values(ROOT/'backend/.env')['API_KEY']
        self.client=httpx.Client(base_url=BASE,timeout=10)
        self.addCleanup(self.client.close)

    def test_missing_and_wrong_keys_rejected(self):
        for headers in [{},{'X-API-Key':'wrong'}]:
            self.assertEqual(self.client.get('/api/v1/jobs/nonexistent-api-test',headers=headers).status_code,401)
            self.assertEqual(self.client.post('/api/v1/analyze',headers=headers).status_code,401)

    def test_correct_key_needs_no_browser_session(self):
        headers={'X-API-Key':self.key}
        self.assertEqual(self.client.get('/api/v1/jobs/nonexistent-api-test',headers=headers).status_code,404)
        r=self.client.post('/api/v1/analyze',headers=headers,files={'file':('empty.mov',b'','video/quicktime')})
        self.assertEqual(r.status_code,400)
        self.assertIn('empty',r.json()['detail'])

    def test_browser_session_cannot_hide_wrong_key(self):
        self.client.post('/api/auth/login',data=CREDENTIALS)
        self.assertEqual(self.client.post('/api/v1/analyze',headers={'X-API-Key':'wrong'}).status_code,401)

if __name__=='__main__':unittest.main()
