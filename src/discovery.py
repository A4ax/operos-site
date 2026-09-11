import aiohttp
import asyncio
import json
import os
import re
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class TopicDiscovery:
    def __init__(self, config: dict):
        self.config = config
        self.reddit_config = config.get('reddit', {})
        self.seo_config = config.get('seo', {})
        self.base_urls = [
            'https://www.reddit.com/r/{}/{}.json?limit={}&sort={}&t={}',
        ]
        self.cached_topics = self._load_cached_topics()
        
    def _load_cached_topics(self) -> set:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        try:
            with open(os.path.join(data_dir, 'discovered_topics.json'), 'r') as f:
                data = json.load(f)
                return set(data.get('topics', []))
        except:
            return set()
    
    def _save_topics(self, topics: List[str]):
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        existing = list(self.cached_topics)
        for t in topics:
            existing.append(t)
        data = {
            'topics': list(set(existing)),
            'last_updated': datetime.now().isoformat()
        }
        with open(os.path.join(data_dir, 'discovered_topics.json'), 'w') as f:
            json.dump(data, f, indent=2)
    
    async def scrape_reddit(self) -> List[Dict]:
        topics = []
        headers = {
            'User-Agent': 'OperosContentEngine/1.0 (+https://operos.de)'
        }
        
        subreddits = self.reddit_config.get('subreddits', [])
        max_posts = self.reddit_config.get('max_posts_per_subreddit', 25)
        sort_by = self.reddit_config.get('sort_by', 'hot')
        time_filter = self.reddit_config.get('time_filter', 'week')
        
        async with aiohttp.ClientSession() as session:
            for subreddit in subreddits:
                url = f'https://www.reddit.com/r/{subreddit}/{sort_by}.json?limit={max_posts}&t={time_filter}'
                try:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            posts = data.get('data', {}).get('children', [])
                            for post in posts:
                                pdata = post.get('data', {})
                                title = pdata.get('title', '')
                                score = pdata.get('score', 0)
                                num_comments = pdata.get('num_comments', 0)
                                url = pdata.get('url', '')
                                subreddit_name = pdata.get('subreddit_name_prefixed', '')
                                
                                if title and score > 50:
                                    topic = {
                                        'title': title,
                                        'source': f'reddit/{subreddit_name}',
                                        'score': score,
                                        'comments': num_comments,
                                        'url': url,
                                        'category': self._categorize_topic(title),
                                        'affiliation_potential': self._assess_affiliate_potential(title),
                                        'search_intent': self._determine_search_intent(title),
                                        'difficulty': self._estimate_difficulty(score, num_comments)
                                    }
                                    topics.append(topic)
                except Exception as e:
                    print(f"Error scraping r/{subreddit}: {e}")
                
                await asyncio.sleep(random.uniform(1, 3))
        
        return topics
    
    def _categorize_topic(self, title: str) -> str:
        title_lower = title.lower()
        categories = self.seo_config.get('target_keywords', [])
        
        if any(word in title_lower for word in ['ai', 'artificial intelligence', 'llm', 'chatbot', 'gpt']):
            return 'AI Tools'
        elif any(word in title_lower for word in ['software', 'app', 'tool', 'platform']):
            return 'Software Reviews'
        elif any(word in title_lower for word in ['vs', 'versus', 'comparison', 'alternative']):
            return 'Comparisons'
        elif any(word in title_lower for word in ['how', 'tutorial', 'guide', 'learn']):
            return 'How-to Guides'
        elif any(word in title_lower for word in ['productivity', 'workflow', '效率', 'organize']):
            return 'Productivity'
        elif any(word in title_lower for word in ['design', 'figma', 'canva', 'photoshop']):
            return 'Design Tools'
        elif any(word in title_lower for word in ['marketing', 'seo', 'ads', 'email']):
            return 'Marketing Tools'
        elif any(word in title_lower for word in ['write', 'grammar', 'text', 'content']):
            return 'Writing Tools'
        elif any(word in title_lower for word in ['video', 'audio', 'music', 'podcast']):
            return 'Video & Audio'
        else:
            return 'AI Tools'
    
    def _assess_affiliate_potential(self, title: str) -> float:
        title_lower = title.lower()
        affiliate_signals = [
            'best', 'top', 'review', 'pricing', 'free', 'cheap', 'alternative',
            'subscription', 'plan', 'cost', 'software', 'tool', 'platform',
            'saas', 'app', 'productivity', 'ai', 'tool'
        ]
        score = 0
        for signal in affiliate_signals:
            if signal in title_lower:
                score += 1
        return min(score / 5, 1.0)
    
    def _determine_search_intent(self, title: str) -> str:
        title_lower = title.lower()
        if any(word in title_lower for word in ['best', 'top', 'review']):
            return 'commercial'
        elif any(word in title_lower for word in ['vs', 'versus', 'compare', 'alternative']):
            return 'commercial'
        elif any(word in title_lower for word in ['how', 'tutorial', 'guide']):
            return 'informational'
        elif any(word in title_lower for word in ['what', 'who', 'when', 'where']):
            return 'informational'
        else:
            return 'commercial'
    
    def _estimate_difficulty(self, score: int, comments: int) -> str:
        engagement = score + comments
        if engagement > 500:
            return 'high'
        elif engagement > 100:
            return 'medium'
        else:
            return 'low'
    
    async def generate_seo_topics(self) -> List[Dict]:
        topics = []
        templates = [
            "Best {tool_category} for {use_case} in 2026",
            "{tool_a} vs {tool_b}: Complete Comparison",
            "How to Use {tool} for {use_case}",
            "{tool} Review: Is It Worth It in 2026?",
            "Free Alternative to {tool}: Better Options",
            "Top 10 {tool_category} Every {audience} Needs",
            "{tool} vs {tool_category}: Which Is Better?",
            "The Ultimate Guide to {tool_category} for {use_case}",
        ]
        
        tool_categories = [
            'AI Writing Tools', 'AI Video Editors', 'AI Image Generators',
            'Project Management Tools', 'Email Marketing Tools',
            'SEO Tools', 'Design Tools', 'Note-Taking Apps',
            'AI Coding Assistants', 'CRM Software', 'Social Media Tools',
            'Password Managers', 'Cloud Storage Solutions',
            'Time Tracking Software', 'Website Builders'
        ]
        
        tools = [
            ('Notion', 'ClickUp'), ('Canva', 'Figma'), ('Grammarly', 'Hemingway'),
            ('Jasper', 'Copy.ai'), ('Midjourney', 'DALL-E'), ('Ahrefs', 'SEMrush'),
            ('Hostinger', 'Bluehost'), ('Monday.com', 'Asana'), ('ClickUp', 'Asana'),
            ('Notion', 'Obsidian'), ('Descript', 'Adobe Premiere'),
            ('Surfer SEO', 'Clearscope'), ('ConvertKit', 'Mailchimp'),
        ]
        
        use_cases = [
            'Content Creators', 'Small Business', 'Students', 'Remote Teams',
            'Freelancers', 'Marketing Agencies', 'Startups', 'E-commerce',
            'Developers', 'Designers', 'Writers', 'YouTubers',
            'Online Teachers', 'Project Managers'
        ]
        
        audiences = [
            'Remote Worker', 'Content Creator', 'Small Business Owner',
            'Freelancer', 'Developer', 'Designer', 'Marketer',
            'Student', 'Entrepreneur', 'Product Manager'
        ]
        
        # --- Main SEO / SaaS tool topics ---
        for _ in range(100):
            template = random.choice(templates)
            if '{tool_category}' in template:
                template = template.replace('{tool_category}', random.choice(tool_categories))
            if '{use_case}' in template:
                template = template.replace('{use_case}', random.choice(use_cases))
            if '{audience}' in template:
                template = template.replace('{audience}', random.choice(audiences))
            if '{tool_a}' in template and '{tool_b}' in template:
                pair = random.choice(tools)
                template = template.replace('{tool_a}', pair[0])
                template = template.replace('{tool_b}', pair[1])
            if '{tool}' in template:
                template = template.replace('{tool}', random.choice([t[0] for t in tools]))
            
            topics.append({
                'title': template,
                'source': 'seo_template',
                'topic_type': 'saas_tool',
                'score': random.randint(10, 100),
                'category': self._categorize_topic(template),
                'affiliation_potential': random.uniform(0.3, 1.0),
                'search_intent': 'commercial' if 'best' in template.lower() or 'vs' in template.lower() or 'review' in template.lower() else 'informational',
                'difficulty': random.choice(['low', 'medium']),
                'target_keywords': self._extract_keywords(template),
                'estimated_traffic': random.randint(100, 10000)
            })
        
        # --- Amazon product (buyers guide) topics ---
        products = [
            'noise cancelling headphones', 'mechanical keyboards', '4k monitors',
            'webcams', 'external ssds', 'wireless mice', 'laptop stands',
            'standing desks', 'gaming headsets', 'usb-c hubs', 'graphics tablets',
            'microphones', 'ring lights', 'blue light glasses', 'laptop backpacks',
            'office chairs', 'laptops'
        ]
        prices = [50, 100, 150, 200, 300, 500]
        product_templates = [
            'Best {product} under EUR{price} in {year}',
            'Top 10 {product} for {audience} in {year}',
            '{product} Buying Guide: What to Look For in {year}',
            'Best {product} in {year}: Tested & Ranked',
            'The {product} for Every Budget in {year}',
        ]
        
        for _ in range(60):
            template = random.choice(product_templates)
            product = random.choice(products)
            template = template.replace('{product}', product)
            template = template.replace('{price}', str(random.choice(prices)))
            template = template.replace('{audience}', random.choice(audiences))
            template = template.replace('{year}', str(datetime.now().year))
            
            topics.append({
                'title': template,
                'source': 'amazon_product',
                'topic_type': 'amazon_product',
                'score': random.randint(40, 100),
                'category': 'Buyers Guides',
                'affiliation_potential': random.uniform(0.7, 1.0),
                'search_intent': 'commercial',
                'difficulty': random.choice(['low', 'medium']),
                'target_keywords': self._extract_keywords(template),
                'estimated_traffic': random.randint(200, 8000)
            })
        
        return topics
    
    def _extract_keywords(self, title: str) -> List[str]:
        keywords = []
        words = re.findall(r'[a-zA-Z\u00C0-\u024F]+', title)
        stop_words = {'the', 'a', 'an', 'for', 'and', 'to', 'of', 'in', 'on', 'at', 'vs', 'for', 'by', 'with', 'is', 'it'}
        for word in words:
            if len(word) > 3 and word.lower() not in stop_words:
                keywords.append(word.lower())
        return keywords[:5]
    
    async def discover_all_topics(self) -> List[Dict]:
        reddit_topics = await self.scrape_reddit()
        seo_topics = await self.generate_seo_topics()
        
        all_topics = reddit_topics + seo_topics
        
        all_topics.sort(key=lambda x: (x.get('affiliation_potential', 0) * 2 + x.get('score', 0) * 0.5), reverse=True)
        
        new_topics = [t for t in all_topics if t['title'] not in self.cached_topics]
        self._save_topics([t['title'] for t in new_topics])
        
        return all_topics[:50]
