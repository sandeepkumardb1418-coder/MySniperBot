import os, requests, pytz, pandas as pd, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def place_order(symbol, qty, side):
    """फाइनल उपाय: शुद्ध सिंबल आधारित आर्डर"""
    url = "https://api.dhan.co/orders"
    
    # धन (Dhan) के लिए सिंबल को सही फॉर्मेट (SYMBOL-EQ) में बदलना
    formatted_symbol = f"{symbol}-EQ" 
    
    payload = {
        "dhanClientId": CLIENT_ID,
        "transactionType": side,
        "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY",
        "orderType": "MARKET",
        "quantity": int(qty),
        "tradingSymbol": formatted_symbol, 
        "price": 0
    }
    
    try:
        res = requests.post(url, headers=HEADERS, json=payload)
        print(f"📡 {formatted_symbol} | Status: {res.status_code}")
        print(f"📄 Server Response: {res.text}")
    except Exception as e:
        print(f"❌ कनेक्शन एरर: {e}")

def sniper_360_logic():
    # 1. फंड और मूड चेक
    try:
        f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
        cash = float(f_res.json().get('availabelBalance', 0))
        nifty = yf.Ticker("^NSEI").history(period="1d", interval="15m")
        sentiment = ((nifty['Close'].iloc[-1] - nifty['Open'].iloc[0]) / nifty['Open'].iloc[0]) * 100
        print(f"💰 फंड: ₹{cash} | 🌍 मूड: {sentiment:.2f}%")
    except: return

    # 2. आज के 'प्राइस एक्शन' स्टॉक्स (सिर्फ 5 सबसे मज़बूत नाम)
    stocks = ["ANANDRATHI", "DCXINDIA", "NOCIL", "AWL", "RELIANCE"]
    
    for s in stocks:
        try:
            df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
            if len(df) < 2: continue
            
            ltp = df['Close'].iloc[-1]
            day_high = df['High'].iloc[:-1].max()
            day_low = df['Low'].iloc[:-1].min()
            
            # 📈 रेजिस्टेंस ब्रेकआउट (BUY)
            if ltp > day_high and sentiment > 0.1:
                place_order(s, int((cash * 4) / ltp), "BUY")
                break
            # 📉 सपोर्ट ब्रेकडाउन (SELL)
            elif ltp < day_low and sentiment < -0.1:
                place_order(s, int((cash * 4) / ltp), "SELL")
                break
        except: continue

if __name__ == "__main__":
    print("🚀 स्नाइपर 2.0 (नो-आईडी मोड) स्टार्ट...")
    sniper_360_logic()
    print("✅ प्रक्रिया पूरी हुई।")
