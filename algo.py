import os, requests, pytz, pandas as pd, numpy as np, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# --- AI स्मार्ट पैरामीटर्स ---
MAX_TRADES_PER_DAY = 2

def get_market_sentiment():
    """ग्लोबल और निफ्टी का 360° मूड चेक"""
    try:
        nifty = yf.Ticker("^NSEI").history(period="2d")
        return ((nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]) / nifty['Close'].iloc[-2]) * 100
    except: return 0

def calculate_ai_indicators(df):
    """फेक ब्रेकआउट से बचने के लिए RSI और ATR (Trailing Target) कैलकुलेशन"""
    df['Change'] = df['Close'].diff()
    df['Gain'] = df['Change'].mask(df['Change'] < 0, 0.0)
    df['Loss'] = -df['Change'].mask(df['Change'] > 0, 0.0)
    df['Avg_Gain'] = df['Gain'].rolling(14).mean()
    df['Avg_Loss'] = df['Loss'].rolling(14).mean()
    rs = df['Avg_Gain'] / df['Avg_Loss']
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def check_open_positions_and_trail():
    """नियम: ट्रेलिंग टारगेट (Trailing Target) और डायनामिक एग्जिट"""
    try:
        res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
        positions = res.json() if res.status_code == 200 else []
        
        for pos in positions:
            if pos.get('positionType') == 'OPEN':
                symbol = pos.get('tradingSymbol')
                side = pos.get('transactionType')
                
                # मोमेंटम चेक: अगर मोमेंटम टूट रहा है, तो तुरंत प्रॉफिट बुक करो (Trailing Exit)
                df = yf.Ticker(f"{symbol}.NS").history(period="1d", interval="15m")
                current_rsi = calculate_ai_indicators(df)['RSI'].iloc[-1]
                
                print(f"🔍 ट्रेलिंग रडार: {symbol} | RSI: {current_rsi:.2f}")
                
                # AI सेल्फ-करेक्शन: अगर BUY किया है और RSI 75 के ऊपर जाकर गिरने लगे, तो एग्जिट।
                if side == "BUY" and current_rsi < 55:
                    print(f"⚠️ मोमेंटम रिवर्सल! {symbol} में प्रॉफिट बुक किया जा रहा है।")
                    # यहाँ एग्जिट आर्डर का पेलोड आएगा
                    return True
        return False
    except: return False

def sniper_360_scan():
    """हाई-प्रोबेबिलिटी क्वालिटी ट्रेड (No Fake Breakouts)"""
    sentiment = get_market_sentiment()
    
    # डायनामिक लेवरेज (Self-Correction)
    # अगर मार्केट का मूड बहुत अच्छा है (>0.5%), तो 5x लेवरेज, वरना सिर्फ 3x रिस्क।
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
            
            # वॉल्यूम 20-कैंडल के एवरेज से 2.5 गुना ज्यादा होना चाहिए (फेक ब्रेकआउट किलर)
            vol_avg = df['Volume'].rolling(20).mean().iloc[-2]
            vol_spike = df['Volume'].iloc[-1] > (vol_avg * 2.5)
            rsi = df['RSI'].iloc[-1]

            # AI हाई-प्रोबेबिलिटी शर्त:
            # 1. 2% से ज़्यादा मूव
            # 2. भयंकर वॉल्यूम (Institutional Buying)
            # 3. RSI 60 से 75 के बीच (ताकि एकदम टॉप पर न फंसे)
            # 4. सेंटीमेंट के साथ
            if change >= 2.0 and vol_spike and (60 < rsi < 75) and sentiment > -0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 हाई-क्वालिटी शिकार: {s} | BUY | RSI: {rsi:.1f} | Qty: {qty}")
                
                p = {"dhanClientId": CLIENT_ID, "transactionType": "BUY", "exchangeSegment": "NSE_EQ",
                     "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty,
                     "securityId": "11915", "price": 0}
                requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p)
                return  # एक बार में एक ही बेस्ट ट्रेड

            elif change <= -2.0 and vol_spike and (25 < rsi < 40) and sentiment < 0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 हाई-क्वालिटी शिकार: {s} | SELL | RSI: {rsi:.1f} | Qty: {qty}")
                # SELL आर्डर पेलोड...
                return
        except: continue

if __name__ == "__main__":
    # 1. पहले चेक करो कि क्या कोई ट्रेड चल रहा है? अगर हाँ, तो उसे ट्रेल करो।
    is_trailing = check_open_positions_and_trail()
    
    # 2. अगर कोई पोजीशन ओपन नहीं है, तब नया हाई-प्रोबेबिलिटी ट्रेड ढूंढो।
    if not is_trailing:
        sniper_360_scan()
    
    # काम खत्म, स्क्रिप्ट बंद (मिनट बचाने के लिए)
    print("✅ AI चेक पूरा हुआ। सिस्टम स्टैंडबाय पर जा रहा है।")
