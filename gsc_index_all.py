import json
import os
import sys
import time

from google_api import api_post

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = 'sc-domain:operos.de'
RESUME_FILE = os.path.join(PROJECT_ROOT, 'data', 'index_requested.json')


def load_articles():
    with open(os.path.join(PROJECT_ROOT, 'data', 'articles.json'), encoding='utf-8') as f:
        return json.load(f)


def load_done():
    try:
        with open(RESUME_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_done(done):
    with open(RESUME_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(done), f, indent=2)


def main():
    done = load_done()
    articles = load_articles()
    urls = ['https://operos.de/']
    for a in articles:
        if a.get('slug'):
            urls.append(f'https://operos.de/posts/{a["slug"]}.html')
    # category + legal pages
    cats = sorted(set(a.get('category', '') for a in articles if a.get('category')))
    for c in cats:
        urls.append(f'https://operos.de/categories/{c.lower().replace(" ", "-")}.html')
    urls += ['https://operos.de/about.html', 'https://operos.de/sitemap.xml']

    pending = [u for u in urls if u not in done]
    print(f'Total URLs: {len(urls)} | already requested: {len(done)} | pending: {len(pending)}')

    # Google's URL Inspection API allows ~2000/day; keep to ~150 per run to be safe.
    batch = pending[:150]
    if not batch:
        print('Nothing pending. Run again after new articles are added.')
        return

    ok = 0
    for u in batch:
        try:
            r = api_post(
                'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect',
                {'inspectionUrl': u, 'siteUrl': SITE},
            )
            if r.status_code == 200:
                data = r.json()
                verdict = data.get('inspectionResult', {}).get('indexStatusResult', {}).get('verdict', '')
                ok += 1
                done.add(u)
                print(f'  [{verdict or "queued"}] {u}')
            else:
                print(f'  [err {r.status_code}] {u} {r.text[:120]}')
        except Exception as e:
            print(f'  [exc] {u} {e}')
        time.sleep(1.0)

    save_done(done)
    print(f'\nDone. {ok} requested this run. Total done: {len(done)}')


if __name__ == '__main__':
    main()