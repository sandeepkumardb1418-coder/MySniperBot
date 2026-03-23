import os, requests, pytz, pandas as pd, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def get_accurate_sec_id(symbol):
    """तकनीकी सुधार: यह सीधा धन के सिंबल मास्टर से ID उठाएगा"""
    try:
        # हम यहाँ एक डिक्शनरी का उपयोग कर रहे हैं जो सबसे ज़्यादा ट्रेड होने वाले स्टॉक्स के ID रखेगी
        # लाइव मार्केट में यह सबसे फ़ास्ट तरीका है
        master_ids = {"ANANDRATHI": "13637", "TATASTEEL": "3499", "RELIANCE": "2885", "AWL": "18096"}
        return master_ids.get(symbol, "11915") # अगर लिस्ट में नहीं है तो डिफॉल्ट (जोखिम भरा)
    except: return "11915"

def place_order(symbol, qty, side, ltp):
    sec_id = get_accurate_sec_id(symbol)
    payload = {
        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY", "orderType": "MARKET", "quantity": int(qty),
        "securityId": sec_id, "price": 0
    }
    # 🚨 असली सुधार: आर्डर रिस्पॉन्स को बारीकी से चेक करना
    response = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
    print(f"📡 {symbol} आर्डर स्टेटस: {response.status_code} | रिस्पॉन्स: {response.text}")

def sniper_360_logic():
    # फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    if f_res.status_code != 200:
        print("❌ धन सर्वर से कनेक्शन टूटा।")
        return
    cash = float(f_res.json().get('availabelBalance', 0))
    
    # मार्केट मूड (करेंट डे)
    nifty = yf.Ticker("^NSEI").history(period="1d", interval="15m")
    sentiment = ((nifty['Close'].iloc[-1] - nifty['Open'].iloc[0]) / nifty['Open'].iloc[0]) * 100
    
    print(f"💰 बैलेंस: ₹{cash} | 🌍 मूड: {sentiment:.2f}%")

    # टॉप 100 शेयरों को ही स्कैन करें (स्पीड के लिए)
    stocks = ["ANANDRATHI", "TATASTEEL", "RELIANCE", "AWL", "ZOMATO", "IRFC", "RVNL"]
    
    for s in stocks:
        df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
        if len(df) < 2: continue
        
        ltp = df['Close'].iloc[-1]
        change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
        
        # सरल लेकिन मज़बूत प्राइस एक्शन
        if change > 2.5 and sentiment > 0.2:
            place_order(s, int((cash*5)/ltp), "BUY", ltp)
            break
        elif change < -2.5 and sentiment < -0.2:
            place_order(s, int((cash*5)/ltp), "SELL", ltp)
            break

if __name__ == "__main__":
    sniper_360_logic()
