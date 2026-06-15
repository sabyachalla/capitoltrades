import requests
import json
import os
from datetime import datetime
from collections import defaultdict

API_KEY = os.environ.get("FMP_API_KEY", "")

def fetch_trades():
    trades = []

    # Senate trades
    print("Fetching Senate trades...")
    url = f"https://financialmodelingprep.com/api/v4/senate-trading?apikey={API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        print(f"Senate status: {r.status_code}")
        data = r.json()
        print(f"Senate records: {len(data)}")
        for tx in data:
            tx_type = tx.get("type", "").lower()
            if "purchase" in tx_type or "buy" in tx_type:
                tx_type = "buy"
            elif "sale" in tx_type or "sell" in tx_type:
                tx_type = "sell"
            else:
                tx_type = "other"
            trades.append({
                "politician": tx.get("senator", ""),
                "issuer": tx.get("assetDescription", ""),
                "ticker": tx.get("ticker", ""),
                "type": tx_type
            })
    except Exception as e:
        print(f"Senate error: {e}")

    # House trades
    print("Fetching House trades...")
    url = f"https://financialmodelingprep.com/api/v4/senate-disclosure?apikey={API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        print(f"House status: {r.status_code}")
        data = r.json()
        print(f"House records: {len(data)}")
        for tx in data:
            tx_type = tx.get("type", "").lower()
            if "purchase" in tx_type or "buy" in tx_type:
                tx_type = "buy"
            elif "sale" in tx_type or "sell" in tx_type:
                tx_type = "sell"
            else:
                tx_type = "other"
            trades.append({
                "politician": tx.get("representative", ""),
                "issuer": tx.get("assetDescription", ""),
                "ticker": tx.get("ticker", ""),
                "type": tx_type
            })
    except Exception as e:
        print(f"House error: {e}")

    print(f"Total trades: {len(trades)}")
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
