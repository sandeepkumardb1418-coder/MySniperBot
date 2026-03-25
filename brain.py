import yfinance as yf
import pandas as pd

class TradingBrain:
    def __init__(self):
        self.min_prob = 0.88 

    def analyze_stock(self, symbol):
        try:
            # डेटा डाउनलोड करना
            df = yf.download(f"{symbol}.NS", period="5d", interval="15m", progress=False)
            if df.empty or len(df) < 25: 
                return None
            
            # .iloc[-1] का इस्तेमाल ताकि सिर्फ एक नंबर मिले (अम्बुइटी खत्म)
            curr_price = float(df['Close'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            
            # पिछले 15 कैंडल्स का स्विंग हाई/लो
            swing_high = float(df['High'].iloc[-15:-1].max())
            swing_low = float(df['Low'].iloc[-15:-1].min())
            avg_vol = float(df['Volume'].iloc[-15:-1].mean())
            
            # MSS और वॉल्यूम डीएनए का लॉजिक
            if curr_price > swing_high and curr_vol > (avg_vol * 1.8):
                return "BUY"
            elif curr_price < swing_low and curr_vol > (avg_vol * 1.8):
                return "SELL"
                
            return None
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None
