import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class AmazonAssociates:
    """Amazon Product Advertising API 5 client with real ASIN lookups.

    Falls back to keyword search links when PA-API credentials are not
    configured, so the pipeline stays fully automatic in both modes.
    """

    HOST = 'webservices.amazon.de'
    REGION = 'eu-west-1'
    SERVICE = 'ProductAdvertisingAPI'
    ENDPOINT = f'https://{HOST}/paapi5/searchitems'

    def __init__(self, config: dict):
        amazon = config.get('amazon', {})
        self.enabled = amazon.get('enabled', False)
        self.partner_tag = amazon.get('tracking_id', 'operos-21')
        self.marketplace = amazon.get('marketplace', 'www.amazon.de')
        self.domain = amazon.get('domain', 'amazon.de')
        self.search_index = amazon.get('search_index', 'Electronics')
        self.max_links = amazon.get('links_per_article', 2)

        self.access_key = os.environ.get('AMAZON_PAAPI_ACCESS_KEY', '') or amazon.get('paapi_access_key', '')
        self.secret_key = os.environ.get('AMAZON_PAAPI_SECRET_KEY', '') or amazon.get('paapi_secret_key', '')
        self.has_credentials = bool(self.access_key and self.secret_key)

        self._cache = self._load_cache()

    def _load_cache(self) -> Dict:
        cache_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'data', 'amazon_products.json'
        )
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self):
        cache_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'data', 'amazon_products.json'
        )
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Signing (AWS Signature Version 4)
    # ------------------------------------------------------------------
    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def _get_signature_key(self, secret: str, date_stamp: str) -> bytes:
        k_date = self._sign(('AWS4' + secret).encode('utf-8'), date_stamp)
        k_region = self._sign(k_date, self.REGION)
        k_service = self._sign(k_region, self.SERVICE)
        return self._sign(k_service, 'aws4_request')

    def _build_headers(self, payload: str) -> Dict[str, str]:
        amz_date = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        date_stamp = amz_date[:8]
        content_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

        canonical_uri = '/paapi5/searchitems'
        canonical_querystring = ''
        canonical_headers = (
            f'content-encoding:amz-1-0\n'
            f'host:{self.HOST}\n'
            f'x-amz-content-sha256:{content_hash}\n'
            f'x-amz-date:{amz_date}\n'
        )
        signed_headers = 'content-encoding;host;x-amz-content-sha256;x-amz-date'

        canonical_request = (
            f'POST\n{canonical_uri}\n{canonical_querystring}\n'
            f'{canonical_headers}\n{signed_headers}\n{content_hash}'
        )

        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{self.REGION}/{self.SERVICE}/aws4_request'
        string_to_sign = (
            f'{algorithm}\n{amz_date}\n{credential_scope}\n'
            + hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        )

        signing_key = self._get_signature_key(self.secret_key, date_stamp)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        authorization_header = (
            f'{algorithm} Credential={self.access_key}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, Signature={signature}'
        )

        return {
            'Content-Type': 'application/json; charset=UTF-8',
            'Content-Encoding': 'amz-1-0',
            'Host': self.HOST,
            'X-Amz-Date': amz_date,
            'X-Amz-Content-Sha256': content_hash,
            'Authorization': authorization_header,
            'User-Agent': 'OperosContentEngine/1.0 (+https://operos.de)',
        }

    # ------------------------------------------------------------------
    # Product lookup
    # ------------------------------------------------------------------
    def search_products(self, keyword: str, max_items: int = 2) -> List[Dict]:
        """Fetch real products for a keyword. Priority: PA-API (when unlocked),
        then Amazon.de mobile-search scraping for real ASINs, then keyword
        search links as a last-resort fallback."""
        keyword = keyword.strip()
        if not keyword:
            return []

        if keyword in self._cache:
            return self._cache[keyword][:max_items]

        results = []
        if self.has_credentials:
            try:
                results = self._paapi_search(keyword, max_items)
            except Exception as e:
                print(f"  [amazon] PA-API error for '{keyword}': {e}")

        if not results:
            results = self._scrape_asins(keyword, max_items)

        if not results:
            results = self._keyword_links(keyword, max_items)

        if results:
            self._cache[keyword] = results
            self._save_cache()

        return results[:max_items]

    def _scrape_asins(self, keyword: str, max_items: int = 2) -> List[Dict]:
        """Resolve real ASINs by scraping the Amazon.de mobile search page.
        Returns product dicts with /dp/<ASIN>?tag=... URLs. Empty on failure."""
        # Polite rate-limit: at least ~1.5s between scrape requests
        now = time.time()
        gap = now - getattr(self, '_last_scrape', 0)
        if gap < 1.5:
            time.sleep(1.5 - gap)
        self._last_scrape = time.time()

        url = f'https://www.amazon.de/gp/aw/s/?k={urllib.parse.quote(keyword)}'
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
                'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 '
                'Mobile/15E148 Safari/604.1'
            ),
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive',
        }
        try:
            resp = requests.get(url, headers=headers, timeout=25)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, 'html.parser')
            products = []
            seen = set()
            for div in soup.select('div[data-asin]'):
                asin = div.get('data-asin', '').strip()
                if not re.fullmatch(r'[A-Z0-9]{10}', asin):
                    continue
                if asin in seen:
                    continue
                seen.add(asin)
                h2 = div.select_one('h2') or div.select_one('h2 span')
                title = h2.get_text(strip=True) if h2 else keyword
                img = div.select_one('img')
                image = ''
                if img:
                    image = img.get('src') or img.get('data-src') or ''
                products.append({
                    'asin': asin,
                    'title': title,
                    'url': f'https://{self.domain}/dp/{asin}?tag={self.partner_tag}',
                    'image': self.resize_image(image, 800),
                    'price': None,
                    'source': 'amazon-scrape',
                })
                if len(products) >= max_items:
                    break
            return products
        except Exception as e:
            print(f"  [amazon] scrape error for '{keyword}': {e}")
            return []

    def _paapi_search(self, keyword: str, max_items: int) -> List[Dict]:
        payload = json.dumps({
            'Keywords': keyword,
            'SearchIndex': self.search_index,
            'ItemCount': max_items,
            'PartnerTag': self.partner_tag,
            'PartnerType': 'Associates',
            'Marketplace': self.marketplace,
            'Resources': [
                'ItemInfo.Title',
                'ItemInfo.ByLineInfo',
                'Offers.Listings.Price',
                'Offers.Summaries.LowestPrice',
            ],
        })

        request = urllib.request.Request(
            self.ENDPOINT,
            data=payload.encode('utf-8'),
            headers=self._build_headers(payload),
            method='POST',
        )

        with urllib.request.urlopen(request, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        items = (data.get('SearchResult') or {}).get('Items', []) or []
        products = []
        for item in items:
            asin = item.get('ASIN')
            if not asin:
                continue
            title = (((item.get('ItemInfo') or {}).get('Title') or {}).get('DisplayValue')) or keyword
            price = None
            offers = item.get('Offers') or {}
            listings = (offers.get('Listings') or [])
            if listings:
                price = ((listings[0].get('Price') or {}).get('DisplayAmount'))
            if not price:
                summary = (offers.get('Summaries') or [])
                if summary:
                    price = (summary[0].get('LowestPrice') or {}).get('DisplayAmount')
            products.append({
                'asin': asin,
                'title': title,
                'url': f'https://{self.domain}/dp/{asin}?tag={self.partner_tag}',
                'price': price,
                'source': 'amazon-paapi',
            })
        return products

    def _keyword_links(self, keyword: str, max_items: int) -> List[Dict]:
        """Fallback: Amazon keyword-search links with the tracking tag."""
        query = urllib.parse.urlencode({'k': keyword, 'tag': self.partner_tag})
        return [{
            'asin': None,
            'title': keyword,
            'url': f'https://{self.domain}/s?{query}',
            'price': None,
            'source': 'amazon-keyword',
        }] * max_items

    # ------------------------------------------------------------------
    # Link text helpers
    # ------------------------------------------------------------------
    def resize_image(self, url: str, size: int = 800) -> str:
        """Rebuild an Amazon product image URL at a requested size."""
        if not url:
            return ''
        m = re.search(r'/images/I/(.+?)\._', url)
        if not m:
            return url
        image_id = m.group(1)
        return f'https://m.media-amazon.com/images/I/{image_id}._SL{size}_.jpg'

    def build_link_text(self, product: Dict) -> str:
        if product.get('price'):
            return f"Check price on Amazon — {product['price']}"
        if product.get('asin'):
            return f"{product.get('title', 'Product')} on Amazon"
        return f"Find {product.get('title', 'this product')} on Amazon"