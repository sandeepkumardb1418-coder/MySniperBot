import os, requests
from datetime import datetime

CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def execute_exit_order(symbol, sec_id, qty, side, reason):
    print(f"⚡ एक्शन: {reason} -> {symbol} को क्लोज किया जा रहा है...")
    payload = {
        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
        "quantity": int(qty), "securityId": str(sec_id), "tradingSymbol": symbol, "price": 0
    }
    requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
    print(f"✅ एग्जिट आर्डर भेज दिया गया।")

def run_ai_risk_manager():
    print(f"🛡️ AI रिस्क मैनेजर चेक कर रहा है... ({datetime.now().strftime('%H:%M:%S')})")
    res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
    if res.status_code != 200: return

    positions = res.json()
    active_positions = [p for p in positions if int(float(p.get('netQty', 0))) != 0 and p.get('productType') == 'INTRADAY']

    if not active_positions:
        print("✅ इस समय कोई ओपन ट्रेड नहीं है।")
        return

    for pos in active_positions:
        symbol = pos['tradingSymbol']
        sec_id = pos['securityId']
        net_qty = int(float(pos['netQty']))
        ltp = float(pos.get('lastPrice', pos.get('ltp', 0))) 
        
        is_long = net_qty > 0
        entry_price = float(pos['buyAvg']) if is_long else float(pos['sellAvg'])
        
        if entry_price == 0: continue # सेफ्टी चेक
        
        pnl_pct = ((ltp - entry_price) / entry_price) * 100 if is_long else ((entry_price - ltp) / entry_price) * 100
        exit_side = "SELL" if is_long else "BUY"
        abs_qty = abs(net_qty)
        
        print(f"📊 {symbol} | एंट्री: ₹{entry_price:.2f} | P&L: {pnl_pct:.2f}%")

        # 1% स्टॉप लॉस या 3.5% टारगेट
        if pnl_pct <= -1.0:
            execute_exit_order(symbol, sec_id, abs_qty, exit_side, "🚨 1% Stop-Loss Hit")
        elif pnl_pct >= 3.5:
            execute_exit_order(symbol, sec_id, abs_qty, exit_side, "🎯 3.5% Target Hit")

if __name__ == "__main__":
    run_ai_risk_manager()
