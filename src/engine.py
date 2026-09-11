import asyncio
import json
import os
import time
import sys
from datetime import datetime
from typing import List, Dict

from src.discovery import TopicDiscovery
from src.generator import ContentGenerator
from src.site_builder import SiteBuilder
from src.deploy import DeployBot

class ContentEngine:
    def __init__(self, config_path: str = None):
        if config_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, 'config', 'settings.json')
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.discovery = TopicDiscovery(self.config)
        self.generator = ContentGenerator(self.config)
        self.scheduler_config = self.config.get('scheduler', {})
        self.max_total = self.scheduler_config.get('max_total_articles', 2000)
        
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self._load_state()
    
    def _load_state(self):
        state_file = os.path.join(self.data_dir, 'state.json')
        try:
            with open(state_file, 'r') as f:
                self.state = json.load(f)
        except:
            self.state = {
                'total_articles_generated': 0,
                'last_run': None,
                'total_deployed': 0,
                'errors': 0
            }
    
    def _save_state(self):
        state_file = os.path.join(self.data_dir, 'state.json')
        with open(state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    async def run_cycle(self) -> Dict:
        print(f"\n{'='*60}")
        print(f"Content Engine Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        cycle_result = {
            'timestamp': datetime.now().isoformat(),
            'steps': {}
        }
        
        try:
            # Step 1: Discover topics
            print("[1/4] Discovering topics...")
            topics = await self.discovery.discover_all_topics()
            cycle_result['steps']['topics_discovered'] = len(topics)
            print(f"  Found {len(topics)} topics")
            
            if not topics:
                print("  No new topics found. Exiting cycle.")
                return cycle_result
            
            # Step 2: Generate content - generate more on first run
            print("[2/4] Generating content...")
            max_articles = self.scheduler_config.get('max_articles_per_run', 5)
            
            # Check if this is first run (no articles.json yet)
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            articles_json = os.path.join(data_dir, 'articles.json')
            is_first_run = not os.path.exists(articles_json)
            
            if is_first_run:
                max_articles = 50  # Generate 50 articles on first run

            # Bias toward Amazon product (buyers guide) articles: ~2/3 of each batch
            product_topics = [t for t in topics if t.get('topic_type') == 'amazon_product']
            saas_topics = [t for t in topics if t.get('topic_type') != 'amazon_product']
            target_product = max(1, int(max_articles * 0.66))
            selected = product_topics[:target_product] + saas_topics[:max_articles - target_product]
            if not selected:
                selected = topics[:max_articles]

            articles = []
            
            for topic in selected[:max_articles]:
                try:
                    article = self.generator.generate_article(topic)
                    articles.append(article)
                    print(f"  Generated: {article['title']} ({article['word_count']} words)")
                except Exception as e:
                    print(f"  Error generating article: {e}")
                    self.state['errors'] = self.state.get('errors', 0) + 1
            
            cycle_result['steps']['articles_generated'] = len(articles)
            print(f"  Generated {len(articles)} articles")
            
            if not articles:
                print("  No articles generated. Exiting cycle.")
                return cycle_result
            
            # Step 3: Build site
            print("[3/4] Building site...")
            builder = SiteBuilder(self.config)
            build_result = builder.build_site(articles)
            cycle_result['steps']['build_result'] = build_result
            print(f"  {build_result}")
            
            # Step 4: Deploy
            print("[4/4] Deploying...")
            deployer = DeployBot(self.config)
            deploy_result = deployer.deploy(articles)
            cycle_result['steps']['deploy'] = {
                'success': deploy_result['success'],
                'articles': deploy_result['articles_deployed']
            }
            
            if deploy_result['success']:
                self.state['total_articles_generated'] += len(articles)
                self.state['total_deployed'] += len(articles)
                self.state['last_run'] = datetime.now().isoformat()
                self._save_state()
                print(f"  Deployed successfully! Total articles: {self.state['total_deployed']}")
            else:
                print(f"  Deploy failed: {deploy_result.get('error', 'Unknown error')}")
            
            print(f"\nCycle complete. Articles this run: {len(articles)}")
            
        except Exception as e:
            print(f"\nCycle error: {e}")
            import traceback
            traceback.print_exc()
            cycle_result['steps']['error'] = str(e)
            self.state['errors'] = self.state.get('errors', 0) + 1
            self._save_state()
        
        return cycle_result
    
    def run_scheduled(self, interval_minutes: int = None):
        if interval_minutes is None:
            interval_minutes = self.scheduler_config.get('run_every_minutes', 10)
        
        print(f"Content Engine starting...")
        print(f"Running every {interval_minutes} minutes")
        print(f"Max articles: {self.max_total}")
        print(f"Press Ctrl+C to stop\n")
        
        while True:
            try:
                asyncio.run(self.run_cycle())
            except Exception as e:
                print(f"Fatal error: {e}")
            
            print(f"\nNext run in {interval_minutes} minutes...")
            print(f"Total articles generated: {self.state.get('total_articles_generated', 0)}")
            print(f"Total deployed: {self.state.get('total_deployed', 0)}")
            print(f"Errors: {self.state.get('errors', 0)}")
            
            time.sleep(interval_minutes * 60)


async def main():
    engine = ContentEngine()
    
    # Single run mode (use -s for scheduled)
    if len(sys.argv) > 1 and sys.argv[1] == '-s':
        engine.run_scheduled()
    else:
        result = await engine.run_cycle()
        print(f"\nFinal result: {json.dumps(result, indent=2)}")


if __name__ == '__main__':
    asyncio.run(main())
