import os, requests, pytz, pandas as pd, numpy as np, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()

HEADERS = {
    "access-token": ACCESS_TOKEN,
    "client-id": CLIENT_ID,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# --- नियम ---
LEVERAGE = 5
SL_PCT = 1.0 

def get_market_sentiment():
    try:
        nifty = yf.Ticker("^NSEI").history(period="2d")
        return ((nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]) / nifty['Close'].iloc[-2]) * 100
    except: return 0

def calculate_ai_indicators(df):
    df['Change'] = df['Close'].diff()
    df['Gain'] = df['Change'].mask(df['Change'] < 0, 0.0)
    df['Loss'] = -df['Change'].mask(df['Change'] > 0, 0.0)
    df['Avg_Gain'] = df['Gain'].rolling(14).mean()
    df['Avg_Loss'] = df['Loss'].rolling(14).mean()
    rs = df['Avg_Gain'] / df['Avg_Loss']
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def get_dhan_funds():
    print("🔍 धन (Dhan) सर्वर से फंड की जानकारी ली जा रही है...")
    try:
        url = "https://api.dhan.co/fundlimit"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            print(f"❌ API Error ({res.status_code}): {res.text}")
            return 0
        cash = float(res.json().get('availabelBalance', 0))
        return cash
    except Exception as e:
        print(f"❌ सर्वर से जुड़ने में त्रुटि: {e}")
        return 0

def place_strict_orders(symbol, ltp, qty, side):
    try:
        p_main = {
            "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty,
            "securityId": "11915", "price": 0
        }
        print(f"🚀 {symbol} के लिए {side} आर्डर भेजा जा रहा है...")
        res_main = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_main)
        print(f"📡 ब्रोकर का जवाब (Main): {res_main.status_code} - {res_main.text}")
        
        sl_price = round(ltp - (ltp * (SL_PCT / 100)), 1) if side == "BUY" else round(ltp + (ltp * (SL_PCT / 100)), 1)
        sl_side = "SELL" if side == "BUY" else "BUY"
            
        p_sl = {
            "dhanClientId": CLIENT_ID, "transactionType": sl_side, "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", "orderType": "STOP_LOSS", "quantity": qty,
            "securityId": "11915", "price": 0, "triggerPrice": sl_price
        }
        res_sl = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_sl)
        print(f"📡 ब्रोकर का जवाब (SL): {res_sl.status_code} - {res_sl.text}")
        
    except Exception as e:
        print(f"❌ आर्डर लगाने में त्रुटि: {e}")

def exit_open_positions():
    """3 बजे से पहले पेनल्टी से बचने के लिए सभी ओपन ट्रेड काटना"""
    print("⏰ 2:45 PM हो चुके हैं! ब्रोकर की पेनल्टी से बचने के लिए ओपन पोजीशन काटी जा रही हैं...")
    try:
        res = requests.get("https://api.dhan.co/positions", headers=HEADERS)
        if res.status_code == 200:
            positions = res.json()
            closed_any = False
            for pos in positions:
                # कितनी क्वांटिटी खरीदी और बेची गई है, उसका अंतर (Net Qty) निकालना
                b_qty = float(pos.get('buyQty', 0))
                s_qty = float(pos.get('sellQty', 0))
                net_qty = b_qty - s_qty
                
                # अगर कोई इंट्राडे पोजीशन ओपन है
                if net_qty != 0 and pos.get('productType') == 'INTRADAY':
                    symbol = pos.get('tradingSymbol')
                    sec_id = pos.get('securityId')
                    exch = pos.get('exchangeSegment')
                    
                    side = "SELL" if net_qty > 0 else "BUY"
                    qty = int(abs(net_qty))
                    
                    p_exit = {
                        "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": exch,
                        "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty,
                        "securityId": sec_id, "price": 0
                    }
                    requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_exit)
                    print(f"✅ ब्रोकर पेनल्टी से बचाव: {symbol} की {qty} क्वांटिटी {side} कर दी गई है!")
                    closed_any = True
            
            if not closed_any:
                print("👍 कोई ओपन पोजीशन नहीं है। सब कुछ सुरक्षित है।")
        else:
            print(f"❌ पोजीशन चेक करने में एरर: {res.text}")
    except Exception as e:
        print(f"❌ पोजीशन काटने में त्रुटि: {e}")

def sniper_360_scan():
    cash = get_dhan_funds()
    if cash < 100: 
        print("⚠️ ट्रेडिंग के लिए पर्याप्त फंड नहीं है। सिस्टम बंद हो रहा है।")
        return

    sentiment = get_market_sentiment()
    leverage = 5 if abs(sentiment) > 0.5 else 3 
    print(f"✅ बैलेंस: ₹{cash} | 🌍 ग्लोबल मूड: {sentiment:.2f}% | ⚙️ लेवरेज: {leverage}x")

    symbols = pd.read_csv("https://archives.nseindia.com/content/indices/ind_nifty500list.csv")['Symbol'].tolist()
    
    for s in symbols[:200]:
        try:
            df = yf.Ticker(f"{s}.NS").history(period="5d", interval="15m")
            if len(df) < 15: continue
            
            df = calculate_ai_indicators(df)
            ltp = df['Close'].iloc[-1]
            change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
            
            vol_avg = df['Volume'].rolling(20).mean().iloc[-2]
            vol_spike = df['Volume'].iloc[-1] > (vol_avg * 1.5) 
            rsi = df['RSI'].iloc[-1]

            if change >= 2.0 and vol_spike and (60 < rsi < 75) and sentiment > -0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 शिकार मिला: {s} | BUY | RSI: {rsi:.1f} | Qty: {qty}")
                place_strict_orders(s, ltp, qty, "BUY")
                return  

            elif change <= -2.0 and vol_spike and (25 < rsi < 40) and sentiment < 0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 शिकार मिला: {s} | SELL | RSI: {rsi:.1f} | Qty: {qty}")
                place_strict_orders(s, ltp, qty, "SELL")
                return

        except Exception as e: continue
    
    print("🔍 रडार स्कैन पूरा हुआ, लेकिन 1.5x वॉल्यूम वाला कोई 'क्वालिटी शेयर' नहीं मिला।")

if __name__ == "__main__":
    print("🚀 AI स्नाइपर सिस्टम स्टार्ट हो रहा है...")
    
    # भारतीय समय (IST) चेक करना
    ist_now = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M")
    
    # नियम: 2:45 PM के बाद नया ट्रेड ब्लॉक और पोजीशन काटना (3:00 बजे से पहले)
    if ist_now >= "14:45" and ist_now <= "15:30":
        exit_open_positions()
    else:
        sniper_360_scan()
        
    print("✅ AI चेक पूरा हुआ।")
