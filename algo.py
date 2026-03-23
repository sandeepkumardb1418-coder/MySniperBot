import os, requests, pytz, pandas as pd, numpy as np, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स (सख्त नियम) ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()

# Dhan API के लिए सटीक Headers
HEADERS = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# --- नियम ---
LEVERAGE = 5
SL_PCT = 1.0 

def get_market_sentiment():
    try:
        nifty = yf.Ticker("^NSEI").history(period="2d")
        return ((nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]) / nifty['Close'].iloc[-2]) * 100
    except: return 0

def calculate_ai_indicators(df):
    df['Change'] = df['Close'].diff()
    df['Gain'] = df['Change'].mask(df['Change'] < 0, 0.0)
    df['Loss'] = -df['Change'].mask(df['Change'] > 0, 0.0)
    df['Avg_Gain'] = df['Gain'].rolling(14).mean()
    df['Avg_Loss'] = df['Loss'].rolling(14).mean()
    rs = df['Avg_Gain'] / df['Avg_Loss']
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def get_dhan_funds():
    """फंड चेक करने का 100% ट्रांसपेरेंट तरीका"""
    print("🔍 धन (Dhan) सर्वर से फंड की जानकारी ली जा रही है...")
    try:
        url = "https://api.dhan.co/fundlimit"
        res = requests.get(url, headers=HEADERS)
        
        # अगर सर्वर ने रोका, तो असली वजह यहाँ प्रिंट होगी
        if res.status_code != 200:
            print(f"❌ API Error ({res.status_code}): {res.text}")
            return 0
            
        cash = float(res.json().get('availabelBalance', 0))
        return cash
    except Exception as e:
        print(f"❌ सर्वर से जुड़ने में भयानक त्रुटि: {e}")
        return 0

def place_strict_orders(symbol, ltp, qty, side):
    """सख्त आर्डर और लाइव एरर रिपोर्टिंग"""
    try:
        # नोट: "securityId": "11915" डमी है। असल ट्रेडिंग में धन को हर शेयर का अलग ID चाहिए होता है।
        p_main = {
            "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty,
            "securityId": "11915", "price": 0
        }
        print(f"🚀 {symbol} के लिए {side} आर्डर भेजा जा रहा है...")
        res_main = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_main)
        print(f"📡 ब्रोकर का जवाब (Main): {res_main.status_code} - {res_main.text}")
        
        # SL कैलकुलेशन
        sl_price = round(ltp - (ltp * (SL_PCT / 100)), 1) if side == "BUY" else round(ltp + (ltp * (SL_PCT / 100)), 1)
        sl_side = "SELL" if side == "BUY" else "BUY"
            
        p_sl = {
            "dhanClientId": CLIENT_ID, "transactionType": sl_side, "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", "orderType": "STOP_LOSS", "quantity": qty,
            "securityId": "11915", "price": 0, "triggerPrice": sl_price
        }
        res_sl = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_sl)
        print(f"📡 ब्रोकर का जवाब (SL): {res_sl.status_code} - {res_sl.text}")
        
    except Exception as e:
        print(f"❌ आर्डर लगाने में त्रुटि: {e}")

def sniper_360_scan():
    cash = get_dhan_funds()
    if cash < 100: 
        print("⚠️ ट्रेडिंग के लिए पर्याप्त फंड नहीं है या API ने फंड नहीं बताया। सिस्टम बंद हो रहा है।")
        return

    sentiment = get_market_sentiment()
    leverage = 5 if abs(sentiment) > 0.5 else 3 
    print(f"✅ बैलेंस: ₹{cash} | 🌍 ग्लोबल मूड: {sentiment:.2f}% | ⚙️ लेवरेज: {leverage}x")

    symbols = pd.read_csv("https://archives.nseindia.com/content/indices/ind_nifty500list.csv")['Symbol'].tolist()
    
    for s in symbols[:200]:
        try:
            df = yf.Ticker(f"{s}.NS").history(period="5d", interval="15m")
            if len(df) < 15: continue
            
            df = calculate_ai_indicators(df)
            ltp = df['Close'].iloc[-1]
            change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
            
            vol_avg = df['Volume'].rolling(20).mean().iloc[-2]
            vol_spike = df['Volume'].iloc[-1] > (vol_avg * 2.5)
            rsi = df['RSI'].iloc[-1]

            if change >= 2.0 and vol_spike and (60 < rsi < 75) and sentiment > -0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 शिकार मिला: {s} | BUY | RSI: {rsi:.1f} | Qty: {qty}")
                place_strict_orders(s, ltp, qty, "BUY")
                return  

        except Exception as e: continue

if __name__ == "__main__":
    sniper_360_scan()
    print("✅ AI चेक पूरा हुआ।")
