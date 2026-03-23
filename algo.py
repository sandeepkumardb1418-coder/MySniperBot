def place_strict_orders(symbol, ltp, qty, side):
    """नियम: सख्त 1% स्टॉप लॉस आर्डर सीधा ब्रोकर के टर्मिनल पर"""
    try:
        # 1. मुख्य आर्डर (Entry)
        p_main = {
            "dhanClientId": CLIENT_ID, "transactionType": side, "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", "orderType": "MARKET", "quantity": qty,
            "securityId": "11915", "price": 0
        }
        res_main = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_main)
        print(f"📡 ब्रोकर का जवाब (Main): {res_main.text}") # यहाँ धन की असली बीमारी पता चलेगी
        
        # 2. 1% सख्त स्टॉप लॉस कैलकुलेशन
        if side == "BUY":
            sl_price = round(ltp - (ltp * (1.0 / 100)), 1)
            sl_side = "SELL"
        else:
            sl_price = round(ltp + (ltp * (1.0 / 100)), 1)
            sl_side = "BUY"
            
        # 3. स्टॉप लॉस आर्डर ब्रोकर को भेजना
        p_sl = {
            "dhanClientId": CLIENT_ID, "transactionType": sl_side, "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY", "orderType": "STOP_LOSS", "quantity": qty,
            "securityId": "11915", "price": 0, "triggerPrice": sl_price
        }
        res_sl = requests.post("https://api.dhan.co/orders", headers=HEADERS, json=p_sl)
        print(f"📡 ब्रोकर का जवाब (SL): {res_sl.text}")
        print(f"🛡️ 1% सख्त SL सेट किया गया: ₹{sl_price} पर।")
    except Exception as e:
        print(f"आर्डर लगाने में त्रुटि: {e}")
