import os, requests, pytz
from datetime import datetime
from brain import TradingBrain

# Credentials
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID", "")).strip()
TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN", "")).strip()
TG_BOT_TOKEN = str(os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
TG_CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

HEADERS = {"access-token": TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def send_telegram(text):
    """हर अपडेट सीधा टेलीग्राम पर"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def get_live_positions():
    """धन अकाउंट चेक करना और SL/Target मैनेज करना"""
    url = "https://api.dhan.co/positions"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        
        # 1. टोकन एक्सपायर चेक
        if res.status_code == 401:
            send_telegram("🚨 *TOKEN EXPIRED:* धन का एक्सेस टोकन बदलें!")
            return None, True
            
        if res.status_code != 200:
            return None, False
            
        positions = res.json()
        active_trades = False
        
        for pos in positions:
            net_qty = int(float(pos.get('netQty', 0)))
            if net_qty != 0 and pos.get('productType') == 'INTRADAY':
                active_trades = True
                sym = pos['tradingSymbol']
                
                # 2. THE FIX: अगर API 0 भाव भेजता है, तो इग्नोर करो (फर्जी -100% PnL से बचाव)
                ltp = float(pos.get('lastPrice', pos.get('ltp', 0)))
                if ltp <= 0: continue 
                
                buy_avg = float(pos.get('buyAvg', 0))
                sell_avg = float(pos.get('sellAvg', 0))
                is_long = net_qty > 0
                entry_price = buy_avg if is_long else sell_avg
                
                # 3. सटीक PnL गणित
                pnl_pct = ((ltp - entry_price) / entry_price) * 100 if is_long else ((entry_price - ltp) / entry_price) * 100

                # 4. 1% SL या 3.5% Target
                action = None
                if pnl_pct <= -1.0: action = "🚨 *1% STOP-LOSS HIT*"
                elif pnl_pct >= 3.5: action = "🎯 *3.5% TARGET HIT*"

                if action:
                    exit_side = "SELL" if is_long else "BUY"
                    payload = {
                        "dhanClientId": CLIENT_ID, "transactionType": exit_side, "exchangeSegment": pos.get('exchangeSegment', 'NSE_EQ'),
                        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                        "quantity": abs(net_qty), "securityId": str(pos.get('securityId', '')), "tradingSymbol": sym, "price": 0
                    }
                    order_res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                    
                    if order_res.status_code in [200, 201]:
                        send_telegram(f"{action}\n✅ *{sym}* की पोजीशन क्लोज कर दी गई है।\n📊 बुक PnL: `{pnl_pct:.2f}%`\nभाव: ₹{ltp}")
                    else:
                        send_telegram(f"❌ *EXIT FAILED:*\nशेयर: {sym}\nAPI Error: {order_res.text}")
        
        return active_trades, False
    except Exception as e:
        send_telegram(f"⚠️ *Position Fetch Error:* {e}")
        return None, False

def place_new_order(sym, signal):
    """नया ट्रेड लेना और टेलीग्राम पर बताना"""
    qty = 10 # शेयर की क्वांटिटी 
    side = "BUY" if signal == "BUY" else "SELL"
    
    payload = {
        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
        "quantity": qty, "securityId": "11536", "tradingSymbol": sym, "price": 0
    }
    
    order_res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
    
    if order_res.status_code in [200, 201]:
        send_telegram(f"🚀 *AI SNIPER ENTRY*\n✅ शेयर: {sym}\n🎯 दिशा: {signal}\n📈 क्वांटिटी: {qty}")
    else:
        # अगर आर्डर नहीं लगता है तो भी टेलीग्राम पर बताएगा (Security ID मैपिंग के लिए)
        send_telegram(f"🔍 *AI SIGNAL FOUND* (Order Failed/Testing)\nशेयर: {sym}\nदिशा: {signal}\nAPI Msg: {order_res.text}")

def main():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # 9:15 AM से 3:15 PM तक ही काम करेगा
    if not (9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 15)):
        if now.hour == 9 and now.minute < 15: pass
        else: return

    # 1. धन अकाउंट की लाइव पोजीशन चेक करें
    has_active_trades, token_expired = get_live_positions()
    
    if token_expired: return 
    if has_active_trades: return # अगर पहले से ट्रेड चल रहा है तो नया मत लो

    # 2. अगर अकाउंट खाली है, तो नया हाई-क्वालिटी ट्रेड ढूंढो
    brain = TradingBrain()
    watchlist = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "SBIN", "INFY", "ITC", "BHARTIARTL"]
    
    best_trade = brain.get_best_trade(watchlist)

    # 3. अगर ट्रेड मिला, तो आर्डर मारो
    if best_trade:
        place_new_order(best_trade['symbol'], best_trade['signal'])

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        send_telegram(f"🚨 *CRITICAL BUG*\nमशीन क्रैश: {str(e)}")
