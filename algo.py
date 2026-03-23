def place_strict_orders(symbol, ltp, qty, side):
    """सक्षम आर्डर: अब यह सीधा सिंबल के आधार पर ट्रेड करेगा"""
    try:
        # 1. सही Security ID ढूंढना (Dhan API के अनुसार)
        # नोट: लाइव ट्रेडिंग में हम सिंबल को सीधा इस्तेमाल कर रहे हैं
        p_main = {
            "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty,
            "tradingSymbol": f"{symbol}", # सीधा नाम का उपयोग
            "price": 0
        }
        
        print(f"🚀 {symbol} के लिए असली आर्डर भेजा जा रहा है...")
        res_main = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_main)
        
        # अगर रिजेक्ट हुआ तो कारण प्रिंट करेगा
        print(f"📡 ब्रोकर रिस्पॉन्स: {res_main.text}") 

        # 2. स्टॉप लॉस आर्डर
        sl_price = round(ltp * 0.99, 1) if side == "BUY" else round(ltp * 1.01, 1)
        p_sl = {
            "dhanClientId": CLIENT_ID, "transactionType": "SELL" if side == "BUY" else "BUY",
            "exchangeSegment": "NSE_EQ", "productType": "INTRADAY", "orderType": "STOP_LOSS",
            "quantity": qty, "tradingSymbol": f"{symbol}", "price": 0, "triggerPrice": sl_price
        }
        requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_sl)
        
    except Exception as e:
        print(f"❌ एरर: {e}")
