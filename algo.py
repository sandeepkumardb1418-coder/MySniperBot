import os, requests, pandas as pd, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# 🎯 Nifty 500 की मास्टर वॉचलिस्ट (बेहतरीन अवसरों के लिए)
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

def get_trade_status():
    """सख्त नियम: ओपन ट्रेड और टोटल 2 ट्रेड की लिमिट चेक करना"""
    try:
        res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
        if res.status_code != 200: return -1, -1
        
        positions = res.json()
        intraday_positions = [p for p in positions if p.get('productType') == 'INTRADAY']
        
        # कितने ट्रेड अभी चल रहे हैं?
        open_trades = sum(1 for p in intraday_positions if int(float(p.get('netQty', 0))) != 0)
        # आज कुल कितने ट्रेड लिए जा चुके हैं? (भले ही कट गए हों)
        total_trades_today = len(intraday_positions)
        
        return open_trades, total_trades_today
    except Exception as e:
        print(f"❌ स्टेटस चेक एरर: {e}")
        return -1, -1

def fetch_dhan_master_ids():
    """धन सर्वर से सटीक ID डाउनलोड"""
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df_eq = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') & (df['SEM_SERIES'] == 'EQ')]
        return dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_SMST_SECURITY_ID'])), dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_TRADING_SYMBOL']))
    except:
        return {}, {}

def run_pro_sniper():
    open_trades, total_trades = get_trade_status()
    
    # 🚨 रूल 1: अगर कोई ट्रेड ओपन है, तो नया मत लो (Risk Manager को काम करने दो)
    if open_trades > 0:
        print("⏳ एक पोजीशन पहले से ओपन है। नया ट्रेड नहीं लिया जाएगा।")
        return
        
    # 🚨 रूल 2: अगर दिन के 2 ट्रेड पूरे हो गए, तो मशीन बंद
    if total_trades >= 2:
        print("🛑 आज के अधिकतम 2 बेहतरीन ट्रेड पूरे हो चुके हैं। मशीन अब कल तक के लिए लॉक है।")
        return

    # फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    if f_res.status_code != 200: return
    cash = float(f_res.json().get('availabelBalance', 0))
    if cash < 100: return

    # मास्टर फाइल सिंक
    id_map, symbol_map = fetch_dhan_master_ids()
    if not id_map: return

    # स्कैनिंग (केवल बेहतरीन अवसर)
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

            # 🚀 असली बेहतरीन अवसर: 1.5% का मज़बूत मूव
            if change > 1.5 or change < -1.5:
                side = "BUY" if change > 1.5 else "SELL"
                qty = int((cash * 4) / ltp)
                if qty < 1: qty = 1 
                
                print(f"🎯 बेहतरीन अवसर मिला: {s} | मूव: {change:.2f}% | साइड: {side}")
                
                payload = {
                    "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
                    "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                    "quantity": qty, "securityId": str(sec_id), "tradingSymbol": str(exact_symbol), "price": 0
                }
                res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                
                if res.status_code in [200, 201]:
                    print(f"🔥 {s} में ट्रेड लग गया है। मशीन अब एग्जिट का इंतज़ार करेगी।")
                    break # एक बार में एक ही ट्रेड
        except:
            continue

if __name__ == "__main__":
    print(f"🚀 Nifty 500 प्रो स्नाइपर बूट... ({datetime.now().strftime('%H:%M:%S')})")
    run_pro_sniper()
