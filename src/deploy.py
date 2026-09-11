import os
import json
import subprocess
import sys
from datetime import datetime
from typing import List, Dict

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class DeployBot:
    def __init__(self, config: dict):
        self.config = config
        self.deployment_config = config.get('deployment', {})
        self.site_config = config.get('site', {})
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        self.vercel_token = os.environ.get('VERCEL_TOKEN', '') or self.deployment_config.get('vercel_token', '')

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

            git_output = self._git_push(len(articles))

            vercel_output = ""
            if self.vercel_token:
                vercel_output = self._vercel_deploy()
                if not vercel_output:
                    result['error'] = 'Vercel deploy failed'
                    result['git_output'] = git_output
                    self._log_deploy(result)
                    return result
            else:
                print("  VERCEL_TOKEN not set — skipping Vercel deploy (articles are committed to git)")

            result['articles_deployed'] = len(articles)
            result['success'] = True
            result['git_output'] = git_output
            result['vercel_output'] = vercel_output

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
            ['git', 'push'],
        ]

        output = ""
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                output += f"{' '.join(cmd)}\n{result.stdout}\n{result.stderr}\n\n"
            except subprocess.TimeoutExpired:
                output += f"Command timed out: {' '.join(cmd)}\n"
            except Exception as e:
                output += f"Error: {e}\n"

        return output

    def _vercel_deploy(self) -> str:
        repo_dir = os.path.dirname(os.path.dirname(__file__))

        vercel_cli = None
        candidates = [
            os.path.expanduser('~\\AppData\\Roaming\\npm\\node_modules\\vercel\\dist\\vc.js'),
            os.path.expanduser('~\\AppData\\Roaming\\npm\\vercel.cmd'),
            'vercel',
        ]
        for candidate in candidates:
            if os.path.exists(candidate) or candidate == 'vercel':
                vercel_cli = candidate
                break

        if not vercel_cli:
            print("  Vercel CLI not found")
            return ""

        env = dict(os.environ)
        env['VERCEL_TOKEN'] = self.vercel_token

        try:
            if vercel_cli.endswith('.js'):
                node = 'C:\\Program Files\\nodejs\\node.exe'
                cmd = [node, vercel_cli, 'deploy', '--prod', '--token', self.vercel_token, '--force']
            elif vercel_cli.endswith('.cmd'):
                cmd = [vercel_cli, 'deploy', '--prod', '--token', self.vercel_token, '--force']
            else:
                cmd = ['vercel', 'deploy', '--prod', '--token', self.vercel_token, '--force']

            result = subprocess.run(
                cmd,
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            output = f"{result.stdout}\n{result.stderr}\n"
            if 'https://' in result.stdout:
                print(f"  Vercel deploy URL: {result.stdout.strip()}")
            else:
                print(f"  Vercel deploy output: {output.strip()[:300]}")
                return ""
            return output
        except Exception as e:
            print(f"  Vercel deploy error: {e}")
            return ""

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