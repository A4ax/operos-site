import json
import os
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8081
REDIRECT_URI = f'http://localhost:{PORT}/'

# Pinterest app credentials
CLIENT_ID = os.environ.get('PINTEREST_CLIENT_ID', '') or '1611118'
def _get_secret():
    return os.environ.get('PINTEREST_CLIENT_SECRET', '') or ''

# Read + write scopes so we can pin and manage boards
SCOPES = 'boards:read,boards:write,pins:read,pins:write'

captured_code = None
auth_error = None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_code, auth_error
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if 'code' in params:
            captured_code = params['code'][0]
            body = b'<h2>Authorization successful! You can close this window.</h2>'
            self.send_response(200)
        elif 'error' in params:
            auth_error = params.get('error', ['unknown'])[0]
            body = f'<h2>Error: {auth_error}</h2>'.encode()
            self.send_response(200)
        else:
            body = b'<h2>No code received.</h2>'
            self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    secret = _get_secret() or (sys.argv[1] if len(sys.argv) > 1 else '')
    if not secret:
        print('ERROR: PINTEREST_CLIENT_SECRET is not set.')
        print('Add it to .env or pass it: python pinterest_auth.py YOUR_APP_SECRET')
        sys.exit(1)

    server = HTTPServer(('localhost', PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    auth_url = (
        'https://www.pinterest.com/oauth/?'
        f'client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe="")}'
        f'&response_type=code&scope={urllib.parse.quote(SCOPES, safe=",")}'
    )
    print('=' * 70)
    print('OPEN THIS URL IN YOUR BROWSER, SIGN IN, AND CLICK AUTHORIZE:')
    print()
    print(auth_url)
    print()
    print('Waiting for authorization...')
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    for _ in range(300):
        if captured_code:
            break
        if auth_error:
            print(f'Auth error: {auth_error}')
            sys.exit(1)
        time.sleep(1)

    server.shutdown()
    server.server_close()

    if not captured_code:
        print('Timed out.')
        sys.exit(1)

    print('Exchanging code for token...')
    # Pinterest requires Basic auth header: base64(client_id:client_secret)
    import base64 as b64
    basic = b64.b64encode(f'{CLIENT_ID}:{secret}'.encode()).decode()
    body = {
        'grant_type': 'authorization_code',
        'code': captured_code,
        'redirect_uri': REDIRECT_URI,
        'continuous_refresh': 'true',
    }
    r = requests.post(
        'https://api.pinterest.com/v5/oauth/token',
        data=body,
        headers={
            'Authorization': f'Basic {basic}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        timeout=60,
    )
    if r.status_code != 200:
        print(f'Token exchange failed: {r.status_code} {r.text[:300]}')
        sys.exit(1)
    data = r.json()
    token = data.get('access_token', '')
    refresh_token = data.get('refresh_token', '')
    if not token:
        print('No access_token in response:', r.text)
        sys.exit(1)
    print(f'Exchange OK. scope={data.get("scope")} expires_in={data.get("expires_in")}')
    if refresh_token:
        print('Refresh token also obtained (pinr_...).')

    # Save to .env (replace existing PINTEREST_TOKEN)
    env_path = os.path.join(PROJECT_ROOT, '.env')
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    updates = {'PINTEREST_TOKEN=': f'PINTEREST_TOKEN={token}\n'}
    if refresh_token:
        updates['PINTEREST_REFRESH_TOKEN='] = f'PINTEREST_REFRESH_TOKEN={refresh_token}\n'
    for key, val in updates.items():
        found = False
        for i, line in enumerate(lines):
            if line.startswith(key):
                lines[i] = val
                found = True
        if not found:
            lines.append(f'\n{val}')
    with open(env_path, 'w') as f:
        f.writelines(lines)

    print('SUCCESS! Token saved to .env')
    print('You can now run: python pin_backfill.py 15')


if __name__ == '__main__':
    main()