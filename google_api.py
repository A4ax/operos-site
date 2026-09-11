import json
import os
import time

import requests

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = os.path.join(PROJECT_ROOT, 'client_secret.json')
TOKEN_FILE = os.path.join(PROJECT_ROOT, 'token.json')


def load_token():
    with open(TOKEN_FILE, 'r') as f:
        return json.load(f)


def refresh_token(token, secret):
    resp = requests.post(
        secret['token_uri'],
        data={
            'refresh_token': token['refresh_token'],
            'client_id': secret['client_id'],
            'client_secret': secret['client_secret'],
            'grant_type': 'refresh_token',
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f'Token refresh failed: {resp.status_code} {resp.text}')
    new_token = {**token, **resp.json()}
    new_token['refresh_token'] = token['refresh_token']
    with open(TOKEN_FILE, 'w') as f:
        json.dump(new_token, f, indent=2)
    return new_token


def get_headers():
    token = load_token()
    secret = json.load(open(SECRET_FILE))['installed']
    if token.get('expires_at', 0) - time.time() < 60:
        token = refresh_token(token, secret)
    return {'Authorization': f"Bearer {token['access_token']}"}


def api_get(url, params=None):
    return requests.get(url, headers=get_headers(), params=params, timeout=60)


def api_post(url, body):
    headers = get_headers()
    headers['Content-Type'] = 'application/json'
    return requests.post(url, headers=headers, json=body, timeout=60)