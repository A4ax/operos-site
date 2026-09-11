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

print(f'Regenerating {len(articles)} articles with fixed link cleaner...')

regenerated = []
for a in articles:
    title = a['title']
    category = a.get('category', 'AI Tools')
    topic_type = 'amazon_product' if category == 'Buyers Guides' else 'saas_tool'
    search_intent = a.get('search_intent', 'commercial' if 'review' in title.lower() or 'best' in title.lower() or 'vs' in title.lower() else 'informational')
    topic = {'title': title, 'category': category, 'search_intent': search_intent, 'topic_type': topic_type}
    new_article = generator.generate_article(topic)
    new_article['published_at'] = a.get('published_at', new_article['published_at'])
    new_article['slug'] = a.get('slug', new_article['slug'])
    regenerated.append(new_article)

with open(articles_path, 'w', encoding='utf-8') as f:
    json.dump(regenerated, f, ensure_ascii=False, indent=2)

# Verify no broken links
broken_anchor = [a for a in regenerated if 'the tool(#affiliate' in a['content'] or 'the tool(https' in a['content']]
print(f'Regenerated {len(regenerated)} articles. Broken-link articles: {len(broken_anchor)}')
print(f'Articles with working markdown links: {sum(1 for a in regenerated if "](http" in a["content"])}')