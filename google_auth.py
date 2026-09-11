import json
import os
import sys
import threading
import time
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = os.path.join(PROJECT_ROOT, 'client_secret.json')
TOKEN_FILE = os.path.join(PROJECT_ROOT, 'token.json')
PORT = 8080
REDIRECT_URI = f'http://localhost:{PORT}/'

SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/adsense.readonly',
]

captured_code = None
auth_error = None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_code, auth_error
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if 'code' in params:
            captured_code = params['code'][0]
            body = b'<h2>Authorization successful!</h2><p>You can close this window now.</p>'
            self.send_response(200)
        elif 'error' in params:
            auth_error = params.get('error', ['unknown'])[0]
            body = f'<h2>Authorization failed: {auth_error}</h2>'.encode()
            self.send_response(200)
        else:
            body = b'<h2>No code received.</h2>'
            self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def build_auth_url(client_id: str) -> str:
    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true',
    }
    return f"https://accounts.google.com/o/oauth2/auth?{urllib.parse.urlencode(params)}"


def main():
    if not os.path.exists(SECRET_FILE):
        print('client_secret.json not found in project root.')
        sys.exit(1)

    with open(SECRET_FILE, 'r') as f:
        secret = json.load(f)['installed']

    server = HTTPServer(('localhost', PORT), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    auth_url = build_auth_url(secret['client_id'])
    print('=' * 70)
    print('OPEN THIS URL IN YOUR BROWSER, SIGN IN AS YOUR GOOGLE/ADSENSE')
    print('ACCOUNT, AND CLICK ALLOW:')
    print()
    print(auth_url)
    print()
    print('Waiting for authorization... (up to 5 minutes)')
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    server.serve_forever(timeout=1)
    for _ in range(300):
        if captured_code:
            break
        if auth_error:
            print(f'Auth error: {auth_error}')
            sys.exit(1)
        threading.Event().wait(1)

    server.shutdown()

    if not captured_code:
        print('Timed out waiting for authorization.')
        sys.exit(1)

    print('Exchanging code for token...')
    resp = requests.post(
        secret['token_uri'],
        data={
            'code': captured_code,
            'client_id': secret['client_id'],
            'client_secret': secret['client_secret'],
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code',
        },
        timeout=60,
    )
    if resp.status_code != 200:
        print(f'Token exchange failed: {resp.status_code} {resp.text}')
        sys.exit(1)

    token = resp.json()
    token['expires_at'] = time.time() + int(token.get('expires_in', 3600)) - 60
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token, f, indent=2)

    print('SUCCESS! Token saved to token.json')
    print('Scopes granted:', token.get('scope', ''))
    print('You can now run: python google_check.py')


if __name__ == '__main__':
    main()