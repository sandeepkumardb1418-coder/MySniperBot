import os, requests, yfinance as yf

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def place_order_final(symbol, qty, side):
    """बिना किसी फालतू डेटा के सीधा प्रहार"""
    url = "https://api.dhan.co/orders"
    
    # तकनीकी सुधार: सिर्फ Security ID का उपयोग (यही धन को सबसे ज़्यादा पसंद है)
    ids = {"ANANDRATHI": "13637", "ZOMATO": "5097", "TATASTEEL": "3499", "AWL": "18096"}
    sec_id = ids.get(symbol)
    
    if not sec_id: return

    payload = {
        "dhanClientId": CLIENT_ID,
        "transactionType": side,
        "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY",
        "orderType": "MARKET",
        "quantity": int(qty),
        "securityId": sec_id,
        "price": 0
    }
    
    res = requests.post(url, headers=HEADERS, json=payload)
    # अगर यहाँ 200 आया, तो मतलब सौदा आपके मोबाइल ऐप में दिख गया!
    print(f"📡 {symbol} | Response: {res.status_code} | {res.text}")

def execution_engine():
    # फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    cash = float(f_res.json().get('availabelBalance', 0))
    print(f"💰 फंड: ₹{cash}")

    # सिर्फ आनंद राठी पर फोकस (क्योंकि वह गिर रहा है और हमारा शिकार है)
    target = "ANANDRATHI"
    df = yf.Ticker(f"{target}.NS").history(period="1d", interval="5m")
    
    if not df.empty:
        ltp = df['Close'].iloc[-1]
        change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
        print(f"📊 {target} भाव: {ltp} | बदलाव: {change:.2f}%")

        # अगर 1% से ज़्यादा गिरा है, तो सीधा SELL (शॉर्ट सेल)
        if change < -1.0:
            qty = int((cash * 4) / ltp)
            place_order_final(target, qty, "SELL")

if __name__ == "__main__":
    execution_engine()
