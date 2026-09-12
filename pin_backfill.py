"""Pin existing articles to Pinterest (one-time backfill of best guides)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from social_share import post_pinterest

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    arts = json.load(open(os.path.join(PROJECT_ROOT, 'data', 'articles.json'), encoding='utf-8'))
    # Priority: Buyers Guides first (best Pinterest fit), then newest
    buyers = [a for a in arts if a.get('category') == 'Buyers Guides']
    others = [a for a in arts if a.get('category') != 'Buyers Guides']
    others.sort(key=lambda a: a.get('published_at', ''), reverse=True)
    targets = buyers + others

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    ok = 0
    for a in targets[:limit]:
        slug = a['slug']
        url = f"https://operos.de/posts/{slug}.html"
        title = a.get('title', slug)
        image = a.get('image', '')
        r = post_pinterest(url, title, image, slug)
        print(f"{r} | {title[:60]}")
        if 'HTTP 201' in r:
            ok += 1
        time.sleep(1.0)
    print(f"\nPinned {ok} of {min(limit, len(targets))}")


if __name__ == '__main__':
    main()