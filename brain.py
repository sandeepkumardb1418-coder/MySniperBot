import yfinance as yf
import pandas as pd
import numpy as np

class TradingBrain:
    def __init__(self):
        self.min_prob = 0.90 # 90% से कम की एक्यूरेसी पर ट्रेड नहीं लेगा
        
    def check_global_sentiment(self):
        """Inter-Market Analysis: ग्लोबल कोरिलेशन (Nifty & US Markets)"""
        try:
            # ^NSEI (Nifty 500/Nifty 50 का प्रॉक्सी)
            nifty = yf.download("^NSEI", period="5d", progress=False)
            if nifty.empty: return "NEUTRAL"
            
            trend = "BULLISH" if float(nifty['Close'].iloc[-1]) > float(nifty['Close'].iloc[-2]) else "BEARISH"
            return trend
        except:
            return "NEUTRAL"

    def analyze_microstructure(self, symbol):
        """Market Microstructure, MSS & HFT Liquidity Tracking"""
        try:
            df = yf.download(f"{symbol}.NS", period="5d", interval="15m", progress=False)
            if df.empty or len(df) < 20: 
                return "IGNORE", 0
                
            curr_price = float(df['Close'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            
            # पिछले 10 कैंडल्स का स्ट्रक्चर (MSS)
            recent_high = float(df['High'].iloc[-10:-1].max())
            recent_low = float(df['Low'].iloc[-10:-1].min())
            avg_vol = float(df['Volume'].iloc[-10:-1].mean())
            
            # Alternative Data / Volume Spikes (बड़े प्लेयर्स की एंट्री)
            vol_spike = curr_vol > (avg_vol * 2.0) # 2 गुना से ज्यादा वॉल्यूम
            
            if curr_price > recent_high and vol_spike:
                return "BUY", 0.95
            elif curr_price < recent_low and vol_spike:
                return "SELL", 0.92
                
            return "WAIT", 0.50
        except Exception as e:
            return "ERROR", 0

    def execute_blueprint(self, watchlist):
        """High Probability Trade Plan"""
        global_trend = self.check_global_sentiment()
        best_trade = None
        highest_prob = 0
        
        for stock in watchlist:
            signal, prob = self.analyze_microstructure(stock)
            
            # ग्लोबल ट्रेंड के साथ अलाइनमेंट (Smart Money Concept)
            if signal == "BUY" and global_trend == "BULLISH" and prob > self.min_prob:
                if prob > highest_prob:
                    best_trade = {"symbol": stock, "signal": signal, "prob": prob}
                    highest_prob = prob
                    
            elif signal == "SELL" and global_trend == "BEARISH" and prob > self.min_prob:
                if prob > highest_prob:
                    best_trade = {"symbol": stock, "signal": signal, "prob": prob}
                    highest_prob = prob
                    
        return best_trade
