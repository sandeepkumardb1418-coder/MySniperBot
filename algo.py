import os, requests, pandas as pd, yfinance as yf
from datetime import datetime

CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# Nifty 500 टॉप स्टॉक्स की लिस्ट
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

def analyze_previous_orders_and_positions():
    """मशीन का दिमाग: ऑर्डर्स और पोजीशन का आंकलन करेगा"""
    traded_symbols = set()
    open_trades_count = 0
    total_trades_taken = 0

    # 1. ऑर्डर हिस्ट्री चेक करना (ताकि कोई पुराना कटा हुआ सौदा भी याद रहे)
    try:
        ord_res = requests.get("https://api.dhan.co/orders", headers=HEADERS)
        if ord_res.status_code == 200:
            for o in ord_res.json():
                if o.get('orderStatus') == 'TRADED':
                    sym = str(o.get('tradingSymbol', '')).split('-')[0]
                    traded_symbols.add(sym)
    except Exception as e:
        print("ऑर्डर चेक फेल:", e)

    # 2. करेंट ओपन पोजीशन चेक करना
    try:
        pos_res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
        if pos_res.status_code == 200:
            for p in pos_res.json():
                if p.get('productType') == 'INTRADAY':
                    if abs(int(float(p.get('netQty', 0)))) > 0:
                        open_trades_count += 1
    except:
        pass
    
    total_trades_taken = len(traded_symbols)
    return traded_symbols, open_trades_count, total_trades_taken

def execute_smart_sniper():
    # --- स्मार्ट आंकलन शुरू ---
    traded_symbols, open_trades, total_trades = analyze_previous_orders_and_positions()

    if open_trades > 0:
        print("⏳ एक ट्रेड अभी चालू है। मशीन ओवरट्रेडिंग रोकने के लिए स्लीप मोड में जा रही है।")
        return

    if total_trades >= 2:
        print(f"🛑 आज के 2 ट्रेड ({traded_symbols}) पूरे हो चुके हैं। मशीन आज के लिए परमानेंट बंद।")
        return

    # 🧠 एडवांस थिंकिंग: अगर 1 ट्रेड हो चुका है (यानी शायद लॉस हुआ है), तो अगली बार ज़्यादा सेफ एंट्री लो
    required_momentum = 1.5
    if total_trades == 1:
        print("⚠️ 1 ट्रेड हो चुका है। रिकवरी के लिए अब 'बेहतरीन अवसर' (2.0% मूव) की तलाश है...")
        required_momentum = 2.0 

    # --- फंड चेक ---
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    if f_res.status_code != 200: return
    cash = float(f_res.json().get('availabelBalance', 0))
    if cash < 100: return

    # --- ID सिंक ---
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df_eq = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') & (df['SEM_SERIES'] == 'EQ')]
        id_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_SMST_SECURITY_ID']))
        symbol_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_TRADING_SYMBOL']))
    except: return

    # --- शिकार खोजना ---
    for s in WATCHLIST:
        # 🚨 सबसे सख्त नियम: अगर आज इस शेयर का नाम ऑर्डर बुक में है, तो इसे छुओ भी मत
        if s in traded_symbols:
            continue

        sec_id = id_map.get(s)
        exact_symbol = symbol_map.get(s)
        if not sec_id or not exact_symbol: continue

        try:
            df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
            if len(df) < 2: continue

            ltp = df['Close'].iloc[-1]
            open_p = df['Open'].iloc[0]
            change = ((ltp - open_p) / open_p) * 100

            # 🚀 स्मार्ट शर्त: नॉर्मल दिन 1.5%, रिकवरी के लिए 2.0%
            if change > required_momentum or change < -required_momentum:
                side = "BUY" if change > required_momentum else "SELL"
                qty = int((cash * 4) / ltp)
                if qty < 1: qty = 1 
                
                print(f"🎯 बेहतरीन अवसर लॉक: {s} | मूव: {change:.2f}% | साइड: {side}")
                
                payload = {
                    "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
                    "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                    "quantity": qty, "securityId": str(sec_id), "tradingSymbol": str(exact_symbol), "price": 0
                }
                res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                if res.status_code in [200, 201]:
                    print(f"🔥 {s} में स्मार्ट ट्रेड लग गया! नया शिकार खोजना बंद।")
                    break
        except: continue

if __name__ == "__main__":
    print(f"🚀 AI असेसमेंट इंजन स्टार्ट... ({datetime.now().strftime('%H:%M:%S')})")
    execute_smart_sniper()
