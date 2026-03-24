import os, requests, json, time, pandas as pd, yfinance as yf
from datetime import datetime
import pytz 

CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
DEFAULT_ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
TELEGRAM_BOT_TOKEN = str(os.environ.get("TELEGRAM_BOT_TOKEN")).strip()
TELEGRAM_CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID")).strip()

WATCHLIST = [
    "ABB", "ACC", "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJFINANCE", 
    "BHARTIARTL", "BHEL", "COALINDIA", "DLF", "EICHERMOT", "HAL", "HDFCBANK", "ICICIBANK", 
    "INFY", "ITC", "JSWSTEEL", "LT", "M&M", "MARUTI", "NTPC", "RELIANCE", "SBIN", "SUNPHARMA", 
    "TATASTEEL", "TCS", "TITAN", "ZOMATO", "RVNL", "IRFC", "AWL", "PNB", "POWERGRID", "VEDL"
]

MEMORY_FILE = "memory.json"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

def get_latest_token():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res.get("ok"):
            for msg in reversed(res["result"]):
                text = msg.get("message", {}).get("text", "")
                if text.startswith("TOKEN:"):
                    return text.replace("TOKEN:", "").strip()
    except: pass
    return DEFAULT_ACCESS_TOKEN

def load_memory():
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).strftime('%Y-%m-%d')
    default_mem = {"date": today, "trades_taken": [], "reports": {"pre_open": False, "market_open": False, "eod": False}, "hourly": []}
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                mem = json.load(f)
                if mem.get("date") == today: return mem
        except: pass
    return default_mem

def save_memory(mem):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(mem, f)

