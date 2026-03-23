import os, requests, pandas as pd, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# 🎯 टॉप 30 हाई-वॉल्यूम वॉचलिस्ट (GitHub मिनट बचाने और फ़ास्ट एग्जीक्यूशन के लिए)
WATCHLIST = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "ITC", "BHARTIARTL", 
    "BAJFINANCE", "TATAMOTORS", "SUNPHARMA", "MARUTI", "KOTAKBANK", "AXISBANK", 
    "NTPC", "TATASTEEL", "ULTRACEMCO", "POWERGRID", "M&M", "ASIANPAINT", "HCLTECH", 
    "TITAN", "BAJAJFINSV", "WIPRO", "NESTLEIND", "ZOMATO", "ANANDRATHI", "AWL", "IRFC", "RVNL"
]

def fetch_dhan_master_ids():
    """धन सर्वर से 100% सटीक ID डाउनलोड करना"""
    print("📥 धन सर्वर से Master ID List डाउनलोड हो रही है...")
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df_eq = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') & (df['SEM_SERIES'] == 'EQ')]
        id_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_SMST_SECURITY_ID']))
        symbol_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_TRADING_SYMBOL']))
        print("✅ Master ID List डाउनलोड सफल!")
        return id_map, symbol_map
    except Exception as e:
        print(f"❌ Master List डाउनलोड एरर: {e}")
        return {}, {}

def execute_instant_trade():
    # 1. फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    if f_res.status_code != 200:
        print("❌ धन API से कनेक्शन फेल।")
        return
    cash = float(f_res.json().get('availabelBalance', 0))
    if cash < 100:
        print("⚠️ ट्रेडिंग के लिए अपर्याप्त फंड।")
        return
    print(f"💰 उपलब्ध कैपिटल: ₹{cash}")

    # 2. धन मास्टर फाइल सिंक
    id_map, symbol_map = fetch_dhan_master_ids()
    if not id_map: return

    # 3. तुरंत ट्रेड (Instant Execution) लॉजिक
    trade_taken = False
    
    for s in WATCHLIST:
        if trade_taken: 
            break # एक ट्रेड हो गया, तो कोड तुरंत बंद (मिनट बचाने के लिए)
            
        sec_id = id_map.get(s)
        exact_symbol = symbol_map.get(s)
        if not sec_id or not exact_symbol: continue

        try:
            # लेटेस्ट 5 मिनट का डाटा
            df = yf.Ticker(f"{s}.NS").history(period="1d", interval="5m")
            if len(df) < 2: continue

            ltp = df['Close'].iloc[-1]
            open_p = df['Open'].iloc[0]
            change = ((ltp - open_p) / open_p) * 100

            # 🚀 तुरंत ट्रेड की शर्त (0.2% मूव)
            if change > 0.2 or change < -0.2:
                side = "BUY" if change > 0.2 else "SELL"
                
                # क्वांटिटी कैलकुलेशन (4x लेवरेज)
                qty = int((cash * 4) / ltp)
                if qty < 1: qty = 1 
                
                print(f"🎯 शिकार मिल गया: {s} | मूव: {change:.2f}% | साइड: {side}")
                
                # 💥 आर्डर प्रहार (सुधरा हुआ पेलोड - validity DAY के साथ)
                payload = {
                    "dhanClientId": CLIENT_ID, 
                    "transactionType": side, 
                    "exchangeSegment": "NSE_EQ",
                    "productType": "INTRADAY", 
                    "orderType": "MARKET", 
                    "validity": "DAY",        # 👈 यह रही वो जादुई लाइन जिसने हमारा एरर खत्म किया
                    "quantity": qty,
                    "securityId": str(sec_id), 
                    "tradingSymbol": str(exact_symbol), 
                    "price": 0
                }
                res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                
                if res.status_code in [200, 201]:
                    print(f"🔥 महा-सफलता! {s} का {side} आर्डर आपके धन ऐप में लग गया है!")
                else:
                    print(f"⚠️ ब्रोकर रिस्पॉन्स: {res.status_code} | {res.text}")
                    
                trade_taken = True
        except:
            continue
            
    if not trade_taken:
        print("⚠️ आज बाज़ार बिल्कुल जाम है (0.2% भी नहीं हिला)।")

if __name__ == "__main__":
    print(f"🚀 'Instant Trade' स्नाइपर बूट हो रहा है... ({datetime.now().strftime('%H:%M:%S')})")
    execute_instant_trade()
    print("🏁 कोड का काम पूरा हुआ। GitHub मिनट बचाए गए।")
