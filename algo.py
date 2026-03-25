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

def get_account_summary():
    """धन खाते से बैलेंस और पेंडिंग आर्डर निकालना"""
    funds = "Error"
    pending_orders = 0
    
    try:
        # फंड चेक
        res_funds = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS, timeout=5)
        if res_funds.status_code == 200:
            funds = res_funds.json().get("availabelBalance", 0)
            
        # पेंडिंग आर्डर चेक
        res_orders = requests.get("https://api.dhan.co/orders", headers=HEADERS, timeout=5)
        if res_orders.status_code == 200:
            orders = res_orders.json()
            pending_orders = sum(1 for o in orders if o.get('orderStatus') == 'PENDING')
    except:
        pass
    return funds, pending_orders

def manage_live_positions():
    """पोजीशन चेक करना और SL/Target काटना"""
    url = "https://api.dhan.co/positions"
    active_sym = "कोई नहीं"
    current_pnl = 0.0
    has_active = False
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 401: return "TOKEN_EXPIRED", 0, False
        if res.status_code != 200: return active_sym, current_pnl, False
            
        positions = res.json()
        
        for pos in positions:
            net_qty = int(float(pos.get('netQty', 0)))
            if net_qty != 0 and pos.get('productType') == 'INTRADAY':
                has_active = True
                active_sym = pos['tradingSymbol']
                
                ltp = float(pos.get('lastPrice', pos.get('ltp', 0)))
                if ltp <= 0: continue # Zero LTP Bug Fix
                
                buy_avg = float(pos.get('buyAvg', 0))
                sell_avg = float(pos.get('sellAvg', 0))
                is_long = net_qty > 0
                entry_price = buy_avg if is_long else sell_avg
                
                # PnL Calculation
                pnl_pct = ((ltp - entry_price) / entry_price) * 100 if is_long else ((entry_price - ltp) / entry_price) * 100
                current_pnl = pnl_pct
                
                # Exit Logic
                action = None
                if pnl_pct <= -1.0: action = "🚨 *1% STOP-LOSS HIT*"
                elif pnl_pct >= 3.5: action = "🎯 *3.5% TARGET HIT*"

                if action:
                    exit_side = "SELL" if is_long else "BUY"
                    payload = {
                        "dhanClientId": CLIENT_ID, "transactionType": exit_side, "exchangeSegment": pos.get('exchangeSegment', 'NSE_EQ'),
                        "productType": "INTRADAY", "orderType": "MARKET", "validity": "DAY",
                        "quantity": abs(net_qty), "securityId": str(pos.get('securityId', '')), "tradingSymbol": active_sym, "price": 0
                    }
                    order_res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                    if order_res.status_code in [200, 201]:
                        send_telegram(f"{action}\n✅ *{active_sym}* पोजीशन क्लोज्ड।\n📊 बुक PnL: `{pnl_pct:.2f}%`")
                        has_active = False
                        active_sym = "कोई नहीं"
        
        return active_sym, current_pnl, has_active
    except Exception as e:
        return f"Error: {str(e)[:20]}", 0, False

def main():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    time_str = now.strftime('%I:%M %p')
    
    # समय की पाबंदी
    if not (9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 15)):
        return

    # 1. डेटा कलेक्ट करना
    funds, pending_orders = get_account_summary()
    active_sym, current_pnl, has_active = manage_live_positions()
    
    if active_sym == "TOKEN_EXPIRED":
        send_telegram("🚨 *CRITICAL ERROR:* धन का टोकन एक्सपायर हो गया है। कृपया नया टोकन अपडेट करें।")
        return

    # 2. ट्रेडिंग ब्रेन और स्कैनिंग
    brain = TradingBrain()
    watchlist = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "SBIN", "INFY", "ITC", "BHARTIARTL"]
    best_trade, global_trend = brain.get_best_trade(watchlist)

    # 3. कारण तय करना कि आर्डर क्यों नहीं लिया
    reason = ""
    if has_active:
        reason = f"पहले से {active_sym} में ट्रेड चल रहा है। रूल के अनुसार एक बार में एक ही ट्रेड।"
    elif best_trade:
        reason = f"✅ ऑपरेटर सिग्नल मिल गया है! {best_trade['symbol']} में {best_trade['signal']} आर्डर लगाया जा रहा है।"
    else:
        reason = "किसी भी शेयर में 'ऑपरेटर वॉल्यूम (2x)' और '90% से ज्यादा एक्यूरेसी' वाला ब्रेकआउट नहीं मिला। पैसा सुरक्षित रखा गया है।"

    # 4. टेलीग्राम पर लाइव रिपोर्ट (डैशबोर्ड) भेजना
    dashboard = f"""📊 *AI SYSTEM REPORT* 📊
⏰ समय: {time_str}
📈 निफ्टी ट्रेंड: {global_trend}

💰 *बैलेंस / फंड:* ₹{funds}
📦 *लाइव पोजीशन:* {active_sym} (PnL: {current_pnl:.2f}%)
📝 *पेंडिंग आर्डर:* {pending_orders}

❓ *AI स्टेटस / अगला आर्डर:*
{reason}

🛡️ _मशीन 5 मिनट बाद फिर से स्कैन करेगी।_"""

    send_telegram(dashboard)

    # 5. अगर नया आर्डर मिला है, तो लगाओ
    if best_trade and not has_active:
        sym = best_trade['symbol']
        sig = best_trade['signal']
        payload = {
            "dhanClientId": CLIENT_ID, "transactionType": "BUY" if sig == "BUY" else "SELL", 
            "exchangeSegment": "NSE_EQ", "productType": "INTRADAY", "orderType": "MARKET", 
            "validity": "DAY", "quantity": 10, "securityId": "11536", "tradingSymbol": sym, "price": 0
        }
        res = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
        if res.status_code not in [200, 201]:
            send_telegram(f"❌ *ORDER FAILED:* {sym} में आर्डर रिजेक्ट हो गया। API Error: {res.text}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        send_telegram(f"🚨 *SYSTEM CRASH:* गिटहब मशीन में तकनीकी खराबी: {str(e)}")
