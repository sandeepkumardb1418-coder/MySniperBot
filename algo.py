import os, time, requests, pytz, pandas as pd, yfinance as yf
from datetime import datetime

# क्रेडेंशियल्स (Secrets से आएंगे, पब्लिक रेपो में भी 100% सुरक्षित)
CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("DHAN_ACCESS_TOKEN")
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def ai_sniper_trade():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).strftime("%H:%M:%S")
    
    # AI नियम: केवल मार्केट ऑवर में काम करेगा (9:30 AM से 3:00 PM)
    if not ("09:30:00" <= now <= "15:00:00"): return

    try:
        f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
        cash = float(f_res.json().get('availabelBalance', 0))
        
        # निफ्टी 500 स्कैन (AI Logic - Momentum + Volume)
        symbols = pd.read_csv("https://archives.nseindia.com/content/indices/ind_nifty500list.csv")['Symbol'].tolist()
        for s in symbols[:200]: # टॉप 200 पर फोकस
            df = yf.Ticker(f"{s}.NS").history(period="1d", interval="15m")
            if len(df) < 2: continue
            
            ltp = df['Close'].iloc[-1]
            change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
            
            # AI प्रहार: AWL जैसे 2% मूव और भारी वॉल्यूम पर
            if abs(change) >= 2.0 and df['Volume'].iloc[-1] > (df['Volume'].mean() * 1.5):
                qty = int((cash * 5) / ltp) # 5x लेवरेज
                p = {"dhanClientId": CLIENT_ID, "transactionType": "BUY" if change > 0 else "SELL",
                     "exchangeSegment": "NSE_EQ", "productType": "INTRADAY", "orderType": "MARKET", 
                     "quantity": qty, "securityId": "11915", "price": 0}
                requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p)
                print(f"✅ ट्रेड सफल: {s}")
                return True
        return False
    except: return False

if __name__ == "__main__":
    ai_sniper_trade()
