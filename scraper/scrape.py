import requests
import json
import os
import zipfile
import io
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict

def fetch_house_trades():
    print("Fetching House trades...")
    trades = []

    for year in [2026, 2025]:
        url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
        print(f"Downloading {year} ZIP...")
        try:
            r = requests.get(url, timeout=60)
            if r.status_code != 200:
                print(f"Failed: {r.status_code}")
                continue

            z = zipfile.ZipFile(io.BytesIO(r.content))
            xml_files = [f for f in z.namelist() if f.endswith('.xml')]

            for xml_file in xml_files:
                tree = ET.parse(z.open(xml_file))
                root = tree.getroot()

                for member in root.findall('.//Member'):
                    first = member.findtext('First', '').strip()
                    last = member.findtext('Last', '').strip()
                    filing_type = member.findtext('FilingType', '').strip()
                    doc_id = member.findtext('DocID', '').strip()
                    name = f"{first} {last}".strip()

                    # Only PTR filings (P = periodic transaction report)
                    if filing_type != 'P' or not doc_id:
                        continue

                    # Fetch the individual XML for this PTR
                    ptr_url = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.xml"
                    try:
                        ptr_r = requests.get(ptr_url, timeout=10)
                        if ptr_r.status_code != 200:
                            continue

                        ptr_tree = ET.fromstring(ptr_r.content)

                        for tx in ptr_tree.findall('.//Transaction'):
                            asset = tx.findtext('AssetName', '').strip()
                            ticker = tx.findtext('Ticker', '').strip()
                            tx_type = tx.findtext('Type', '').lower()

                            if not asset or asset == '--':
                                continue
                            if 'purchase' in tx_type or 'buy' in tx_type:
                                tx_type = 'buy'
                            elif 'sale' in tx_type or 'sell' in tx_type:
                                tx_type = 'sell'
                            else:
                                tx_type = 'other'

                            trades.append({
                                'politician': name,
                                'issuer': asset,
                                'ticker': ticker,
                                'type': tx_type
                            })

                    except Exception as e:
                        continue

        except Exception as e:
            print(f"Error for {year}: {e}")

    print(f"Got {len(trades)} trades")
    return trades

def process(trades):
    issuer_map = defaultdict(lambda: {
        'name': '',
        'ticker': '',
        'politicians': set(),
        'trades': 0,
        'buys': 0,
        'sells': 0
    })

    for t in trades:
        # Only count buys for ranking
        if t['type'] != 'buy':
            continue
        key = t['issuer'].upper().strip()
        if not key or key == '--':
            continue
        issuer_map[key]['name'] = t['issuer']
        if t.get('ticker'):
            issuer_map[key]['ticker'] = t['ticker']
        issuer_map[key]['politicians'].add(t['politician'])
        issuer_map[key]['trades'] += 1
        issuer_map[key]['buys'] += 1

    ranked = sorted(issuer_map.values(), key=lambda x: len(x['politicians']), reverse=True)

    return [{
        'name': item['name'],
        'ticker': item['ticker'],
        'politician_count': len(item['politicians']),
        'politicians': list(item['politicians']),
        'trades': item['trades'],
        'buys': item['buys'],
        'sells': item['sells']
    } for item in ranked]

def main():
    trades = fetch_house_trades()
    output = process(trades)

    os.makedirs('data', exist_ok=True)
    with open('data/trades.json', 'w') as f:
        json.dump({
            'updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            'total_trades': len(trades),
            'issuers': output
        }, f, indent=2)

    print(f"Done! {len(trades)} trades → {len(output)} companies saved.")

if __name__ == '__main__':
    main()
