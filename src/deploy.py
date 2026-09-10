import os
import json
import subprocess
import sys
from datetime import datetime
from typing import List, Dict

class DeployBot:
    def __init__(self, config: dict):
        self.config = config
        self.deployment_config = config.get('deployment', {})
        self.site_config = config.get('site', {})
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        
    def deploy(self, articles: List[Dict]) -> Dict:
        result = {
            'success': False,
            'articles_deployed': 0,
            'error': None,
            'deployed_at': datetime.now().isoformat()
        }
        
        try:
            from src.site_builder import SiteBuilder
            
            builder = SiteBuilder(self.config)
            build_result = builder.build_site(articles)
            print(f"Site built: {build_result}")
            
            git_result = self._git_push(len(articles))
            result['articles_deployed'] = len(articles)
            result['success'] = True
            result['git_output'] = git_result
            
        except Exception as e:
            result['error'] = str(e)
            print(f"Deploy error: {e}")
        
        self._log_deploy(result)
        return result
    
    def _git_push(self, article_count: int = 0) -> str:
        repo_dir = os.path.dirname(os.path.dirname(__file__))
        
        commit_msg = f"Auto-deploy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {article_count} articles"
        
        commands = [
            ['git', 'add', '.'],
            ['git', 'commit', '-m', commit_msg],
        ]
        
        output = ""
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                output += f"{' '.join(cmd)}\n{result.stdout}\n{result.stderr}\n\n"
            except subprocess.TimeoutExpired:
                output += f"Command timed out: {' '.join(cmd)}\n"
            except Exception as e:
                output += f"Error: {e}\n"
        
        return output
    
    def _log_deploy(self, result: Dict):
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'deploy_history.json')
        
        try:
            with open(log_file, 'r') as f:
                history = json.load(f)
        except:
            history = {'deploys': []}
        
        history['deploys'].append(result)
        
        with open(log_file, 'w') as f:
            json.dump(history, f, indent=2)
