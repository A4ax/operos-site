import os
import json
import re
from datetime import datetime

data_dir = 'data'
os.makedirs(data_dir, exist_ok=True)
articles_json = os.path.join(data_dir, 'articles.json')

# Load all existing posts from output folder
all_articles = []
posts_dir = 'output/posts'

for filename in os.listdir(posts_dir):
    if filename.endswith('.html'):
        slug = filename.replace('.html', '')
        html_path = os.path.join(posts_dir, filename)
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract title from HTML
            match = re.search(r'<title>(.*?)</title>', content)
            title = match.group(1) if match else slug
            
            # Extract meta description
            match = re.search(r'<meta name="description" content="(.*?)">', content)
            meta = match.group(1) if match else ''
            
            # Clean title - remove " — Operos..." suffix
            title = re.sub(r' — Operos.*', '', title).strip()
            
            article = {
                'title': title,
                'slug': slug,
                'category': 'AI Tools',
                'content': '',
                'meta_description': meta,
                'keywords': [],
                'published_at': datetime.now().isoformat(),
                'author': 'Operos Editorial Team',
                'affiliate_links': [],
                'estimated_read_time': 5,
                'word_count': 0
            }
            all_articles.append(article)

print(f'Loaded {len(all_articles)} articles')

with open(articles_json, 'w', encoding='utf-8') as f:
    json.dump(all_articles, f)
    
print(f'Saved to {articles_json}')
