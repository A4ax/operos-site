import os
import json
import subprocess
import sys
import time
from datetime import datetime
from typing import List, Dict

import requests

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
                if self._deploy_due():
                    vercel_output = self._vercel_deploy()
                    if not vercel_output:
                        result['error'] = 'Vercel deploy failed'
                        result['git_output'] = git_output
                        self._log_deploy(result)
                        return result
                    self._mark_deployed()
                else:
                    vercel_output = "Skipped (within deploy interval)"
                    print(f"  {vercel_output}")
            else:
                print("  VERCEL_TOKEN not set — skipping Vercel deploy (articles are committed to git)")

            result['articles_deployed'] = len(articles)
            result['success'] = True
            result['git_output'] = git_output
            result['vercel_output'] = vercel_output

            indexnow_output = self._indexnow_submit()
            result['indexnow_output'] = indexnow_output

            social_output = self._social_share(articles)
            result['social_output'] = social_output

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
                cmd = [node, vercel_cli, 'deploy', '--prod', '--token', self.vercel_token, '--force', '--archive=tgz']
            elif vercel_cli.endswith('.cmd'):
                cmd = [vercel_cli, 'deploy', '--prod', '--token', self.vercel_token, '--force', '--archive=tgz']
            else:
                cmd = ['vercel', 'deploy', '--prod', '--token', self.vercel_token, '--force', '--archive=tgz']

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

    def _deploy_interval_minutes(self) -> int:
        return int(self.config.get('scheduler', {}).get('deploy_interval_minutes', 60))

    def _state_file(self):
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'deploy_state.json')

    def _deploy_due(self) -> bool:
        try:
            with open(self._state_file(), 'r') as f:
                state = json.load(f)
            last = state.get('last_deploy_epoch', 0)
        except Exception:
            last = 0
        interval = self._deploy_interval_minutes() * 60
        return (time.time() - last) >= interval

    def _mark_deployed(self):
        with open(self._state_file(), 'w') as f:
            json.dump({'last_deploy_epoch': time.time()}, f)

    def _indexnow_submit(self) -> str:
        """Submit newest article URLs to IndexNow (instant Bing/Yandex/Seznam
        indexing)."""
        try:
            indexnow = self.config.get('indexnow', {})
            if not indexnow.get('enabled'):
                return "IndexNow disabled"
            key = indexnow.get('key', '')
            domain = self.site_config.get('domain', 'operos.de')
            if not key:
                return "IndexNow: no key configured"

            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            articles_json = os.path.join(data_dir, 'articles.json')
            with open(articles_json, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            articles.sort(key=lambda a: a.get('published_at', ''), reverse=True)

            urls = [f'https://{domain}/']
            for a in articles[:50]:
                slug = a.get('slug')
                if slug:
                    urls.append(f'https://{domain}/posts/{slug}.html')
            urls.append(f'https://{domain}/sitemap.xml')

            payload = {
                'host': domain,
                'key': key,
                'keyLocation': f'https://{domain}/{key}.txt',
                'urlList': urls,
            }
            r = requests.post('https://api.indexnow.org/indexnow', json=payload, timeout=30)
            if r.status_code in (200, 202):
                return f"IndexNow: submitted {len(urls)} URLs (HTTP {r.status_code})"
            return f"IndexNow: HTTP {r.status_code} {r.text[:200]}"
        except Exception as e:
            return f"IndexNow: error {e}"

    def _social_share(self, articles: List[Dict]) -> str:
        """Share the newest article once (only when it changes)."""
        try:
            state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'social_state.json')
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
            except Exception:
                state = {}
            if not articles:
                return 'Social: no articles'
            newest = max(articles, key=lambda a: a.get('published_at', ''))
            slug = newest.get('slug', '')
            if state.get('last_shared') == slug:
                return 'Social: already shared'
            url = f'https://{self.site_config.get("domain", "operos.de")}/posts/{slug}.html'
            title = newest.get('title', slug)
            image = newest.get('image', '')
            script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'social_share.py')
            result = subprocess.run(
                [sys.executable, script, url, title, image],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=os.path.dirname(os.path.dirname(__file__)),
            )
            state['last_shared'] = slug
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            out = (result.stdout or '') + (result.stderr or '')
            return f"Social: {out.strip()[:400]}"
        except Exception as e:
            return f'Social: error {e}'

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