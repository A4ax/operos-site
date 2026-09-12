"""Instant Pinterest token check: validates auth + reports which scopes work.
Usage: python pinterest_test.py <pina_token>"""
import sys
import requests


def main():
    tok = sys.argv[1].strip() if len(sys.argv) > 1 else ''
    if not tok:
        print('Usage: python pinterest_test.py <token>')
        return
    h = {'Authorization': f'Bearer {tok}'}

    r = requests.get('https://api.pinterest.com/v5/user_account', headers=h, timeout=30)
    if r.status_code != 200:
        print(f'AUTH FAILED: {r.status_code} {r.text[:150]}')
        return
    u = r.json()
    print(f'OK - logged in as: {u.get("username")} (business: {u.get("business_name")})')

    # boards read
    r = requests.get('https://api.pinterest.com/v5/boards', headers=h, timeout=30)
    if r.status_code == 200:
        items = r.json().get('items', []) or []
        print(f'boards:read OK - {len(items)} board(s)')
    else:
        print(f'boards:read FAILED: {r.text[:100]}')

    # pins:write test (harmless attempt, no real image)
    r = requests.post(
        'https://api.pinterest.com/v5/pins',
        json={
            'board_id': '1092756365776584519',
            'link': 'https://operos.de/',
            'title': 'permission test',
            'description': 'permission test',
            'media_source': {'source_type': 'image_url', 'url': 'https://operos.de/static/style.css'},
        },
        headers=h,
        timeout=30,
    )
    if r.status_code in (201, 200):
        print('pins:write OK - pin created')
    else:
        print(f'pins:write: {r.status_code} {r.text[:130]}')


if __name__ == '__main__':
    main()