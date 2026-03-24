import os, requests, pandas as pd, yfinance as yf
from datetime import datetime

CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# Nifty 500 के टॉप स्टॉक्स 
WATCHLIST = [
    "ABB", "ACC", "ADANIENT", "ADANIPORTS", "ADANIPOWER", "AMBUJACEM", "APOLLOHOSP", "ASIANPAINT", "AUBANK", "AXISBANK", 
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BEL", "BERGEPAINT", "BHARATFORG", 
    "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", 
    "COLPAL", "CONCOR", "CROMPTON", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", 
    "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GODREJCP", "GODREJPROP", "GRASIM", "GUJGASLTD", 
    "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", 
    "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIGO", 
    "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IRCTC", "IRFC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", 
    "LTIM", "LT", "LUPIN", "M&M", "MARICO", "MARUTI", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NESTLEIND", "NMDC", 
    "NTPC", "OBEROIRLTY", "ONGC", "PEL", "PFC", "PIDILITIND", "PNB", "POWERGRID", "RECLTD", "RELIANCE", "SAIL", "SBIN", 
    "SIEMENS", "SRF", "SUNPHARMA", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", 
    "TECHM", "TITAN", "TRENT", "TVSMOTOR", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZOMATO", "AWL", "RVNL"
]

def get_dhan_positions():
    """धन API से आज की सारी पोजीशन मंगाना (ब्रोकर की लूट रोकने के लिए)"""
    try:
        res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

def execute_sniper():
    positions = get_dhan_positions()
    
    open_trades = 0
    traded_symbols_today = set()

    for p in positions:
        if p.get('productType') == 'INTRADAY':
            # सिंबल का नाम निकाल रहे हैं (जैसे ABB-EQ से सिर्फ ABB)
            sym = str(p.get('tradingSymbol', '')).split('-')[0]
            traded_symbols_today.add(sym)
            
            # अगर क्वांटिटी 0 नहीं है, मतलब ट्रेड अभी चल रहा है
            if abs(int(float(p.get('netQty', 0)))) > 0:
                open_trades += 1

    # 🚨 ब्रह्मास्त्र नियम 1: अगर 1 भी ट्रेड ओपन है, तो मशीन तुरंत बंद!
    if open_trades > 0:
        print("⏳ एक पोजीशन पहले से चालू है। गिटहब मिनट बचाने के लिए मशीन बंद हो रही है।")
        return

    # 🚨 ब्रह्मास्त्र नियम 2: दिन के 2 ट्रेड पूरे हो गए, तो मशीन बंद!
    if len(traded_symbols_today) >= 2:
        print(f"🛑 आज के 2 बेहतरीन ट्रेड पूरे हो चुके हैं ({traded_symbols_today})। सिस्टम आज के लिए बंद।")
        return

    # फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    if f_res.status_code != 200: return
    cash = float(f_res.json().get('availabelBalance', 0))
    if cash < 100: return

    # धन मास्टर ID सिंक
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df_eq = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') & (df['SEM_SERIES'] == 'EQ')]
        id_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_SMST_SECURITY_ID']))
        symbol_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_TRADING_SYMBOL']))
    except:
        return

    # शिकार खोजना शुरू
    for s in WATCHLIST:
        # 🚨 ब्रह्मास्त्र नियम 3: अगर इस शेयर में आज एक बार भी ट्रेड हो चुका है, तो इसे छोड़ दो!
        if s in traded_symbols_today:
            continue

        sec_id = id_map.get(s)
        exact_symbol = symbol_map.get(s)
        if not sec_id or not exact_symbol: continue

        try:
            # पिछले 15 मिनट का डेटा
            df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
            if len(df) < 2: continue

            ltp = df['Close'].iloc[-1]
            open_p = df['Open'].iloc[0]
            change = ((ltp - open_p) / open_p) * 100

            # 🚀 सॉलिड अवसर (1.5% का ट्रेंड)
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
                    print(f"🔥 {s} में 1 फ्रेश ट्रेड लग गया! लूप ब्रेक किया जा रहा है।")
                    break # एक ट्रेड लगते ही सर्च हमेशा के लिए बंद!
        except: continue

if __name__ == "__main__":
    execute_sniper()
