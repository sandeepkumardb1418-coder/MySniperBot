import os, requests, pandas as pd, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# 🎯 NIFTY 500 की मास्टर वॉचलिस्ट (आप इसमें और भी नाम जोड़ सकते हैं)
NIFTY_WATCHLIST = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "INFY", "ITC", "SBIN", 
    "LTIM", "HINDUNILVR", "BAJFINANCE", "TATAMOTORS", "LT", "HCLTECH", "ASIANPAINT", 
    "SUNPHARMA", "MARUTI", "TITAN", "ULTRACEMCO", "KOTAKBANK", "NTPC", "TATACONSUM", 
    "ONGC", "M&M", "WIPRO", "JSWSTEEL", "POWERGRID", "COALINDIA", "HDFCLIFE", "BAJAJFINSV", 
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "GRASIM", "BAJAJ-AUTO", "HINDALCO", "TECHM", 
    "DIVISLAB", "DRREDDY", "BRITANNIA", "CIPLA", "EICHERMOT", "TATAPOWER", "TATASTEEL", 
    "ZOMATO", "ANANDRATHI", "AWL", "DCXINDIA", "NOCIL", "IRFC", "RVNL", "MAZDOCK", "PAYTM"
]

def fetch_dhan_master_ids():
    """अत्याधुनिक तकनीक: धन की आज की ताज़ा 'Scrip Master' फाइल सीधा सर्वर से डाउनलोड करना"""
    print("📥 धन (Dhan) के सर्वर से आज की आधिकारिक 'Master ID List' डाउनलोड हो रही है...")
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        
        # सिर्फ NSE और Equity (शेयरों) का डेटा फिल्टर करना
        df_eq = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') & (df['SEM_SERIES'] == 'EQ')]
        
        # सिंबल को उसकी सटीक ID के साथ जोड़ना (Mapping)
        id_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_SMST_SECURITY_ID']))
        symbol_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_TRADING_SYMBOL']))
        
        print(f"✅ धन सर्वर सिंक सफल! कुल {len(id_map)} शेयरों की असली ID सुरक्षित कर ली गई है।")
        return id_map, symbol_map
    except Exception as e:
        print(f"❌ मास्टर लिस्ट डाउनलोड एरर: {e}")
        return {}, {}

def fire_flawless_order(symbol, sec_id, exact_trading_symbol, qty, side):
    """ज़ीरो एरर आर्डर एग्जीक्यूशन"""
    url = "https://api.dhan.co/orders"
    payload = {
        "dhanClientId": CLIENT_ID,
        "transactionType": side,
        "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY",
        "orderType": "MARKET",
        "quantity": int(qty),
        "securityId": str(sec_id), # धन द्वारा दी गई 100% सटीक ID
        "tradingSymbol": str(exact_trading_symbol), # धन का अपना फॉर्मेट (जैसे RELIANCE-EQ)
        "price": 0
    }
    
    try:
        res = requests.post(url, headers=HEADERS, json=payload)
        if res.status_code == 200 or res.status_code == 201:
            print(f"🔥 महा-सफलता! {symbol} का {side} आर्डर आपके ऐप में लग गया है!")
        else:
            print(f"⚠️ ब्रोकर रिस्पॉन्स: {res.status_code} | {res.text}")
    except Exception as e:
        print(f"❌ आर्डर भेजने में इंटरनेट एरर: {e}")

def run_ultimate_sniper():
    # 1. फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    if f_res.status_code != 200:
        print("❌ धन API से कनेक्शन फेल।")
        return
    cash = float(f_res.json().get('availabelBalance', 0))
    print(f"💰 उपलब्ध कैपिटल: ₹{cash}")

    # 2. धन मास्टर फाइल डाउनलोड
    id_map, symbol_map = fetch_dhan_master_ids()
    if not id_map: return

    # 3. सुपर-फ़ास्ट स्कैनिंग
    for s in NIFTY_WATCHLIST:
        try:
            sec_id = id_map.get(s)
            exact_symbol = symbol_map.get(s)
            
            # अगर कोई शेयर धन की लिस्ट में आज नहीं है, तो उसे छोड़ दो
            if not sec_id or not exact_symbol: continue

            df = yf.Ticker(f"{s}.NS").history(period="1d", interval="5m")
            if df.empty or len(df) < 2: continue

            ltp = df['Close'].iloc[-1]
            open_p = df['Open'].iloc[0]
            change = ((ltp - open_p) / open_p) * 100

            # वॉल्यूम स्पाइक चेक (संस्थागत खरीदारी/बिकवाली)
            avg_vol = df['Volume'].rolling(10).mean().iloc[-2]
            curr_vol = df['Volume'].iloc[-1]

            # 🚀 एडवांस ब्रेकआउट स्ट्रेटेजी (1.5% मूव + 1.5x वॉल्यूम)
            if change > 1.5 and curr_vol > (avg_vol * 1.5):
                qty = int((cash * 4) / ltp)
                print(f"🎯 शिकार लॉक: {s} | {change:.2f}% UP | Volume Spike Detected!")
                fire_flawless_order(s, sec_id, exact_symbol, qty, "BUY")
                break # एक बार में एक ट्रेड

            elif change < -1.5 and curr_vol > (avg_vol * 1.5):
                qty = int((cash * 4) / ltp)
                print(f"📉 शिकार लॉक: {s} | {change:.2f}% DOWN | Panic Selling Detected!")
                fire_flawless_order(s, sec_id, exact_symbol, qty, "SELL")
                break
                
        except: continue

if __name__ == "__main__":
    print(f"🚀 अल्टीमेट स्नाइपर इंजन बूट हो रहा है... ({datetime.now().strftime('%H:%M:%S')})")
    run_ultimate_sniper()
    print("🏁 स्कैनिंग साइकिल पूरी हुई।")
