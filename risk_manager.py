import os, requests
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def execute_exit_order(symbol, sec_id, qty, side, reason):
    """पोजीशन को क्लोज करने का अचूक फंक्शन"""
    print(f"⚡ एक्शन: {reason} -> {symbol} को क्लोज किया जा रहा है...")
    payload = {
        "dhanClientId": CLIENT_ID,
        "transactionType": side,
        "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY",
        "orderType": "MARKET",
        "validity": "DAY",
        "quantity": int(qty),
        "securityId": str(sec_id),
        "tradingSymbol": symbol,
        "price": 0
    }
    try:
        res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
        if res.status_code in [200, 201]:
            print(f"✅ एग्जिट सफल! {symbol} की पोजीशन काट दी गई है।")
        else:
            print(f"❌ एग्जिट एरर: {res.text}")
    except Exception as e:
        print(f"❌ सिस्टम एरर: {e}")

def run_ai_risk_manager():
    print(f"🛡️ AI रिस्क मैनेजर सक्रिय... ({datetime.now().strftime('%H:%M:%S')})")
    
    # धन (Dhan) से आपकी चल रही पोजीशन मंगाना
    res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
    if res.status_code != 200:
        print("❌ पोजीशन डेटा नहीं मिला।")
        return

    positions = res.json()
    # सिर्फ ओपन इंट्राडे पोजीशन छांटना
    active_positions = [p for p in positions if int(p.get('netQty', 0)) != 0 and p.get('productType') == 'INTRADAY']

    if not active_positions:
        print("✅ इस समय कोई ओपन ट्रेड नहीं है।")
        return

    for pos in active_positions:
        symbol = pos['tradingSymbol']
        sec_id = pos['securityId']
        net_qty = int(pos['netQty'])
        # लेटेस्ट प्राइस (LTP)
        ltp = float(pos.get('lastPrice', pos.get('ltp', 0))) 
        
        # एंट्री प्राइस (BUY है या SELL)
        is_long = net_qty > 0
        entry_price = float(pos['buyAvg']) if is_long else float(pos['sellAvg'])
        
        # PnL (मुनाफा/नुकसान) का % कैलकुलेशन
        if is_long:
            pnl_pct = ((ltp - entry_price) / entry_price) * 100
            exit_side = "SELL"
        else:
            pnl_pct = ((entry_price - ltp) / entry_price) * 100
            exit_side = "BUY"
            
        abs_qty = abs(net_qty)
        print(f"📊 पोजीशन: {symbol} | एंट्री: ₹{entry_price:.2f} | मौजूदा भाव: ₹{ltp:.2f} | P&L: {pnl_pct:.2f}%")

        # --- 🤖 AI रिस्क और ट्रेलिंग लॉजिक ---
        
        # 1. सख्त 1% स्टॉप लॉस
        if pnl_pct <= -1.0:
            execute_exit_order(symbol, sec_id, abs_qty, exit_side, "🚨 1% Stop-Loss Hit")
            
        # 2. 3.5% शानदार टारगेट
        elif pnl_pct >= 3.5:
            execute_exit_order(symbol, sec_id, abs_qty, exit_side, "🎯 3.5% Target Hit")
            
        # 3. AI Trailing (प्रॉफिट लॉक करना)
        # अगर स्टॉक 1.5% मुनाफे में जाने के बाद वापस गिरकर 0.2% पर आ जाए, तो ज़ीरो लॉस पर निकल जाओ
        elif pnl_pct < 0.2 and pnl_pct > 0: 
            # ध्यान दें: यह बेसिक ट्रेलिंग है। 1.5% तक जाने पर हम इसे सेफ मानते हैं।
            # अगर यह वापस एंट्री के पास आ रहा है तो काट देंगे।
            pass # (अभी इसे सिंपल SL और Target पर रखते हैं ताकि कोई गलत ट्रेड न कटे)

if __name__ == "__main__":
    run_ai_risk_manager()
