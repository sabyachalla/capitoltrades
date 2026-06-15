import requests
import json
import os
import zipfile
import io
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://disclosures-clerk.house.gov/"
}

def fetch_house_trades():
    print("Fetching House trades...")
    trades = []

    for year in [2026, 2025]:
        url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
        print(f"Downloading {year} ZIP...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            print(f"ZIP status: {r.status_code}")
            if r.status_code != 200:
                continue

            z = zipfile.ZipFile(io.BytesIO(r.content))
            xml_files = [f for f in z.namelist() if f.endswith('.xml')]
            print(f"Found XML: {xml_files}")

            for xml_file in xml_files:
                tree = ET.parse(z.open(xml_file))
                root = tree.getroot()
                members = root.findall('.//Member')
                print(f"Members in {year}: {len(members)}")

                count = 0
                for member in members:
                    first = member.findtext('First', '').strip()
                    last = member.findtext('Last', '').strip()
                    filing_type = member.findtext('FilingType', '').strip()
                    doc_id = member.findtext('DocID', '').strip()
                    name = f"{first} {last}".strip()

                    if filing_type != 'P' or not doc_id:
                        continue

                    ptr_url = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.xml"
                    try:
                        time.sleep(0.5)
                        ptr_r = requests.get(ptr_url, headers=HEADERS, timeout=15)
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
                        count += 1
                        if count % 10 == 0:
                            print(f"  Processed {count} PTRs, {len(trades)} trades so far...")

                        # cap at 200 PTRs per year to stay within time limits
                        if count >= 200:
                            break

                    except Exception as e:
                        continue

        except Exception as e:
            print(f"Error for {year}: {e}")

    print(f"Got {len(trades)} trades total")
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
        key = t['issuer'].upper().strip()
        if not key or key == '--':
            continue
        issuer_map[key]['name'] = t['issuer']
        if t.get('ticker'):
            issuer_map[key]['ticker'] = t['ticker']
        issuer_map[key]['politicians'].add(t['politician'])
        issuer_map[key]['trades'] += 1
        if t['type'] == 'buy':
            issuer_map[key]['buys'] += 1
        elif t['type'] == 'sell':
            issuer_map[key]['sells'] += 1

    # rank by number of politicians who BOUGHT
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
