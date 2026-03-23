import os, requests, pytz, pandas as pd, numpy as np, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()

HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# --- सेटिंग्स ---
LEVERAGE = 5
SL_PCT = 1.0 

def get_market_sentiment():
    try:
        nifty = yf.Ticker("^NSEI").history(period="2d")
        return ((nifty['Close'].iloc[-1] - nifty['Open'].iloc[-1]) / nifty['Open'].iloc[-1]) * 100
    except: return 0

def get_dhan_funds():
    try:
        res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
        return float(res.json().get('availabelBalance', 0)) if res.status_code == 200 else 0
    except: return 0

def place_strict_orders(symbol, ltp, qty, side):
    """सख्त इंट्राडे आर्डर"""
    try:
        p_main = {
            "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty,
            "securityId": "11915", "price": 0
        }
        requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_main)
        
        sl_price = round(ltp * 0.99, 1) if side == "BUY" else round(ltp * 1.01, 1)
        p_sl = {
            "dhanClientId": CLIENT_ID, "transactionType": "SELL" if side == "BUY" else "BUY",
            "exchangeSegment": "NSE_EQ", "productType": "INTRADAY", "orderType": "STOP_LOSS",
            "quantity": qty, "securityId": "11915", "price": 0, "triggerPrice": sl_price
        }
        requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_sl)
        print(f"✅ ट्रेड निष्पादित: {symbol} {side} at {ltp} with 1% SL")
    except Exception as e: print(f"❌ आर्डर एरर: {e}")

def exit_open_positions():
    """ब्रोकर पेनल्टी से बचाव (2:45 PM)"""
    try:
        res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
        if res.status_code == 200:
            for pos in res.json():
                net_qty = float(pos.get('buyQty', 0)) - float(pos.get('sellQty', 0))
                if net_qty != 0 and pos.get('productType') == 'INTRADAY':
                    side = "SELL" if net_qty > 0 else "BUY"
                    p_exit = {
                        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": pos.get('exchangeSegment'),
                        "productType": "INTRADAY", "orderType": "MARKET", "quantity": int(abs(net_qty)),
                        "securityId": pos.get('securityId'), "price": 0
                    }
                    requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_exit)
                    print(f"🛡️ ऑटो-एक्जिट: {pos.get('tradingSymbol')} क्लोज्ड।")
    except: pass

def sniper_360_scan():
    cash = get_dhan_funds()
    if cash < 100: return

    sentiment = get_market_sentiment()
    print(f"💰 बैलेंस: ₹{cash} | 🌍 आज का मूड: {sentiment:.2f}%")

    symbols = pd.read_csv("https://archives.nseindia.com/content/indices/ind_nifty500list.csv")['Symbol'].tolist()
    
    for s in symbols[:200]: # Top 200 Stocks
        try:
            df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m") # सिर्फ आज का डेटा
            if len(df) < 5: continue
            
            ltp = df['Close'].iloc[-1]
            day_high = df['High'].iloc[:-1].max() # आज का अब तक का रेजिस्टेंस
            day_low = df['Low'].iloc[:-1].min()   # आज का अब तक का सपोर्ट
            
            vol_avg = df['Volume'].rolling(5).mean().iloc[-2]
            vol_spike = df['Volume'].iloc[-1] > (vol_avg * 1.5)
            
            # --- एडवांस प्राइस एक्शन लॉजिक ---
            
            # 📈 गेनर (Breakout Strategy): रेजिस्टेंस तोड़ा + वॉल्यूम + मूड पॉजिटिव
            if ltp > day_high and vol_spike and sentiment > 0.1:
                qty = int((cash * LEVERAGE) / ltp)
                print(f"🎯 रेजिस्टेंस ब्रेकआउट: {s} | BUY | LTP: {ltp} | Prev High: {day_high}")
                place_strict_orders(s, ltp, qty, "BUY")
                return

            # 📉 लूजर (Breakdown Strategy): सपोर्ट तोड़ा + वॉल्यूम + मूड नेगेटिव
            elif ltp < day_low and vol_spike and sentiment < -0.1:
                qty = int((cash * LEVERAGE) / ltp)
                print(f"🎯 सपोर्ट ब्रेकडाउन: {s} | SELL | LTP: {ltp} | Prev Low: {day_low}")
                place_strict_orders(s, ltp, qty, "SELL")
                return

        except: continue
    print("🔍 स्कैन पूरा: फिलहाल कोई 'प्राइस एक्शन' ब्रेकआउट नहीं मिला।")

if __name__ == "__main__":
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M")
    if ist_now >= "14:45":
        exit_open_positions()
    else:
        sniper_360_scan()
