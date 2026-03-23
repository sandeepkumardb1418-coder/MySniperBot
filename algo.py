import os, requests, pandas as pd, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# 🎯 Nifty 500 की बड़ी लिस्ट (मशीन अब पूरा जंगल छानेगी)
WATCHLIST = [
    "ABB", "ACC", "ADANIENT", "ADANIPORTS", "ADANIPOWER", "AMBUJACEM", "APOLLOHOSP", "ASIANPAINT", "AUBANK", "AXISBANK", 
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BEL", "BERGEPAINT", "BHARATFORG", 
    "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", 
    "COLPAL", "CONCOR", "CROMPTON", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", 
    "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GODREJCP", "GODREJPROP", "GRASIM", "GUJGASLTD", 
    "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", 
    "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIGO", 
    "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IRCTC", "IRFC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", 
    "L&TFH", "LTIM", "LT", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MFSL", "MPHASIS", "MRF", "MUTHOOTFIN", 
    "NATIONALUM", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "ONGC", "PAGEIND", "PEL", "PERSISTENT", "PETRONET", 
    "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", 
    "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", 
    "TATAELXSI", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", 
    "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZOMATO", "ZYDUSLIFE", "AWL", "DCXINDIA", "NOCIL", "RVNL"
]

def check_if_trade_already_done():
    """सख्त नियम: ओवरट्रेडिंग और ब्रोकर की लूट बंद करने के लिए"""
    try:
        res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
        if res.status_code == 200:
            positions = res.json()
            for p in positions:
                # अगर आज कोई भी इंट्राडे ट्रेड हुआ है (चाहे ओपन हो या क्लोज्ड), तो मशीन चुप रहेगी
                if p.get('productType') == 'INTRADAY':
                    return True 
    except Exception as e:
        pass
    return False 

def fetch_dhan_master_ids():
    """ID सिंक"""
    print("📥 Master ID List डाउनलोड हो रही है...")
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df_eq = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') & (df['SEM_SERIES'] == 'EQ')]
        id_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_SMST_SECURITY_ID']))
        symbol_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_TRADING_SYMBOL']))
        return id_map, symbol_map
    except:
        return {}, {}

def run_pro_sniper():
    # 🚨 सबसे पहला चेक: क्या आज कोई ट्रेड हो चुका है?
    if check_if_trade_already_done():
        print("🛑 आज का ट्रेड कोटा पूरा हो चुका है। ब्रोकरेज बचाने के लिए नया ट्रेड नहीं लिया जाएगा।")
        return 

    # 1. फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    if f_res.status_code != 200: return
    cash = float(f_res.json().get('availabelBalance', 0))
    if cash < 100: return

    # 2. धन मास्टर फाइल सिंक
    id_map, symbol_map = fetch_dhan_master_ids()
    if not id_map: return

    # 3. 500 स्टॉक स्कैनिंग और सॉलिड ट्रेड
    for s in WATCHLIST:
        sec_id = id_map.get(s)
        exact_symbol = symbol_map.get(s)
        if not sec_id or not exact_symbol: continue

        try:
            df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
            if len(df) < 2: continue

            ltp = df['Close'].iloc[-1]
            open_p = df['Open'].iloc[0]
            change = ((ltp - open_p) / open_p) * 100

            # 🚀 असली शर्त: 1.5% का मज़बूत मूव (बच्चों वाला 0.2% नहीं)
            if change > 1.5 or change < -1.5:
                side = "BUY" if change > 1.5 else "SELL"
                qty = int((cash * 4) / ltp)
                if qty < 1: qty = 1 
                
                print(f"🎯 सॉलिड शिकार: {s} | मूव: {change:.2f}% | साइड: {side}")
                
                payload = {
                    "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
                    "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                    "quantity": qty, "securityId": str(sec_id), "tradingSymbol": str(exact_symbol), "price": 0
                }
                res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                
                if res.status_code in [200, 201]:
                    print(f"🔥 {s} में 1 सिंगल ट्रेड लग गया है। मशीन अब बंद हो रही है।")
                    break # एक ट्रेड होते ही लूप ब्रेक!
        except:
            continue

if __name__ == "__main__":
    print(f"🚀 Nifty 500 प्रो स्नाइपर बूट... ({datetime.now().strftime('%H:%M:%S')})")
    run_pro_sniper()
    print("🏁 स्कैनिंग पूरी।")
