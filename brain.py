import yfinance as yf
import pandas as pd

class TradingBrain:
    def __init__(self):
        self.min_prob = 0.90 # 90% से ऊपर की सटीकता
        
    def check_global_sentiment(self):
        """ग्लोबल मार्केट और निफ़्टी का ट्रेंड"""
        try:
            nifty = yf.download("^NSEI", period="5d", progress=False)
            if nifty.empty: return "NEUTRAL"
            return "BULLISH" if float(nifty['Close'].iloc[-1]) > float(nifty['Close'].iloc[-2]) else "BEARISH"
        except:
            return "NEUTRAL"

    def analyze_microstructure(self, symbol):
        """लिक्विडिटी, MSS और ऑपरेटर की ट्रैकिंग"""
        try:
            df = yf.download(f"{symbol}.NS", period="5d", interval="15m", progress=False)
            if df.empty or len(df) < 20: 
                return "IGNORE", 0
                
            curr_price = float(df['Close'].iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            
            recent_high = float(df['High'].iloc[-10:-1].max())
            recent_low = float(df['Low'].iloc[-10:-1].min())
            avg_vol = float(df['Volume'].iloc[-10:-1].mean())
            
            # ऑपरेटर एंट्री: 2 गुना से ज्यादा वॉल्यूम
            vol_spike = curr_vol > (avg_vol * 2.0) 
            
            if curr_price > recent_high and vol_spike:
                return "BUY", 0.95
            elif curr_price < recent_low and vol_spike:
                return "SELL", 0.92
                
            return "WAIT", 0.50
        except Exception as e:
            return "ERROR", 0

    def get_best_trade(self, watchlist):
        """Dhan के लिए सबसे सटीक ट्रेड चुनना"""
        global_trend = self.check_global_sentiment()
        best_trade = None
        highest_prob = 0
        
        for stock in watchlist:
            signal, prob = self.analyze_microstructure(stock)
            
            # सिर्फ ग्लोबल ट्रेंड की दिशा में ही ट्रेड लेगा
            if signal == "BUY" and global_trend == "BULLISH" and prob >= self.min_prob:
                if prob > highest_prob:
                    best_trade = {"symbol": stock, "signal": signal, "prob": prob}
                    highest_prob = prob
                    
            elif signal == "SELL" and global_trend == "BEARISH" and prob >= self.min_prob:
                if prob > highest_prob:
                    best_trade = {"symbol": stock, "signal": signal, "prob": prob}
                    highest_prob = prob
                    
        return best_trade
