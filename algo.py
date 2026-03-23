import os, requests, yfinance as yf

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# 🎯 एडवांस डेटा: शेयरों के सटीक सिक्योरिटी ID (Dhan Master Data)
SECURITY_IDS = {
    "ANANDRATHI": "13637", "ZOMATO": "5097", "TATASTEEL": "3499", 
    "RELIANCE": "2885", "AWL": "18096", "DCXINDIA": "11915"
}

def place_order_advanced(symbol, qty, side):
    """बिना किसी एरर के सीधा सटीक आर्डर"""
    url = "https://api.dhan.co/orders"
    sec_id = SECURITY_IDS.get(symbol)
    
    if not sec_id:
        print(f"⚠️ {symbol} की ID नहीं मिली, स्किप कर रहा हूँ।")
        return

    payload = {
        "dhanClientId": CLIENT_ID,
        "transactionType": side,
        "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY",
        "orderType": "MARKET",
        "quantity": int(qty),
        "securityId": sec_id,  # 👈 अब कोई एरर नहीं आएगा
        "tradingSymbol": f"{symbol}-EQ",
        "price": 0
    }
    
    res = requests.post(url, headers=HEADERS, json=payload)
    print(f"📡 {symbol} | स्टेटस: {res.status_code} | रिस्पॉन्स: {res.text}")

def execution_engine():
    # 1. फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    if f_res.status_code != 200: return
    cash = float(f_res.json().get('availabelBalance', 0))
    print(f"💰 उपलब्ध कैश: ₹{cash}")

    # 2. एडवांस स्कैनिंग (Price + Volume)
    for s, sid in SECURITY_IDS.items():
        try:
            stock = yf.Ticker(f"{s}.NS")
            df = stock.history(period="1d", interval="5m")
            if df.empty: continue

            ltp = df['Close'].iloc[-1]
            change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
            
            print(f"🔍 विश्लेषण: {s} | भाव: {ltp} | बदलाव: {change:.2f}%")

            # प्रहार की शर्त: 1.5% का मूव मिलते ही आर्डर
            qty = int((cash * 4) / ltp) # 4x लेवरेज के साथ
            if change > 1.5:
                place_order_advanced(s, qty, "BUY")
                break
            elif change < -1.5:
                place_order_advanced(s, qty, "SELL")
                break
        except Exception as e:
            print(f"❌ {s} में तकनीकी दिक्कत: {e}")

if __name__ == "__main__":
    print("🔥 एडवांस स्नाइपर इंजन सक्रिय...")
    execution_engine()
    print("✅ आज का शिकार अभियान पूरा हुआ।")
