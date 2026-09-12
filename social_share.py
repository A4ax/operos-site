"""Auto-share new articles to social platforms.

Reads tokens from the .env file. Each platform is optional — if its token
is missing, that platform is skipped. Run automatically after each deploy,
or manually: python social_share.py [url]

Required .env entries (fill in the ones you want to use):
  PINTEREST_TOKEN   - from Pinterest Developers (create a "pin it" app)
  X_BEARER_TOKEN    - from developer.x.com (App -> Keys and tokens)
  FACEBOOK_PAGE_ID  - your Facebook page id
  FACEBOOK_TOKEN    - long-lived page access token
  LINKEDIN_TOKEN    - LinkedIn access token (Person/Org URN in config)

Pinterest account setup guide: see SOCIAL_SETUP.md
"""
import json
import os
import sys
import urllib.parse

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def newest_article():
    with open(os.path.join(PROJECT_ROOT, 'data', 'articles.json'), encoding='utf-8') as f:
        arts = json.load(f)
    arts.sort(key=lambda a: a.get('published_at', ''), reverse=True)
    return arts[0]


def post_pinterest(url, title, image_url):
    token = os.environ.get('PINTEREST_TOKEN')
    if not token:
        return 'Pinterest: no token'
    body = {
        'board_id': os.environ.get('PINTEREST_BOARD_ID', ''),
        'link': url,
        'title': title,
        'description': title,
        'media_source': {'source_type': 'image_url', 'url': image_url},
    }
    r = requests.post(
        'https://api-sandbox.pinterest.com/v5/pins',
        json=body,
        headers={'Authorization': f'Bearer {token}'},
        timeout=30,
    )
    return f'Pinterest: HTTP {r.status_code} {r.text[:150]}'


def post_x(url, title):
    token = os.environ.get('X_BEARER_TOKEN')
    if not token:
        return 'X: no token'
    text = f'{title} {url}'
    # X API v2 create tweet (requires OAuth1a user context normally; this
    # endpoint needs app-level OAuth2 with write scope).
    r = requests.post(
        'https://api.x.com/2/tweets',
        json={'text': text},
        headers={'Authorization': f'Bearer {token}'},
        timeout=30,
    )
    return f'X: HTTP {r.status_code} {r.text[:150]}'


def post_facebook(url, title):
    page_id = os.environ.get('FACEBOOK_PAGE_ID')
    token = os.environ.get('FACEBOOK_TOKEN')
    if not page_id or not token:
        return 'Facebook: missing config'
    r = requests.post(
        f'https://graph.facebook.com/v19.0/{page_id}/feed',
        data={'message': title, 'link': url, 'access_token': token},
        timeout=30,
    )
    return f'Facebook: HTTP {r.status_code} {r.text[:150]}'


def post_linkedin(url, title):
    token = os.environ.get('LINKEDIN_TOKEN')
    if not token:
        return 'LinkedIn: no token'
    urn = os.environ.get('LINKEDIN_URN', 'urn:li:person:')
    body = {
        'author': urn,
        'lifecycleState': 'PUBLISHED',
        'specificContent': {
            'com.linkedin.ugc.ShareContent': {
                'shareCommentary': {'text': title},
                'shareMediaCategory': 'ARTICLE',
                'media': [{'status': 'READY', 'originalUrl': url, 'title': {'text': title}}],
            }
        },
        'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'},
    }
    r = requests.post(
        'https://api.linkedin.com/v2/ugcPosts',
        json=body,
        headers={'Authorization': f'Bearer {token}'},
        timeout=30,
    )
    return f'LinkedIn: HTTP {r.status_code} {r.text[:150]}'


def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
        title = sys.argv[2] if len(sys.argv) > 2 else 'New article on Operos'
        image = sys.argv[3] if len(sys.argv) > 3 else ''
    else:
        a = newest_article()
        url = f'https://operos.de/posts/{a["slug"]}.html'
        title = a['title']
        image = a.get('image', '')
    results = [
        post_pinterest(url, title, image),
        post_x(url, title),
        post_facebook(url, title),
        post_linkedin(url, title),
    ]
    for r in results:
        print(r)


if __name__ == '__main__':
    main()