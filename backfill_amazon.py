import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.generator import ContentGenerator

project_root = os.path.dirname(os.path.abspath(__file__))
articles_path = os.path.join(project_root, 'data', 'articles.json')
config_path = os.path.join(project_root, 'config', 'settings.json')

with open(config_path, 'r') as f:
    config = json.load(f)

generator = ContentGenerator(config)

with open(articles_path, 'r', encoding='utf-8') as f:
    articles = json.load(f)

updated = 0
for article in articles:
    content = article.get('content', '')
    if 'upgrade your setup' not in content:
        affiliate_links = generator._insert_affiliate_links(article['title'], content)
        content = generator._inject_inline_amazon_link(content, affiliate_links)
        article['content'] = content
        article['affiliate_links'] = affiliate_links
        updated += 1

with open(articles_path, 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"Updated {updated} of {len(articles)} articles with new Amazon links + inline CTA")