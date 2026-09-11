import json
import os
import sys
from datetime import date, timedelta

from google_api import api_get, api_post

SITE = 'sc-domain:operos.de'


def fmt(n):
    return f'{n:,}'


def check_sitemaps():
    print('=' * 60)
    print('SEARCH CONSOLE - SITEMAPS')
    print('=' * 60)
    r = api_get(f'https://searchconsole.googleapis.com/webmasters/v3/sites/{SITE}/sitemaps')
    if r.status_code != 200:
        print(f'  API error {r.status_code}: {r.text[:400]}')
        return
    data = r.json().get('sitemap', [])
    if not data:
        print('  No sitemaps submitted.')
        return
    for sm in data:
        print(f"  {sm.get('path')}")
        print(f"    status: {sm.get('content', {}).get('status')}")
        print(f"    last submitted: {sm.get('content', {}).get('lastSubmitted')}")
        print(f"    last downloaded: {sm.get('content', {}).get('lastDownloaded')}")
        errors = sm.get('content', {}).get('errors')
        warnings = sm.get('content', {}).get('warnings')
        print(f"    errors: {errors}   warnings: {warnings}")


def check_sites():
    print()
    print('=' * 60)
    print('SEARCH CONSOLE - VERIFIED SITES')
    print('=' * 60)
    r = api_get('https://searchconsole.googleapis.com/webmasters/v3/sites')
    if r.status_code == 200:
        for s in r.json().get('siteEntry', []):
            print(f"  {s.get('siteUrl')}  [{s.get('permissionLevel')}]")
    else:
        print(f"  API error {r.status_code}: {r.text[:300]}")


def check_performance():
    print()
    print('=' * 60)
    print('SEARCH CONSOLE - PERFORMANCE (last 28 days)')
    print('=' * 60)
    today = date.today()
    start = (today - timedelta(days=28)).isoformat()
    end = today.isoformat()
    r = api_post(
        f'https://searchconsole.googleapis.com/webmasters/v3/sites/{SITE}/searchAnalytics/query',
        {
            'startDate': start,
            'endDate': end,
            'dimensions': ['date'],
            'rowLimit': 28,
        },
    )
    if r.status_code != 200:
        print(f'  API error {r.status_code}: {r.text[:400]}')
        return
    rows = r.json().get('rows', [])
    total_clicks = sum(int(row.get('clicks', 0)) for row in rows)
    total_imp = sum(int(row.get('impressions', 0)) for row in rows)
    total_ctr = total_clicks / total_imp if total_imp else 0
    print(f'  Total clicks (28d): {fmt(total_clicks)}')
    print(f'  Total impressions (28d): {fmt(total_imp)}')
    print(f'  Average CTR: {total_ctr:.2%}')
    if rows:
        last = rows[-1]
        print(f'  Latest day ({last["keys"][0]}): {fmt(int(last.get("clicks", 0)))} clicks, {fmt(int(last.get("impressions", 0)))} impressions')


def main():
    check_sites()
    check_sitemaps()
    check_performance()


if __name__ == '__main__':
    main()