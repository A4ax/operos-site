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

OLD_DISCLOSURE = "keep our content free"
OLD_CTA = "we may earn a small commission at no extra cost to you."

with open(articles_path, 'r', encoding='utf-8') as f:
    articles = json.load(f)

updated = 0
for article in articles:
    content = article.get('content', '')
    changed = False

    # Remove old commission text
    if OLD_DISCLOSURE in content or OLD_CTA in content:
        content = content.replace(OLD_DISCLOSURE, 'keep our readers informed')
        content = content.replace(OLD_CTA, '')
        content = content.replace('*Disclosure: We may earn a commission when you use our links to claim a discount or sign up for an account. This helps us keep our readers informed. Thank you for your support!*', '')
        changed = True

    # Rewire any remaining broken #affiliate-... anchors
    rewired = generator._rewire_affiliate_anchors(content)
    if rewired != content:
        content = rewired
        changed = True

    # Refresh affiliate links (Amazon) + inline CTA if missing
    if 'upgrade your setup' not in content:
        affiliate_links = generator._insert_affiliate_links(article['title'], content)
        content = generator._inject_inline_amazon_link(content, affiliate_links)
        article['affiliate_links'] = affiliate_links
        changed = True

    if changed:
        article['content'] = content
        updated += 1

with open(articles_path, 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"Updated {updated} of {len(articles)} articles")