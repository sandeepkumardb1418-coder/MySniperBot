import os, requests, pytz
from datetime import datetime
from brain import TradingBrain

CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
TG_BOT_TOKEN = str(os.environ.get("TELEGRAM_BOT_TOKEN")).strip()
TG_CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID")).strip()

HEADERS = {
    "access-token": TOKEN, 
    "client-id": CLIENT_ID, 
    "Content-Type": "application/json"
}

def send_telegram(text):
    """टेलीग्राम पर हर पल की जानकारी भेजना"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def manage_live_positions():
    """धन अकाउंट की लाइव पोजीशन पढ़ना और SL/Target काटना"""
    try:
        url = "https://api.dhan.co/positions"
        res = requests.get(url, headers=HEADERS, timeout=10)
        
        if res.status_code != 200:
            if res.status_code == 401:
                send_telegram("🚨 *TOKEN EXPIRED:* धन का टोकन एक्सपायर हो गया है। नया टोकन दें।")
            return False

        positions = res.json()
        active_trades = False

        for pos in positions:
            net_qty = int(float(pos.get('netQty', 0)))
            if net_qty != 0 and pos.get('productType') == 'INTRADAY':
                active_trades = True
                sym = pos['tradingSymbol']
                ltp = float(pos.get('lastPrice', pos.get('ltp', 0)))
                buy_avg = float(pos.get('buyAvg', 0))
                sell_avg = float(pos.get('sellAvg', 0))
                
                is_long = net_qty > 0
                entry_price = buy_avg if is_long else sell_avg
                
                # PnL Calculation
                if is_long:
                    pnl_pct = ((ltp - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - ltp) / entry_price) * 100

                action = None
                if pnl_pct <= -1.0: action = "🚨 1% STOP-LOSS HIT"
                elif pnl_pct >= 3.5: action = "🎯 3.5% TARGET HIT"

                # अगर SL या Target आ गया तो पोजीशन काटो
                if action:
                    exit_side = "SELL" if is_long else "BUY"
                    payload = {
                        "dhanClientId": CLIENT_ID, "transactionType": exit_side, "exchangeSegment": pos['exchangeSegment'],
                        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                        "quantity": abs(net_qty), "securityId": str(pos['securityId']), "tradingSymbol": sym, "price": 0
                    }
                    order_res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                    if order_res.status_code in [200, 201]:
                        send_telegram(f"{action}\n✅ *{sym}* की पोजीशन क्लोज कर दी गई है।\n📊 बुक किया गया PnL: {pnl_pct:.2f}%")
        
        return active_trades # True अगर कोई ट्रेड चल रहा है
    except Exception as e:
        send_telegram(f"⚠️ Position Fetch Error: {e}")
        return False

def main():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # मशीन के जागने का सबूत
    print(f"[{now.strftime('%H:%M:%S')}] सिस्टम बूट हो रहा है...")

    # समय की सख्त पाबंदी
    if now.hour < 9 or (now.hour == 9 and now.minute < 15) or now.hour >= 15:
        print("Market is closed. Sleeping.")
        return

    # सबसे पहले धन API से लाइव पोजीशन चेक करें और SL/Target मैनेज करें
    has_active_trades = manage_live_positions()

    # अगर पहले से ट्रेड चल रहा है, तो नया ट्रेड नहीं लेना है
    if has_active_trades:
        print("Active trade running. Holding position.")
        return

    # अगर कोई ट्रेड नहीं चल रहा है, तो 'Brain' को जगाएं
    print("No active trades. Scanning for High Probability Setups...")
    brain = TradingBrain()
    
    # टॉप लिक्विड स्टॉक्स की वॉचलिस्ट (Large Caps only for HFT logic)
    watchlist = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "BHARTIARTL", "ITC", "LT", "BAJFINANCE"]
    
    best_trade = brain.execute_blueprint(watchlist)

    if best_trade:
        sym = best_trade['symbol']
        sig = best_trade['signal']
        prob = best_trade['prob']
        
        # टेलीग्राम अलर्ट
        send_telegram(f"⚡ *SMART MONEY ALERT*\n📈 शेयर: {sym}\n🎯 दिशा: {sig}\n🧠 AI एक्यूरेसी: {prob*100:.1f}%\n*(Order execution Logic will trigger here)*")
        
        # (यहाँ आप धन में आर्डर लगाने का API POST रिक्वेस्ट डाल सकते हैं, जैसा आपने पहले किया था)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        send_telegram(f"🚨 *CRITICAL SYSTEM CRASH*\nमशीन रुक गई है। Error: {str(e)}")
