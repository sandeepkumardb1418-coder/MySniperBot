import os, requests, yfinance as yf

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def place_order(symbol, qty, side):
    """सिर्फ नाम के आधार पर सीधा आर्डर"""
    url = "https://api.dhan.co/orders"
    payload = {
        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY", "orderType": "MARKET", "quantity": int(qty),
        "tradingSymbol": f"{symbol}-EQ", "price": 0
    }
    res = requests.post(url, headers=HEADERS, json=payload)
    print(f"🚀 {symbol} | आर्डर भेजा गया | स्टेटस: {res.status_code} | रिस्पॉन्स: {res.text}")

def forced_trade_logic():
    # फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    cash = float(f_res.json().get('availabelBalance', 0))
    print(f"💰 उपलब्ध फंड: ₹{cash}")

    # इन 5 शेयरों में से जो भी आज थोड़ा भी मूव कर रहा है, उसे पकड़ो
    stocks = ["ANANDRATHI", "ZOMATO", "TATASTEEL", "RELIANCE", "AWL"]
    
    for s in stocks:
        df = yf.Ticker(f"{s}.NS").history(period="1d", interval="5m")
        if len(df) < 2: continue
        
        ltp = df['Close'].iloc[-1]
        change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
        
        print(f"👀 चेकिंग: {s} | चेंज: {change:.2f}%")

        # एकदम आसान शर्त: अगर 0.5% भी ऊपर या नीचे है, तो घुस जाओ!
        if change > 0.5:
            place_order(s, int((cash * 4) / ltp), "BUY")
            return
        elif change < -0.5:
            place_order(s, int((cash * 4) / ltp), "SELL")
            return

if __name__ == "__main__":
    forced_trade_logic()
