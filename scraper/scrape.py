import requests
import json
import os
import zipfile
import io
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict

def fetch_house_trades():
    print("Fetching House disclosure index...")
    trades = []
    
    for year in [2026, 2025]:
        url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
        print(f"Downloading {year} ZIP...")
        try:
            r = requests.get(url, timeout=60)
            print(f"Status: {r.status_code}, Size: {len(r.content)} bytes")
            if r.status_code != 200:
                continue

            z = zipfile.ZipFile(io.BytesIO(r.content))
            xml_files = [f for f in z.namelist() if f.endswith('.xml')]
            print(f"XML files in ZIP: {xml_files}")

            for xml_file in xml_files:
                tree = ET.parse(z.open(xml_file))
                root = tree.getroot()
                
                for member in root.findall('.//Member'):
                    prefix = member.findtext('Prefix', '')
                    first = member.findtext('First', '')
                    last = member.findtext('Last', '')
                    filing_type = member.findtext('FilingType', '')
                    state = member.findtext('StateDst', '')
                    
                    name = f"{prefix} {first} {last}".strip()
                    
                    # P = Periodic Transaction Report (stock trades)
                    if 'P' in filing_type:
                        trades.append({
                            "politician": name,
                            "issuer": f"[House PTR - {state}]",
                            "ticker": "",
                            "type": "other",
                            "year": year
                        })

        except Exception as e:
            print(f"Error for {year}: {e}")

    print(f"Got {len(trades)} House PTR filings")
    return trades

def fetch_senate_trades():
    """Pull from the Senate EFD search - returns filing list"""
    print("Fetching Senate trades...")
    trades = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://efdsearch.senate.gov/search/home/"
    }
    
    session = requests.Session()
    
    # Step 1: accept agreement
    try:
        session.get("https://efdsearch.senate.gov/search/home/", timeout=15)
        session.post(
            "https://efdsearch.senate.gov/search/home/",
            data={"prohibition_agreement": "1"},
            headers=headers,
            timeout=15
        )
    except Exception as e:
        print(f"Senate session error: {e}")
        return trades

    # Step 2: search for PTRs
    try:
        payload = {
            "draw": "1",
            "start": "0", 
            "length": "100",
            "report_types": "[11]",
            "submitted_start_date": "01/01/2025 00:00:00",
            "submitted_end_date": "",
            "candidate_state": "",
            "senator_state": "",
            "office_id": "",
            "first_name": "",
            "last_name": "",
            "action": "search",
            "filer_type": "1"
        }
        
        r = session.post(
            "https://efdsearch.senate.gov/search/report/data/",
            data=payload,
            headers=headers,
            timeout=20
        )
        print(f"Senate status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            records = data.get("data", [])
            print(f"Senate records: {len(records)}")
            for rec in records:
                if len(rec) >= 2:
                    name = f"{rec[0]} {rec[1]}".strip()
                    trades.append({
                        "politician": name,
                        "issuer": "Senate PTR Filing",
                        "ticker": "",
                        "type": "other"
                    })
    except Exception as e:
        print(f"Senate search error: {e}")

    return trades

def process(trades):
    # For now count PTR filings per politician
    pol_map = defaultdict(int)
    for t in trades:
        pol_map[t["politician"]] += 1

    # Return as issuer-style output showing most active traders
    output = []
    for pol, count in sorted(pol_map.items(), key=lambda x: x[1], reverse=True):
        output.append({
            "name": pol,
            "ticker": "",
            "politician_count": 1,
            "politicians": [pol],
            "trades": count,
            "buys": 0,
            "sells": 0
        })
    
    return output

def main():
    house = fetch_house_trades()
    senate = fetch_senate_trades()
    all_trades = house + senate

    output = process(all_trades)

    os.makedirs("data", exist_ok=True)
    with open("data/trades.json", "w") as f:
        json.dump({
            "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "total_trades": len(all_trades),
            "issuers": output
        }, f, indent=2)

    print(f"Done! {len(all_trades)} filings → {len(output)} politicians saved.")

if __name__ == "__main__":
    main()
