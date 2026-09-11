from google_api import api_get

BASE = 'https://adsense.googleapis.com/v2'


def fmt(n):
    return f'{n:,}'


def check_accounts():
    print('=' * 60)
    print('ADSENSE - ACCOUNTS')
    print('=' * 60)
    r = api_get(f'{BASE}/accounts')
    if r.status_code != 200:
        print(f'  API error {r.status_code}: {r.text[:400]}')
        return
    accounts = r.json().get('accounts', [])
    if not accounts:
        print('  No AdSense accounts found.')
        return
    for acc in accounts:
        name = acc['name']
        print(f"  Account: {acc.get('displayName')}  [{name}]")
        print(f"    state: {acc.get('state')}")
        print(f"    pending tasks: {acc.get('pendingTasks')}")
        print(f"    time zone: {acc.get('timeZone')}")
        check_ad_clients(name)
        try:
            check_earnings(name)
        except Exception as e:
            print(f'    (earnings report skipped: {e})')


def check_ad_clients(account):
    print(f'  --- Ad clients ---')
    r = api_get(f'{BASE}/{account}/adclients')
    if r.status_code != 200:
        print(f'    API error {r.status_code}: {r.text[:300]}')
        return
    clients = r.json().get('adClients', [])
    if not clients:
        print('    No ad clients (account may still be in review).')
        return
    for c in clients:
        print(f"    product: {c.get('productCode')}  state: {c.get('state')}")
        print(f"      reporting ID: {c.get('reportingDimensionId')}")
        if c.get('state') == 'STATE_ENABLED':
            check_ad_units(account, c['name'])


def check_ad_units(account, ad_client):
    r = api_get(f'{BASE}/{ad_client}/adunits')
    if r.status_code != 200:
        return
    units = r.json().get('adUnits', [])
    print(f'    Ad units ({len(units)}):')
    for u in units:
        print(f"      {u.get('name')}  state={u.get('state')}  code={u.get('code')}")


def check_earnings(account):
    print()
    print(f'  --- Earnings report (last 30 days) ---')
    from datetime import date, timedelta
    today = date.today()
    start = today - timedelta(days=30)

    def d(p):
        return {'startDate.year': str(start.year), 'startDate.month': str(start.month),
                'startDate.day': str(start.day), 'endDate.year': str(today.year),
                'endDate.month': str(today.month), 'endDate.day': str(today.day)}

    params = {
        **d(True),
        'dimensions': 'DATE',
        'metrics': 'ESTIMATED_EARNINGS',
        'dateRange': 'LAST_30_DAYS',
    }
    r = api_get(f'{BASE}/{account}/reports:generate', params=params)
    if r.status_code == 200:
        data = r.json()
        total = 0.0
        clicks = 0
        for row in data.get('rows', []):
            cells = row.get('cells', [])
            if len(cells) >= 2:
                total += float(cells[0].get('value', 0))
                clicks += int(cells[1].get('value', 0))
        print(f'    Estimated earnings (30d): EUR {total:.2f}')
        print(f'    Clicks (30d): {fmt(clicks)}')
    else:
        print(f'    API error {r.status_code}: {r.text[:400]}')


def main():
    check_accounts()


if __name__ == '__main__':
    main()