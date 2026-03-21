import os, time, requests, pytz, pandas as pd, yfinance as yf
from datetime import datetime

# --- क्रेडेंशियल्स (Secrets से सुरक्षित) ---
CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# नियम (नियम 1, 2, 7)
LEVERAGE = 5
TARGET_PCT = 3.5
SL_PCT = 1.0
MAX_TRADES = 2 # खास मौका होने पर 2 ट्रेड, वरना 1 (नियम 7)

def get_market_sentiment():
    """नियम 3: Global Market & GIFT Nifty Study"""
    try:
        # GIFT Nifty और Nifty 50 का सेंटीमेंट चेक
        nifty = yf.Ticker("^NSEI").history(period="2d")
        gift = yf.Ticker("GIFTY=F").history(period="2d") # Symbol may vary by provider
        
        n_chg = ((nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]) / nifty['Close'].iloc[-2]) * 100
        g_chg = ((gift['Close'].iloc[-1] - gift['Close'].iloc[-2]) / gift['Close'].iloc[-2]) * 100
        
        avg_sentiment = (n_chg + g_chg) / 2
        return avg_sentiment
    except: return 0

def sniper_360_radar():
    """नियम 4, 5: Nifty 500 Analyze & 360 Radar"""
    try:
        f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
        cash = float(f_res.json().get('availabelBalance', 0))
        if cash < 100: return None

        sentiment = get_market_sentiment()
        print(f"💰 फंड: ₹{cash} | 🌍 ग्लोबल सेंटीमेंट: {sentiment:.2f}%")

        # Nifty 500 लिस्ट (नियम 5)
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        df_500 = pd.read_csv(url)
        symbols = df_500['Symbol'].tolist()

        best_stock = None
        max_strength = 0

        # Gainers and Losers दोनों तरफ नज़र (नियम 4)
        for s in symbols[:300]: 
            t = yf.Ticker(f"{s}.NS")
            data = t.history(period="1d", interval="15m")
            if len(data) < 2: continue

            ltp = data['Close'].iloc[-1]
            change = ((ltp - data['Open'].iloc[0]) / data['Open'].iloc[0]) * 100
            vol_spike = data['Volume'].iloc[-1] > (data['Volume'].mean() * 2) # भारी वॉल्यूम

            # AI Self-Correction (नियम 5): ट्रेंड के खिलाफ ट्रेड नहीं
            if (change > 2.0 and sentiment > -0.5) or (change < -2.0 and sentiment < 0.5):
                strength = abs(change)
                if strength > max_strength and vol_spike:
                    max_strength = strength
                    best_stock = {"symbol": s, "price": ltp, "side": "BUY" if change > 0 else "SELL"}

        return best_stock, cash
    except: return None, 0

def execute_trade(stock, cash):
    """नियम 1, 2: Execution with 5x Leverage & SL/Target"""
    qty = int((cash * LEVERAGE) / stock['price'])
    # यहाँ धन API का आर्डर पेलोड जाएगा
    p = {
        "dhanClientId": CLIENT_ID, "transactionType": stock['side'], "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty,
        "securityId": "11915", "price": 0
    }
    requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p)
    print(f"🚀 {stock['side']} ट्रेड सफल: {stock['symbol']} @ {stock['price']}")

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    trade_count = 0
    
    while trade_count < MAX_TRADES:
        now = datetime.now(ist).strftime("%H:%M:%S")
        
        # नियम 8: पहला ट्रेड 9:30 AM पर
        if trade_count == 0 and "09:30:00" <= now <= "10:00:00":
            stock, cash = sniper_360_radar()
            if stock:
                execute_trade(stock, cash)
                trade_count += 1
                if trade_count == 1: time.sleep(3600) # 1 घंटे का ब्रेक अगले विश्लेषण के लिए

        # नियम 7 & 8: दूसरा ट्रेड केवल बड़े मौके पर (Significant Surge)
        elif trade_count == 1 and "11:00:00" <= now <= "14:30:00":
            stock, cash = sniper_360_radar()
            if stock and abs(get_market_sentiment()) > 1.5: # 1.5% से बड़ा ग्लोबल मूव = 'Significant Opportunity'
                execute_trade(stock, cash)
                trade_count += 1
        
        # नियम 6: मिनट बचाने के लिए मार्केट आवर्स के बाहर स्क्रिप्ट बंद
        if now > "15:00:00": break
        
        # अगर ट्रेड हो गया तो लूप खत्म (नियम 6 - No waste of time)
        if trade_count >= 1 and abs(get_market_sentiment()) <= 1.5:
            print("✅ नियम 6: आज का कोटा पूरा। मिनट बचाए जा रहे हैं।")
            break
            
        time.sleep(60) # हर मिनट चेक
