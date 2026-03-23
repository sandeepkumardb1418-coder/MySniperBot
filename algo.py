def sniper_360_scan():
    cash = get_dhan_funds()
    if cash < 100: 
        print("⚠️ ट्रेडिंग के लिए पर्याप्त फंड नहीं है या API ने फंड नहीं बताया। सिस्टम बंद हो रहा है।")
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
            
            # 👇 यहाँ 2.5 की जगह 1.5 कर दिया गया है (ढील दी गई है)
            vol_spike = df['Volume'].iloc[-1] > (vol_avg * 1.5)
            rsi = df['RSI'].iloc[-1]

            # BUY कंडीशन (तेज़ी के लिए)
            if change >= 2.0 and vol_spike and (60 < rsi < 75) and sentiment > -0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 शिकार मिला: {s} | BUY | RSI: {rsi:.1f} | Qty: {qty}")
                place_strict_orders(s, ltp, qty, "BUY")
                return  

            # SELL कंडीशन (मंदी के लिए)
            elif change <= -2.0 and vol_spike and (25 < rsi < 40) and sentiment < 0.2:
                qty = int((cash * leverage) / ltp)
                print(f"🎯 शिकार मिला: {s} | SELL | RSI: {rsi:.1f} | Qty: {qty}")
                place_strict_orders(s, ltp, qty, "SELL")
                return

        except Exception as e: continue
