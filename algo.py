import os, requests, pytz, pandas as pd, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def place_order(symbol, qty, side):
    """सुधार: सीधा सिंबल से आर्डर, ताकि ID का झंझट खत्म हो"""
    url = "https://api.dhan.co/orders"
    payload = {
        "dhanClientId": CLIENT_ID,
        "transactionType": side,
        "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY",
        "orderType": "MARKET",
        "quantity": int(qty),
        "tradingSymbol": symbol, # सीधा नाम का उपयोग
        "price": 0
    }
    res = requests.post(url, headers=HEADERS, json=payload)
    print(f"📡 {symbol} आर्डर स्टेटस: {res.status_code} | रिस्पॉन्स: {res.text}")

def sniper_360_logic():
    # 1. फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    cash = float(f_res.json().get('availabelBalance', 0)) if f_res.status_code == 200 else 0
    
    # 2. आज का मूड (Nifty)
    nifty = yf.Ticker("^NSEI").history(period="1d", interval="15m")
    sentiment = ((nifty['Close'].iloc[-1] - nifty['Open'].iloc[0]) / nifty['Open'].iloc[0]) * 100
    print(f"💰 बैलेंस: ₹{cash} | 🌍 मूड: {sentiment:.2f}%")

    # 3. टॉप हाई-वॉल्यूम स्टॉक्स (करेंट विश्लेषण)
    stocks = ["ANANDRATHI", "AWL", "DCXINDIA", "NOCIL", "ZOMATO"]
    
    for s in stocks:
        df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
        if len(df) < 2: continue
        
        ltp = df['Close'].iloc[-1]
        change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
        
        # गेनर पकड़ने का नियम (जैसे DCX, NOCIL)
        if change > 3.0 and sentiment > -0.5:
            qty = int((cash * 4) / ltp) # 4x लेवरेज
            place_order(s, qty, "BUY")
            break
        # लूजर पकड़ने का नियम
        elif change < -3.0 and sentiment < 0.5:
            qty = int((cash * 4) / ltp)
            place_order(s, qty, "SELL")
            break

if __name__ == "__main__":
    sniper_360_logic()
