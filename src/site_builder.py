import os
import json
import re
from datetime import datetime, timezone
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape

class SiteBuilder:
    def __init__(self, config: dict):
        self.config = config
        self.site_config = config.get('site', {})
        self.deployment_config = config.get('deployment', {})
        
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        self.output_dir = output_dir
        self.static_dir = static_dir
        
        self._create_output_structure()
    
    def _create_output_structure(self):
        dirs = [
            self.output_dir,
            os.path.join(self.output_dir, 'categories'),
            os.path.join(self.output_dir, 'posts'),
            os.path.join(self.output_dir, 'static'),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
    
    def build_site(self, articles: List[Dict], categories: List[str] = None) -> str:
        if not articles:
            return "No articles to build"
        
        # Load all existing article JSON files from output folder
        all_articles = list(articles)  # Start with new articles
        posts_dir = os.path.join(self.output_dir, 'posts')
        
        for filename in os.listdir(posts_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(posts_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                        if existing['slug'] not in [a['slug'] for a in all_articles]:
                            all_articles.append(existing)
                except:
                    pass
        
        # Also load from any existing JSON metadata files
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        articles_json = os.path.join(data_dir, 'articles.json')
        if os.path.exists(articles_json):
            with open(articles_json, 'r', encoding='utf-8') as f:
                existing_articles = json.load(f)
                for ea in existing_articles:
                    if ea['slug'] not in [a['slug'] for a in all_articles]:
                        all_articles.append(ea)
        
        # Sort by published date (newest first)
        all_articles.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        if categories is None:
            categories = list(set(a.get('category', 'AI Tools') for a in all_articles))
        
        article_slugs = []
        
        for article in all_articles:
            slug = article.get('slug', self._generate_slug(article['title']))
            html_content = self._render_article_page(article, categories, all_articles)
            
            post_path = os.path.join(self.output_dir, 'posts', f"{slug}.html")
            with open(post_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            article_slugs.append(slug)
        
        self._render_home_page(all_articles, categories)
        self._render_category_pages(all_articles, categories)
        self._render_sitemap(all_articles)
        self._render_robots_txt()
        self._render_rss_feed(all_articles)
        self._render_search_data(all_articles)
        self._render_search_page()
        self._copy_static_files()
        self._render_static_pages()
        
        # Save all article metadata for next run
        with open(articles_json, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f)
        
        return f"Built {len(all_articles)} articles, {len(categories)} categories. Output: {self.output_dir}"
    
    def _render_article_page(self, article: Dict, categories: List[str] = None, all_articles: List[Dict] = None) -> str:
        template = self.env.get_template('article.html')
        
        if categories is None:
            categories = list(set(a.get('category', 'AI Tools') for a in [article]))

        related = self._related_articles(article, all_articles or [])
        
        affiliate_disclosure = """<div class="affiliate-disclosure">
    <p><strong>Disclosure:</strong> As an Amazon Associate we earn from qualifying purchases.</p>
</div>"""
        
        context = {
            'title': article['title'],
            'slug': article['slug'],
            'category': article.get('category', 'AI Tools'),
            'content': self._process_content(article['content']),
            'meta_description': article.get('meta_description', ''),
            'keywords': article.get('keywords', []),
            'published_at': article.get('published_at', datetime.now().isoformat()),
            'author': article.get('author', 'Operos Editorial Team'),
            'affiliate_links': article.get('affiliate_links', []),
            'estimated_read_time': article.get('estimated_read_time', 5),
            'word_count': article.get('word_count', 0),
            'site_name': self.site_config.get('name', 'Operos'),
            'site_domain': self.site_config.get('domain', 'operos.de'),
            'site_description': self.site_config.get('description', ''),
            'article': article,
            'categories': categories,
            'affiliate_disclosure': affiliate_disclosure,
            'current_year': datetime.now().year,
            'related': related
        }
        
        return template.render(**context)
    
    def _process_content(self, content: str) -> str:
        # Convert markdown to HTML
        lines = content.split('\n')
        html_lines = []
        in_list = False
        in_table = False
        table_lines = []
        
        for line in lines:
            # Handle tables
            if line.startswith('|'):
                if in_table and table_lines:
                    html_lines.append(self._format_table(table_lines))
                    table_lines = []
                    in_table = False
                if not in_list:
                    in_table = True
                table_lines.append(line)
                continue
            
            # Close table if we were in one
            if in_table and table_lines:
                html_lines.append(self._format_table(table_lines))
                table_lines = []
                in_table = False
            
            # Close list if we were in one
            if in_list and not line.strip().startswith('- ') and not line.strip().startswith('* ') and line.strip():
                html_lines.append('</ul>')
                in_list = False
            
            stripped = line.strip()
            
            # Handle headers
            if stripped.startswith('### '):
                html_lines.append(f'<h4>{self._convert_inline(stripped[4:])}</h4>')
            elif stripped.startswith('## '):
                html_lines.append(f'<h2>{self._convert_inline(stripped[3:])}</h2>')
            elif stripped.startswith('# '):
                html_lines.append(f'<h1>{self._convert_inline(stripped[2:])}</h1>')
            # Handle bullet lists
            elif stripped.startswith('- ') or stripped.startswith('* '):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                item_text = stripped[2:]
                html_lines.append(f'<li>{self._convert_inline(item_text)}</li>')
            # Handle horizontal rule
            elif stripped == '---':
                html_lines.append('<hr>')
            # Handle empty lines
            elif not stripped:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                continue
            # Regular paragraph
            else:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<p>{self._convert_inline(stripped)}</p>')
        
        # Close any remaining open tags
        if in_table and table_lines:
            html_lines.append(self._format_table(table_lines))
        if in_list:
            html_lines.append('</ul>')
        
        return '\n'.join(html_lines)
    
    def _convert_inline(self, text: str) -> str:
        # Convert **bold** to <strong>
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Convert *italic* to <em>
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # Convert [text](url) to <a>
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
        return text
    
    def _format_table(self, lines: List[str]) -> str:
        html = '<div class="comparison-table">\n<table>\n<thead>\n<tr>\n'
        header_cells = [cell.strip() for cell in lines[0].split('|') if cell.strip()]
        for cell in header_cells:
            html += f'<th>{cell}</th>\n'
        html += '</tr>\n</thead>\n<tbody>\n'
        
        for line in lines[2:]:
            if '---' in line:
                continue
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                html += '<tr>\n'
                for cell in cells:
                    html += f'<td>{cell}</td>\n'
                html += '</tr>\n'
        
        html += '</tbody>\n</table>\n</div>\n'
        return html
    
    def _render_home_page(self, articles: List[Dict], categories: List[str] = None):
        template = self.env.get_template('index.html')
        
        if categories is None:
            categories = list(set(a.get('category', 'AI Tools') for a in articles))
        
        featured = articles[:6]
        recent = articles[:12]
        categories = list(set(a.get('category', 'AI Tools') for a in articles))
        
        context = {
            'title': f'{self.site_config.get("name", "Operos")} - Best AI Tools & Software Reviews',
            'featured': featured,
            'recent': recent,
            'all_articles': articles,
            'categories': categories,
            'total_articles': len(articles),
            'site_name': self.site_config.get('name', 'Operos'),
            'site_domain': self.site_config.get('domain', 'operos.de'),
            'site_description': self.site_config.get('description', ''),
            'current_year': datetime.now().year
        }
        
        output_path = os.path.join(self.output_dir, 'index.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template.render(**context))
    
    def _render_category_pages(self, articles: List[Dict], categories: List[str]):
        category_template = self.env.get_template('category.html')
        
        for category in categories:
            category_articles = [a for a in articles if a.get('category') == category]
            
            if not category_articles:
                continue
            
            context = {
                'title': f'{category} — {self.site_config.get("name", "Operos")}',
                'category': category,
                'articles': category_articles,
                'site_name': self.site_config.get('name', 'Operos'),
                'site_domain': self.site_config.get('domain', 'operos.de'),
                'site_description': self.site_config.get('description', ''),
                'current_year': datetime.now().year
            }
            
            output_path = os.path.join(self.output_dir, 'categories', f'{category.lower().replace(" ", "-")}.html')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(category_template.render(**context))
    
    def _render_sitemap(self, articles: List[Dict]):
        domain = self.site_config.get('domain', 'operos.de')
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        # Home page
        xml += f'  <url>\n    <loc>https://{domain}/</loc>\n'
        xml += f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>\n'
        xml += f'    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
        
        # Article pages
        for article in sorted(articles, key=lambda x: x.get('published_at', ''), reverse=True)[:1000]:
            slug = article.get('slug', self._generate_slug(article['title']))
            url = f'https://{domain}/posts/{slug}.html'
            pub_date = article.get('published_at', '')[:10] if article.get('published_at') else datetime.now().strftime("%Y-%m-%d")
            xml += f'  <url>\n    <loc>{url}</loc>\n'
            xml += f'    <lastmod>{pub_date}</lastmod>\n'
            xml += f'    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
        
        xml += '</urlset>'
        
        sitemap_path = os.path.join(self.output_dir, 'sitemap.xml')
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write(xml)
    
    def _render_robots_txt(self):
        robots_content = f"""User-agent: *
Allow: /
Sitemap: https://{self.site_config.get('domain', 'operos.de')}/sitemap.xml

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /
"""
        with open(os.path.join(self.output_dir, 'robots.txt'), 'w') as f:
            f.write(robots_content)
    
    def _render_rss_feed(self, articles: List[Dict]):
        domain = self.site_config.get('domain', 'operos.de')
        name = self.site_config.get('name', 'Operos')
        desc = self.site_config.get('description', '')
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        xml += '<channel>\n'
        xml += f'<title>{name}</title>\n'
        xml += f'<description>{desc}</description>\n'
        xml += f'<link>https://{domain}/</link>\n'
        xml += f'<language>{self.site_config.get("language", "en")}</language>\n'
        xml += f'<atom:link href="https://{domain}/feed.xml" rel="self" type="application/rss+xml"/>\n'
        xml += f'<lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>\n'
        
        for article in sorted(articles, key=lambda x: x.get('published_at', ''), reverse=True)[:50]:
            slug = article.get('slug', self._generate_slug(article['title']))
            url = f'https://{domain}/posts/{slug}.html'
            pub_date = article.get('published_at', '')
            if pub_date:
                dt = datetime.fromisoformat(pub_date)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                pub_str = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            else:
                pub_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
            
            xml += '<item>\n'
            xml += f'<title>{article["title"]}</title>\n'
            xml += f'<link>{url}</link>\n'
            xml += f'<guid>{url}</guid>\n'
            xml += f'<pubDate>{pub_str}</pubDate>\n'
            xml += f'<description>{article.get("meta_description", "")[:300]}</description>\n'
            xml += '</item>\n'
        
        xml += '</channel>\n</rss>'
        
        feed_path = os.path.join(self.output_dir, 'feed.xml')
        with open(feed_path, 'w', encoding='utf-8') as f:
            f.write(xml)
    
    def _copy_static_files(self):
        static_dest = os.path.join(self.output_dir, 'static')
        os.makedirs(static_dest, exist_ok=True)
        
        for item in os.listdir(self.static_dir):
            src = os.path.join(self.static_dir, item)
            dst = os.path.join(static_dest, item)
            if os.path.isfile(src):
                with open(src, 'rb') as f_src:
                    with open(dst, 'wb') as f_dst:
                        f_dst.write(f_src.read())
    
    def _render_search_data(self, articles: List[Dict]):
        domain = self.site_config.get('domain', 'operos.de')
        items = []
        for article in articles:
            slug = article.get('slug', self._generate_slug(article['title']))
            items.append({
                'title': article['title'],
                'slug': slug,
                'category': article.get('category', 'AI Tools'),
                'date': article.get('published_at', '')[:10],
                'url': f'/posts/{slug}.html',
                'keywords': article.get('keywords', []),
            })
        with open(os.path.join(self.output_dir, 'search.json'), 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)

    def _render_search_page(self):
        template = self.env.get_template('search.html')
        html = template.render(
            site_name=self.site_config.get('name', 'Operos'),
            site_domain=self.site_config.get('domain', 'operos.de'),
            site_description=self.site_config.get('description', ''),
            current_year=datetime.now().year,
        )
        with open(os.path.join(self.output_dir, 'search.html'), 'w', encoding='utf-8') as f:
            f.write(html)

    def _related_articles(self, article: Dict, all_articles: List[Dict], limit: int = 3) -> List[Dict]:
        current_slug = article.get('slug', self._generate_slug(article['title']))
        category = article.get('category', 'AI Tools')
        same_cat = [
            a for a in all_articles
            if a.get('slug', self._generate_slug(a['title'])) != current_slug
            and a.get('category') == category
        ]
        if len(same_cat) < limit:
            others = [
                a for a in all_articles
                if a.get('slug', self._generate_slug(a['title'])) != current_slug
                and a.get('category') != category
            ]
            same_cat.extend(others)
        seen = []
        for a in same_cat:
            slug = a.get('slug', self._generate_slug(a['title']))
            if slug not in [x.get('slug') for x in seen]:
                seen.append(a)
            if len(seen) >= limit:
                break
        return seen

    def _render_static_pages(self):
        """Render static pages (legal, etc) using Jinja2 templates"""
        legal_pages = {
            'privacy-policy.html': {
                'template': 'privacy-policy.html',
                'context': {
                    'site_name': self.site_config.get('name', 'Operos'),
                    'site_domain': self.site_config.get('domain', 'operos.de')
                }
            },
            'terms-of-service.html': {
                'template': 'terms-of-service.html',
                'context': {
                    'site_name': self.site_config.get('name', 'Operos'),
                    'site_domain': self.site_config.get('domain', 'operos.de')
                }
            },
            'affiliate-disclosure.html': {
                'template': 'affiliate-disclosure.html',
                'context': {
                    'site_name': self.site_config.get('name', 'Operos'),
                    'site_domain': self.site_config.get('domain', 'operos.de')
                }
            },
            'datenschutz.html': {
                'template': 'datenschutz.html',
                'context': {
                    'site_name': self.site_config.get('name', 'Operos'),
                    'site_domain': self.site_config.get('domain', 'operos.de')
                }
            },
            'impressum.html': {
                'template': 'impressum.html',
                'context': {
                    'site_name': self.site_config.get('name', 'Operos'),
                    'site_domain': self.site_config.get('domain', 'operos.de')
                }
            }
        }
        
        for output_name, config in legal_pages.items():
            try:
                template = self.env.get_template(config['template'])
                html_content = template.render(**config['context'])
                output_path = os.path.join(self.output_dir, output_name)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            except Exception as e:
                print(f"Warning: Could not render {output_name}: {e}")
    
    def _generate_slug(self, title: str) -> str:
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        slug = slug.strip('-')
        return slug
