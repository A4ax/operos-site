import json
import os
import sys
import urllib.parse

import requests

from google_api import api_get, api_post, get_headers

SITE = 'sc-domain:operos.de'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

SITEMAP = 'https://operos.de/sitemap.xml'


def submit_sitemap():
    enc = urllib.parse.quote(SITEMAP, safe='')
    url = f'https://searchconsole.googleapis.com/webmasters/v3/sites/{SITE}/sitemaps/{enc}'
    headers = get_headers()
    r = requests.put(url, headers=headers, timeout=60)
    print(f'Submit sitemap {SITEMAP}: HTTP {r.status_code}')
    if r.status_code not in (200, 204):
        print(f'  {r.text[:400]}')
    else:
        print('  OK — Google will now fetch the sitemap.')


def request_indexing(urls):
    print(f'\nRequesting indexing for {len(urls)} pages...')
    ok = 0
    for u in urls:
        r = api_post(
            'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect',
            {'inspectionUrl': u, 'siteUrl': SITE},
        )
        if r.status_code == 200:
            data = r.json()
            status = data.get('inspectionResult', {}).get('indexStatusResult', {}).get('verdict')
            ok += 1
            print(f'  [{status or "queued"}] {u}')
        else:
            print(f'  [err {r.status_code}] {u} {r.text[:150]}')
        # throttle: API allows ~600/day; keep ~1/sec
        import time
        time.sleep(1.1)
    print(f'\nDone. {ok} pages queued.')


def top_pages(limit=20):
    articles = json.load(open(os.path.join(PROJECT_ROOT, 'data', 'articles.json')))
    articles.sort(key=lambda a: a.get('published_at', ''), reverse=True)
    urls = []
    for a in articles[:limit]:
        slug = a.get('slug')
        if slug:
            urls.append(f'https://operos.de/posts/{slug}.html')
    urls.insert(0, 'https://operos.de/')
    return urls


def main():
    submit_sitemap()
    urls = top_pages(limit=20)
    request_indexing(urls)


if __name__ == '__main__':
    main()