import os, requests, json, time, pandas as pd, yfinance as yf
from datetime import datetime
import pytz # इंडियन टाइम के लिए

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
DEFAULT_ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
TELEGRAM_BOT_TOKEN = str(os.environ.get("TELEGRAM_BOT_TOKEN")).strip()
TELEGRAM_CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID")).strip()

# इंडियन टाइमज़ोन सेटअप
IST = pytz.timezone('Asia/Kolkata')

# Nifty 500 के टॉप 150 हाई-वॉल्यूम स्टॉक्स (गिटहब टाइमआउट बचाने के लिए 150 बेस्ट हैं)
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

MEMORY_FILE = "memory.json"

# --- 📱 टेलीग्राम संचार ---
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

def get_dhan_token_from_telegram():
    """टेलीग्राम चैट से टोकन ढूँढना"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res.get("ok"):
            messages = res["result"]
            for msg in reversed(messages):
                text = msg.get("message", {}).get("text", "")
                if text.startswith("TOKEN:"):
                    return text.replace("TOKEN:", "").strip()
    except Exception as e:
        send_telegram_message(f"⚠️ टोकन सर्वर कनेक्ट एरर: {e}")
    return DEFAULT_ACCESS_TOKEN

# --- 🧠 मेमोरी मैनेजमेंट ---
def load_memory():
    today = datetime.now(IST).strftime('%Y-%m-%d')
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                memory = json.load(f)
                if memory.get("date") == today:
                    return memory
        except: pass
    
    return {
        "date": today, "pre_market_sent": False, "eod_sent": False, 
        "hourly_sent": [], "traded_symbols": [], "open_trades_high_pnl": {} 
    }

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f)

# --- 🛠 धन API टूल्स ---
def fetch_dhan_master_ids():
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        df_eq = df[(df['SEM_EXM_EXCH_ID'] == 'NSE') & (df['SEM_SERIES'] == 'EQ')]
        id_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_SMST_SECURITY_ID']))
        symbol_map = dict(zip(df_eq['SEM_CUSTOM_SYMBOL'], df_eq['SEM_TRADING_SYMBOL']))
        return id_map, symbol_map
    except: return {}, {}

def execute_exit_order(symbol, sec_id, qty, side, reason, headers):
    payload = {
        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
        "quantity": int(qty), "securityId": str(sec_id), "tradingSymbol": symbol, "price": 0
    }
    try:
        res = requests.post("https://api.dhan.co/orders", headers=headers, json=payload)
        if res.status_code in [200, 201]:
            send_telegram_message(f"⚡ *EXIT SUCCESS*\n\nकारण: {reason}\nशेयर: {symbol}\n✅ सौदा काट दिया गया है।")
            return True
        else:
            send_telegram_message(f"❌ *EXIT ERROR*\n{symbol} कटने में फेल: {res.text}")
    except Exception as e:
        send_telegram_message(f"❌ *SYSTEM ERROR*\n{e}")
    return False

# --- 🛡 रिस्क और ट्रेलिंग मैनेजर ---
def manage_risk(headers, memory):
    res = requests.get("https://api.dhan.co/positions", headers=headers)
    if res.status_code != 200: return False

    open_trades_count = 0
    for pos in res.json():
        if int(float(pos.get('netQty', 0))) != 0 and pos.get('productType') == 'INTRADAY':
            open_trades_count += 1
            symbol = pos['tradingSymbol']
            sec_id = pos['securityId']
            net_qty = int(float(pos['netQty']))
            ltp = float(pos.get('lastPrice', pos.get('ltp', 0))) 
            
            is_long = net_qty > 0
            entry_price = float(pos['buyAvg']) if is_long else float(pos['sellAvg'])
            pnl_pct = ((ltp - entry_price) / entry_price) * 100 if is_long else ((entry_price - ltp) / entry_price) * 100
            exit_side = "SELL" if is_long else "BUY"
            abs_qty = abs(net_qty)

            # Highest PnL अपडेट करना (ट्रेलिंग के लिए)
            high_pnl = memory["open_trades_high_pnl"].get(symbol, 0)
            if pnl_pct > high_pnl:
                memory["open_trades_high_pnl"][symbol] = pnl_pct
                high_pnl = pnl_pct

            # 🚨 1% स्टॉप लॉस
            if pnl_pct <= -1.0:
                if execute_exit_order(symbol, sec_id, abs_qty, exit_side, "🚨 1% Stop-Loss Hit", headers):
                    memory["open_trades_high_pnl"].pop(symbol, None)
                    
            # 🎯 3.5% टारगेट
            elif pnl_pct >= 3.5:
                if execute_exit_order(symbol, sec_id, abs_qty, exit_side, "🎯 3.5% Target Hit", headers):
                    memory["open_trades_high_pnl"].pop(symbol, None)
                    
            # 🛡 स्मार्ट ट्रेलिंग: अगर 1.5% के पार जाकर वापस 0.5% पर गिरे तो एग्जिट (Cost-to-Cost+)
            elif high_pnl >= 1.5 and pnl_pct <= 0.5:
                if execute_exit_order(symbol, sec_id, abs_qty, exit_side, "🛡 Trailing SL Hit (Profit Locked)", headers):
                    memory["open_trades_high_pnl"].pop(symbol, None)

    save_memory(memory)
    return open_trades_count > 0 # Returns True if any trade is open

# --- 🚀 मुख्य इंजन ---
def main_engine():
    memory = load_memory()
    now = datetime.now(IST)
    current_hour = now.hour
    
    access_token = get_dhan_token_from_telegram()
    headers = {"access-token": access_token, "client-id": CLIENT_ID, "Content-Type": "application/json"}

    # 1. 🌅 प्री-मार्केट समरी (9:00 AM - 9:15 AM)
    if not memory["pre_market_sent"] and current_hour == 9 and now.minute <= 15:
        f_res = requests.get("https://api.dhan.co/fundlimit", headers=headers)
        if f_res.status_code == 200:
            funds = f_res.json().get('availabelBalance', 0)
            send_telegram_message(f"🌅 *PRE-MARKET OBSERVATION*\n\n✅ सिस्टम ऑनलाइन है।\n💰 कैपिटल: ₹{funds}\n🤖 मशीन तैयार है।")
            memory["pre_market_sent"] = True
            save_memory(memory)
        elif f_res.status_code in [401, 403]:
            send_telegram_message("🚨 *TOKEN EXPIRED*\nधन सर्वर कनेक्ट नहीं हो रहा। टेलीग्राम पर `TOKEN: आपका_टोकन` भेजें।")
        return

    # 2. 🌙 EOD रिपोर्ट (3:20 PM के बाद)
    if not memory["eod_sent"] and (current_hour > 15 or (current_hour == 15 and now.minute >= 20)):
        trades = len(memory["traded_symbols"])
        send_telegram_message(f"🌙 *EOD REPORT*\n\n🏁 मार्केट क्लोज।\n📊 आज के कुल ट्रेड: {trades}\n💤 सिस्टम स्लीप मोड में।")
        memory["eod_sent"] = True
        save_memory(memory)
        return

    # 3. ⏱ हर घंटे की रिपोर्ट
    if 10 <= current_hour <= 14 and current_hour not in memory["hourly_sent"] and now.minute <= 15:
        send_telegram_message(f"⏱ *HOURLY UPDATE ({current_hour}:00)*\n\n✅ मशीन लाइव है और बाज़ार स्कैन कर रही है।\nलॉस/प्रॉफिट मैनेजर एक्टिव है।")
        memory["hourly_sent"].append(current_hour)
        save_memory(memory)

    # 4. 🛑 ट्रेडिंग लॉजिक (9:15 AM - 3:15 PM)
    if (current_hour == 9 and now.minute >= 15) or (10 <= current_hour <= 14) or (current_hour == 15 and now.minute <= 15):
        
        # सबसे पहले ओपन पोजीशन का रिस्क मैनेज करो
        is_trade_open = manage_risk(headers, memory)

        if is_trade_open:
            return # अगर ट्रेड ओपन है, तो नया ट्रेड मत खोजो (Overtrading Lock)

        if len(memory["traded_symbols"]) >= 2:
            return # दिन के 2 ट्रेड पूरे

        # फंड चेक और 5x लेवरेज कैलकुलेशन
        f_res = requests.get("https://api.dhan.co/fundlimit", headers=headers)
        if f_res.status_code != 200: return
        cash = float(f_res.json().get('availabelBalance', 0))
        if cash < 100: return

        id_map, symbol_map = fetch_dhan_master_ids()
        if not id_map: return

        # शिकार खोजना (Sniper)
        for s in WATCHLIST:
            if s in memory["traded_symbols"]: continue

            sec_id = id_map.get(s)
            exact_sym = symbol_map.get(s)
            if not sec_id or not exact_sym: continue

            try:
                df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
                if len(df) < 2: continue
                
                ltp = df['Close'].iloc[-1]
                open_p = df['Open'].iloc[0]
                change = ((ltp - open_p) / open_p) * 100

                # 🚀 स्नाइपर स्ट्रेटजी (1.5% का तगड़ा ब्रेकआउट)
                if change > 1.5 or change < -1.5:
                    side = "BUY" if change > 1.5 else "SELL"
                    qty = int((cash * 5) / ltp) # 5x लेवरेज
                    if qty < 1: qty = 1 
                    
                    payload = {
                        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
                        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                        "quantity": qty, "securityId": str(sec_id), "tradingSymbol": str(exact_sym), "price": 0
                    }
                    res = requests.post("https://api.dhan.co/orders", headers=headers, json=payload)
                    
                    if res.status_code in [200, 201]:
                        memory["traded_symbols"].append(s)
                        save_memory(memory)
                        send_telegram_message(f"🎯 *SNIPER ENTRY*\n\n📈 शेयर: {s}\n🚀 मूव: {change:.2f}%\n✅ 5x लेवरेज के साथ आर्डर लगा!")
                        break # एक बार में एक ट्रेड
                    elif res.status_code in [401, 403]:
                        send_telegram_message("🚨 *ORDER REJECTED: TOKEN ISSUE*\nटेलीग्राम पर नया टोकन भेजें।")
                        break
            except: continue

if __name__ == "__main__":
    try:
        main_engine()
    except Exception as e:
        send_telegram_message(f"🚨 *CRITICAL CRASH*\nमशीन क्रैश हो गई है:\n`{e}`")