def main_engine():
    mem = load_memory()
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    hour = now.hour
    minute = now.minute
    def main_engine():
    send_telegram("✅ *CONNECTION TEST:* गिटहब और टेलीग्राम 100% जुड़ चुके हैं! संदीप भाई, मशीन रेडी है।")
    
    mem = load_memory()
    # ... (नीचे का बाकी कोड वैसे ही रहने दें)

    token = get_latest_token()
    headers = {"access-token": token, "client-id": CLIENT_ID, "Content-Type": "application/json"}

    # --- 🌅 प्री-ओपन रिपोर्ट (09:00 - 09:14) ---
    if hour == 9 and minute < 15 and not mem["reports"]["pre_open"]:
        send_telegram("🌅 *PRE-MARKET REPORT*\n✅ सिस्टम ऑनलाइन है।\n🎯 आज की स्नाइपर स्ट्रेटजी (9:30 AM Entry) लोड हो गई है।")
        mem["reports"]["pre_open"] = True
        save_memory(mem)

    # फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=headers)
    if f_res.status_code != 200:
        if "Unauthorized" in f_res.text or f_res.status_code in [401, 403]:
            send_telegram("🚨 *TOKEN EXPIRED*\nधन का सर्वर एक्सेस नहीं दे रहा है। टेलीग्राम पर नया टोकन भेजें: `TOKEN: your_token`")
        else:
            send_telegram(f"⚠️ *API Error:* धन का सर्वर डाउन है: {f_res.text}")
        return
    
    cash = float(f_res.json().get('availabelBalance', 0))

    # --- 🚀 मार्केट ओपन (9:15 - 9:29) - सिर्फ चेतावनी, ट्रेड नहीं ---
    if hour == 9 and 15 <= minute < 30 and not mem["reports"]["market_open"]:
        send_telegram(f"🚀 *MARKET OPEN*\n💰 कैपिटल: ₹{cash}\n⚠️ मार्केट सेटल हो रहा है। पहला ट्रेड *9:30 AM* के बाद ही लिया जाएगा।")
        mem["reports"]["market_open"] = True
        save_memory(mem)

    # --- ⏱️ प्रति घंटा अपडेट ---
    if hour in [10, 11, 12, 13, 14] and minute <= 15 and hour not in mem["hourly"]:
        send_telegram(f"⏱️ *HOURLY UPDATE ({hour}:00)*\n✅ मशीन सही काम कर रही है।\n💰 बैलेंस: ₹{cash}\n📊 ट्रेड: {len(mem['trades_taken'])}")
        mem["hourly"].append(hour)
        save_memory(mem)

    # --- 🌙 EOD रिपोर्ट (15:20 के बाद) ---
    if (hour == 15 and minute >= 20) or hour > 15:
        if not mem["reports"]["eod"]:
            send_telegram(f"🌙 *EOD REPORT*\n🏁 बाज़ार बंद।\n📊 कुल ट्रेड: {len(mem['trades_taken'])}\n💤 सिस्टम स्लीप मोड में जा रहा है।")
            mem["reports"]["eod"] = True
            save_memory(mem)
        return

    # ==========================================
    # 🛡️ ट्रेडिंग लॉजिक (सिर्फ 9:30 AM से 3:15 PM तक)
    # ==========================================
    trading_allowed = False
    if hour == 9 and minute >= 30: trading_allowed = True
    elif 10 <= hour < 15: trading_allowed = True
    elif hour == 15 and minute < 15: trading_allowed = True

    if trading_allowed:
        
        pos_res = requests.get("https://api.dhan.co/positions", headers=headers)
        open_trades = []
        if pos_res.status_code == 200:
            for p in pos_res.json():
                if p.get('productType') == 'INTRADAY' and abs(int(float(p.get('netQty', 0)))) > 0:
                    open_trades.append(p)

        # 1. रिस्क मैनेजमेंट (पोजीशन ओपन होने पर)
        if open_trades:
            for pos in open_trades:
                sym = pos['tradingSymbol']
                sec_id = pos['securityId']
                net_qty = int(float(pos['netQty']))
                ltp = float(pos.get('lastPrice', pos.get('ltp', 0)))
                is_long = net_qty > 0
                entry_price = float(pos['buyAvg']) if is_long else float(pos['sellAvg'])
                
                pnl_pct = ((ltp - entry_price) / entry_price) * 100 if is_long else ((entry_price - ltp) / entry_price) * 100
                exit_side = "SELL" if is_long else "BUY"
                
                action = None
                if pnl_pct <= -1.0: action = "🚨 1% SL HIT"
                elif pnl_pct >= 3.5: action = "🎯 3.5% TARGET HIT"
                
                if action:
                    payload = {
                        "dhanClientId": CLIENT_ID, "transactionType": exit_side, "exchangeSegment": "NSE_EQ",
                        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                        "quantity": abs(net_qty), "securityId": str(sec_id), "tradingSymbol": sym, "price": 0
                    }
                    requests.post("https://api.dhan.co/orders", headers=headers, json=payload)
                    send_telegram(f"{action}\n✅ *{sym}* क्लोज किया गया।\n📊 PnL: {pnl_pct:.2f}%")
            return 

        # 2. नया ट्रेड खोजना (अधिकतम 2 ट्रेड लिमिट)
        if len(mem["trades_taken"]) >= 2: return

        try:
            url = "https://images.dhan.co/api-data/api-scrip-master.csv"
            df = pd.read_csv(url, low_memory=False)
            df_eq = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') & (df['SEM_SERIES'] == 'EQ')]
            id_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_SMST_SECURITY_ID']))
            symbol_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_TRADING_SYMBOL']))
        except: return

        for s in WATCHLIST:
            if s in mem["trades_taken"]: continue 
            sec_id = id_map.get(s)
            exact_sym = symbol_map.get(s)
            if not sec_id or not exact_sym: continue

            try:
                df_stk = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
                if len(df_stk) < 2: continue

                ltp = df_stk['Close'].iloc[-1]
                open_p = df_stk['Open'].iloc[0]
                change = ((ltp - open_p) / open_p) * 100

                if change > 1.5 or change < -1.5:
                    side = "BUY" if change > 1.5 else "SELL"
                    qty = max(1, int((cash * 5) / ltp))
                    
                    payload = {
                        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
                        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                        "quantity": qty, "securityId": str(sec_id), "tradingSymbol": str(exact_sym), "price": 0
                    }
                    res = requests.post("https://api.dhan.co/orders", headers=headers, json=payload)
                    
                    if res.status_code in [200, 201]:
                        send_telegram(f"🔫 *SNIPER ENTRY (After 9:30)*\n📈 शेयर: {s}\n🔄 दिशा: {side}\n📦 क्वांटिटी: {qty}\n📊 मूव: {change:.2f}%")
                        mem["trades_taken"].append(s)
                        save_memory(mem)
                        break 
            except: continue

if __name__ == "__main__":
    try:
        main_engine()
    except Exception as e:
        send_telegram(f"🚨 *SYSTEM FATAL CRASH*\nएरर:\n`{e}`")
