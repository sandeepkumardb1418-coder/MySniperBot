import os, time, requests, pytz, pandas as pd, yfinance as yf
from datetime import datetime

# नियम 1: क्रेडेंशियल्स (Secrets से सुरक्षित)
CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

# नियम 2: रिस्क पैरामीटर्स
LEVERAGE = 5
TARGET_PCT = 3.5
SL_PCT = 1.0

def get_market_sentiment():
    """नियम 3: GIFT Nifty & Global Sentiment Study"""
    try:
        # Nifty 50 और ग्लोबल मूड चेक
        nifty = yf.Ticker("^NSEI").history(period="2d")
        n_chg = ((nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]) / nifty['Close'].iloc[-2]) * 100
        return n_chg
    except: return 0

def sniper_radar_360():
    """नियम 4, 5: Nifty 500 Analyze (Both Side Gainers/Losers)"""
    try:
        f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
        cash = float(f_res.json().get('availabelBalance', 0))
        sentiment = get_market_sentiment()
        
        print(f"💰 बैलेंस: ₹{cash} | 🌍 सेंटीमेंट: {sentiment:.2f}%")

        # Nifty 500 स्कैन (नियम 5)
        symbols = pd.read_csv("https://archives.nseindia.com/content/indices/ind_nifty500list.csv")['Symbol'].tolist()
        
        best_pick = None
        for s in symbols[:300]: # रडार सिस्टम
            data = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
            if len(data) < 2: continue
            
            ltp = data['Close'].iloc[-1]
            change = ((ltp - data['Open'].iloc[0]) / data['Open'].iloc[0]) * 100
            
            # AI Self-Correction (नियम 5) - भारी वॉल्यूम और मोमेंटम
            if abs(change) >= 2.0 and data['Volume'].iloc[-1] > (data['Volume'].mean() * 1.8):
                # नियम 4: Gainers और Losers दोनों रडार पर
                side = "BUY" if change > 0 else "SELL"
                # सेंटीमेंट फिल्टर (AI Decision)
                if (side == "BUY" and sentiment < -0.5) or (side == "SELL" and sentiment > 0.5): continue
                
                best_pick = {"s": s, "p": ltp, "side": side}
                break 
        return best_pick, cash
    except: return None, 0

if __name__ == "__main__":
    ist = pytz.timezone('Asia/Kolkata')
    trade_done = 0
    
    while trade_done < 2:
        now = datetime.now(ist).strftime("%H:%M:%S")
        
        # नियम 8: पहला प्रहार 9:30 AM पर
        if trade_done == 0 and "09:30:00" <= now <= "10:00:00":
            pick, cash = sniper_radar_360()
            if pick:
                qty = int((cash * LEVERAGE) / pick['p'])
                payload = {"dhanClientId": CLIENT_ID, "transactionType": pick['side'], "exchangeSegment": "NSE_EQ",
                           "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty, "securityId": "11915", "price": 0}
                requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                print(f"🎯 नियम 8 सफल: {pick['s']} में प्रहार!")
                trade_done += 1
                time.sleep(3600) # नियम 7 के लिए इंतज़ार

        # नियम 7: बड़ा मौका मिलने पर दूसरा ट्रेड (दोपहर में)
        elif trade_done == 1 and "12:00:00" <= now <= "14:30:00":
            pick, cash = sniper_radar_360()
            if pick and abs(get_market_sentiment()) > 1.2: # Significant Surge
                qty = int((cash * LEVERAGE) / pick['p'])
                requests.post("https://api.dhan.co/orders", headers=HEADERS, json=payload)
                print(f"🎯 नियम 7 सफल: दूसरा बड़ा प्रहार!")
                trade_done = 2

        # नियम 6: मिनट बचाना (मार्केट आवर्स के बाद ऑटो-एग्जिट)
        if now > "15:15:00" or (trade_done >= 1 and abs(get_market_sentiment()) < 1.0):
            print("✅ नियम 6: मिनट बचाए जा रहे हैं। आज का काम पूरा।")
            break
        
        time.sleep(60) # हर मिनट रडार स्कैन
