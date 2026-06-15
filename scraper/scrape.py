import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def scrape_page(page_num):
    url = f"https://www.capitoltrades.com/trades?pageSize=96&page={page_num}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tbody tr")
        trades = []
        for row in rows:
            cols = row.select("td")
            if len(cols) < 7:
                continue
            politician = cols[0].get_text(strip=True)
            issuer_el = cols[1].select_one("h3, .issuer-name, a")
            issuer = issuer_el.get_text(strip=True) if issuer_el else cols[1].get_text(strip=True)
            ticker_el = cols[1].select_one(".issuer-ticker, span")
            ticker = ticker_el.get_text(strip=True) if ticker_el else ""
            tx_type = cols[5].get_text(strip=True).lower()
            if "buy" in tx_type:
                tx_type = "buy"
            elif "sell" in tx_type:
                tx_type = "sell"
            else:
                tx_type = "other"
            trades.append({
                "politician": politician,
                "issuer": issuer,
                "ticker": ticker,
                "type": tx_type
            })
        return trades
    except Exception as e:
        print(f"Error on page {page_num}: {e}")
        return []

def main():
    all_trades = []
    for page in range(1, 11):
        print(f"Scraping page {page}...")
        trades = scrape_page(page)
        if not trades:
            break
        all_trades.extend(trades)
        time.sleep(2)

    issuer_map = {}
    for t in all_trades:
        key = t["issuer"].upper().strip()
        if not key:
            continue
        if key not in issuer_map:
            issuer_map[key] = {
                "name": t["issuer"],
                "ticker": t["ticker"],
                "politicians": set(),
                "trades": 0,
                "buys": 0,
                "sells": 0
            }
        issuer_map[key]["politicians"].add(t["politician"])
        issuer_map[key]["trades"] += 1
        if t["type"] == "buy":
            issuer_map[key]["buys"] += 1
        elif t["type"] == "sell":
            issuer_map[key]["sells"] += 1

    ranked = sorted(issuer_map.values(), key=lambda x: len(x["politicians"]), reverse=True)
    output = []
    for item in ranked:
        output.append({
            "name": item["name"],
            "ticker": item["ticker"],
            "politician_count": len(item["politicians"]),
            "politicians": list(item["politicians"]),
            "trades": item["trades"],
            "buys": item["buys"],
            "sells": item["sells"]
        })

    os.makedirs("data", exist_ok=True)
    with open("data/trades.json", "w") as f:
        json.dump({
            "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "total_trades": len(all_trades),
            "issuers": output
        }, f, indent=2)

    print(f"Done! {len(all_trades)} trades, {len(output)} companies.")

if __name__ == "__main__":
    main()
