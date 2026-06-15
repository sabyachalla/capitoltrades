import requests
import json
import os
from datetime import datetime
from collections import defaultdict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_trades():
    print("Fetching Senate trades...")
    trades = []

    # Pull directly from senatestockwatcher.com API
    url = "https://senatestockwatcher.com/api/transactions/all.json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        print(f"Status code: {r.status_code}")
        r.raise_for_status()
        data = r.json()
        print(f"Raw records fetched: {len(data)}")

        for tx in data:
            name = tx.get("senator", "").strip()
            asset = tx.get("asset_description", "").strip()
            ticker = tx.get("ticker", "").strip()
            tx_type = tx.get("type", "").lower()

            if not asset or asset == "--":
                continue
            if "purchase" in tx_type:
                tx_type = "buy"
            elif "sale" in tx_type or "sell" in tx_type:
                tx_type = "sell"
            else:
                tx_type = "other"

            trades.append({
                "politician": name,
                "issuer": asset,
                "ticker": ticker if ticker != "--" else "",
                "type": tx_type
            })

    except Exception as e:
        print(f"Error: {e}")

    print(f"Got {len(trades)} trades")
    return trades

def process(trades):
    issuer_map = defaultdict(lambda: {
        "name": "",
        "ticker": "",
        "politicians": set(),
        "trades": 0,
        "buys": 0,
        "sells": 0
    })

    for t in trades:
        key = t["issuer"].upper().strip()
        if not key or key == "--":
            continue
        issuer_map[key]["name"] = t["issuer"]
        if t.get("ticker"):
            issuer_map[key]["ticker"] = t["ticker"]
        issuer_map[key]["politicians"].add(t["politician"])
        issuer_map[key]["trades"] += 1
        if t["type"] == "buy":
            issuer_map[key]["buys"] += 1
        elif t["type"] == "sell":
            issuer_map[key]["sells"] += 1

    ranked = sorted(issuer_map.values(), key=lambda x: len(x["politicians"]), reverse=True)

    return [{
        "name": item["name"],
        "ticker": item["ticker"],
        "politician_count": len(item["politicians"]),
        "politicians": list(item["politicians"]),
        "trades": item["trades"],
        "buys": item["buys"],
        "sells": item["sells"]
    } for item in ranked]

def main():
    trades = fetch_trades()
    output = process(trades)

    os.makedirs("data", exist_ok=True)
    with open("data/trades.json", "w") as f:
        json.dump({
            "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "total_trades": len(trades),
            "issuers": output
        }, f, indent=2)

    print(f"Done! {len(trades)} trades → {len(output)} companies saved.")

if __name__ == "__main__":
    main()
