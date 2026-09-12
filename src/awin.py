import json
import os
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class Awin:
    """Awin affiliate network client (publisher side).

    Uses the publisher API to list programmes and resolve their
    click-through (affiliate) URLs. Results are cached to data/ so the
    engine doesn't hit the API on every article generation.
    """

    BASE = 'https://api.awin.com'

    def __init__(self, config: dict):
        awin = config.get('awin', {})
        self.enabled = awin.get('enabled', False)
        self.api_key = os.environ.get('AWIN_API_KEY', '') or awin.get('api_key', '')
        self.publisher_id = awin.get('publisher_id', '')
        self.cache_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), awin.get('cache_file', 'data/awin_programmes.json')
        )
        self._cache = self._load_cache()

    def _load_cache(self):
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # expire cache after 24h
            if time.time() - data.get('_fetched', 0) < 86400:
                return data
        except Exception:
            pass
        return {'programmes': []}

    def _save_cache(self, programmes):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump({'programmes': programmes, '_fetched': time.time()}, f, ensure_ascii=False)

    def _headers(self):
        return {'Authorization': f'Bearer {self.api_key}'}

    def get_account(self):
        r = requests.get(f'{self.BASE}/accounts', headers=self._headers(), timeout=30)
        if r.status_code != 200:
            return None
        data = r.json()
        for acc in data.get('accounts', []):
            if acc.get('accountType') == 'publisher':
                return acc
        return None

    def programmes(self, refresh: bool = False):
        if self._cache.get('programmes') and not refresh:
            return self._cache['programmes']
        r = requests.get(
            f'{self.BASE}/publishers/{self.publisher_id}/programmes',
            headers=self._headers(),
            timeout=120,
        )
        if r.status_code != 200:
            return self._cache.get('programmes', [])
        programmes = r.json()
        self._save_cache(programmes)
        self._cache['programmes'] = programmes
        return programmes

    def search(self, keyword: str, limit: int = 5, active_only: bool = True):
        """Return programmes whose name contains keyword."""
        kw = keyword.lower()
        results = []
        for p in self.programmes():
            if active_only and p.get('status', '').lower() != 'active':
                continue
            if kw in p.get('name', '').lower():
                results.append(p)
            if len(results) >= limit:
                break
        return results

    def affiliate_url(self, programme) -> str:
        return programme.get('clickThroughUrl', '')

    def tech_retail_links(self):
        """German electronics retailers to pair with Amazon on product
        buyers guides. Prioritises German (DE) programmes."""
        targets = ['notebooksbilliger DE/AT', 'cyberport DE', 'Computeruniverse DE']
        found = {}
        for name in targets:
            matches = self.search(name, limit=1)
            if matches:
                found[matches[0]['name']] = matches[0].get('clickThroughUrl', '')
        return found