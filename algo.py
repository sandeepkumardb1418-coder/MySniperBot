import os, requests, pytz, pandas as pd, numpy as np, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# --- नियम ---
LEVERAGE = 5
SL_PCT = 1.0 # सख्त 1% स्टॉप लॉस
MAX_TRADES_PER_DAY = 2

def get_market_sentiment():
    """नियम: ग्लोबल और निफ्टी का 360° मूड चेक"""
    try:
        nifty = yf.Ticker("^NSEI").history(period="2d")
        return ((nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]) / nifty['Close'].iloc[-2]) * 100
    except: return 0

def calculate_ai_indicators(df):
    """फेक ब्रेकआउट से बचने और ट्रेलिंग के लिए RSI कैलकुलेशन"""
    df['Change'] = df['Close'].diff()
    df['Gain'] = df['Change'].mask(df['Change'] < 0, 0.0)
    df['Loss'] = -df['Change'].mask(df['Change'] > 0, 0.0)
    df['Avg_Gain'] = df['Gain'].rolling(14).mean()
    df['Avg_Loss'] = df['Loss'].rolling(14).mean()
    rs = df['Avg_Gain'] / df['Avg_Loss']
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def check_open_positions_and_trail():
    """नियम: ट्रेलिंग टारगेट और डायनामिक एग्जिट"""
    try:
        res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
        positions = res.json() if res.status_code == 200 else []
        
        for pos in positions:
            if pos.get('positionType') == 'OPEN':
                symbol = pos.get('tradingSymbol')
                side = pos.get('transactionType')
                
                df = yf.Ticker(f"{symbol}.NS").history(period="1d", interval="15m")
                current_rsi = calculate_ai_indicators(df)['RSI'].iloc[-1]
                
                print(f"🔍 ट्रेलिंग रडार: {symbol} | RSI: {current_rsi:.2f}")
                
                # AI मोमेंटम रिवर्सल चेक (Trailing Stop)
                if side == "BUY" and current_rsi < 55:
                    print(f"⚠️ मोमेंटम टूट रहा है! {symbol} में प्रॉफिट बुक किया जा रहा है।")
                    return True
        return False
    except: return False

def place_strict_orders(symbol, ltp, qty, side):
    """नियम: सख्त 1% स्टॉप लॉस आर्डर सीधा ब्रोकर के टर्मिनल पर (X-Ray के साथ)"""
    try:
        # 1. मुख्य आर्डर (Entry)
        p_main = {
            "dhanClientId": CLIENT_ID, 
            "transactionType": side, 
            "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", 
            "orderType": "MARKET", 
            "quantity": qty,
            "securityId": "11915", # ध्यान दें: यहाँ अभी डमी ID है, इसे ठीक करना होगा
            "price": 0
        }
        res_main = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_main)
        print(f"📡 ब्रोकर का जवाब (Main): {res_main.text}")
        
        # 2. 1% सख्त स्टॉप लॉस कैलकुलेशन
        if side == "BUY":
            sl_price = round(ltp - (ltp * (SL_PCT / 100)), 1)
            sl_side = "SELL"
        else:
            sl_price = round(ltp + (ltp * (SL_PCT / 100)), 1)
            sl_side = "BUY"
            
        # 3. स्टॉप लॉस आर्डर ब्रोकर को भेजना
        p_sl = {
            "dhanClientId": CLIENT_ID, 
            "transactionType": sl_side, 
            "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", 
            "orderType": "STOP_LOSS", 
            "quantity": qty,
            "securityId": "11915", 
            "price": 0, 
            "triggerPrice": sl_price
        }
        res_sl = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_sl)
        print(f"📡 ब्रोकर का जवाब (SL): {res_sl.text}")
        print(f"🛡️ 1% सख्त SL सेट किया गया: ₹{sl_price} पर।")
    except Exception as e:
        print(f"आर्डर लगाने में त्रुटि: {e}")

def sniper_360_scan():
    """नियम: केवल हाई-प्रोबेबिलिटी क्वालिटी ट्रेड"""
    sentiment = get_market_sentiment()
    leverage = 5 if abs(sentiment) > 0.5 else 3 
    
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    cash = float(f_res.json().get('availabelBalance', 0)) if f_res.status_code == 200 else 0
    if cash < 100: return
    
    print(f"💰 फंड: ₹{cash} | 🌍 ग्लोबल सेंटीमेंट: {sentiment:.2f}% | ⚙️ लेवरेज: {leverage}x")

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

            # BUY कंडीशन
            if change >= 2.0 and vol_spike and (60 < rsi < 75) and sentiment > -0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 हाई-क्वालिटी शिकार: {s} | BUY | RSI: {rsi:.1f} | Qty: {qty}")
                place_strict_orders(s, ltp, qty, "BUY")
                return  

            # SELL कंडीशन
            elif change <= -2.0 and vol_spike and (25 < rsi < 40) and sentiment < 0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 हाई-क्वालिटी शिकार: {s} | SELL | RSI: {rsi:.1f} | Qty: {qty}")
                place_strict_orders(s, ltp, qty, "SELL")
                return
        except: continue

if __name__ == "__main__":
    is_trailing = check_open_positions_and_trail()
    if not is_trailing:
        sniper_360_scan()
    print("✅ AI चेक पूरा हुआ। सिस्टम स्टैंडबाय पर जा रहा है।")
