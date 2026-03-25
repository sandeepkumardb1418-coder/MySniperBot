import yfinance as yf
import pandas as pd

class TradingBrain:
    def __init__(self):
        self.min_prob = 0.88 

    def analyze_stock(self, symbol):
        try:
            df = yf.download(f"{symbol}.NS", period="5d", interval="15m", progress=False)
            if df.empty or len(df) < 25: 
                return None
            
            # Warning खत्म करने के लिए .values[0] या सीधे इंडेक्सिंग का उपयोग
            curr_price = float(df['Close'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            
            swing_high = float(df['High'].iloc[-15:-1].max())
            swing_low = float(df['Low'].iloc[-15:-1].min())
            avg_vol = float(df['Volume'].iloc[-15:-1].mean())
            
            # High Probability Logic
            if curr_price > swing_high and curr_vol > (avg_vol * 1.8):
                return "BUY"
            elif curr_price < swing_low and curr_vol > (avg_vol * 1.8):
                return "SELL"
                
            return None
        except Exception as e:
            return None
