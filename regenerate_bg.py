"""Regenerate ONLY Buyers Guides articles with the improved image resolver."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.generator import ContentGenerator

ROOT = os.path.dirname(os.path.abspath(__file__))
arts = json.load(open(os.path.join(ROOT, 'data', 'articles.json'), encoding='utf-8'))
cfg = json.load(open(os.path.join(ROOT, 'config', 'settings.json')))
g = ContentGenerator(cfg)

count = 0
for a in arts:
    if a.get('category') != 'Buyers Guides':
        continue
    topic = {
        'title': a['title'],
        'category': 'Buyers Guides',
        'search_intent': 'commercial',
        'topic_type': 'amazon_product',
    }
    new = g.generate_article(topic)
    new['published_at'] = a.get('published_at', new['published_at'])
    new['slug'] = a.get('slug', new['slug'])
    arts[arts.index(a)] = new
    count += 1

json.dump(arts, open(os.path.join(ROOT, 'data', 'articles.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'Regenerated {count} Buyers Guides articles')

# verify
bg = [a for a in arts if a.get('category') == 'Buyers Guides']
imgs = {}
for a in bg:
    imgs[a.get('image', '')] = imgs.get(a.get('image', ''), 0) + 1
dupes = {k: v for k, v in imgs.items() if v > 1}
print(f'Buyers Guides: {len(bg)} articles, {len(imgs)} distinct images, {len(dupes)} dupes')