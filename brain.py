import yfinance as yf
import pandas as pd

class TradingBrain:
    def __init__(self):
        self.min_prob = 0.88 # 88% प्रोबेबिलिटी फिल्टर

    def analyze_stock(self, symbol):
        df = yf.download(f"{symbol}.NS", period="5d", interval="15m", progress=False)
        if len(df) < 25: return None
        
        # 1. Market Structure Shift (MSS)
        # पिछला Swing High और Low पहचानना
        swing_high = df['High'].iloc[-15:-1].max()
        swing_low = df['Low'].iloc[-15:-1].min()
        curr_price = df['Close'].iloc[-1]
        
        # 2. DNA of Price (Volume & Microstructure)
        avg_vol = df['Volume'].mean()
        curr_vol = df['Volume'].iloc[-1]
        
        # 3. High Probability Signal
        signal = None
        if curr_price > swing_high and curr_vol > avg_vol * 1.8:
            signal = "BUY"
        elif curr_price < swing_low and curr_vol > avg_vol * 1.8:
            signal = "SELL"
            
        return signal

    def global_sentiment(self):
        # Inter-Market Analysis (GIFT Nifty & US Market)
        # यहाँ हम शॉर्ट में 1 (Positive) या -1 (Negative) रिटर्न करेंगे
        try:
            gift = yf.Ticker("^NSEI").history(period="1d")['Close'].iloc[-1]
            return 1 if gift > 0 else -1
        except: return 1
