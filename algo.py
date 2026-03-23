import os, requests, yfinance as yf

# --- क्रेडेंशियल्स ---
CLIENT_ID = str(os.environ.get("DHAN_CLIENT_ID")).strip()
ACCESS_TOKEN = str(os.environ.get("DHAN_ACCESS_TOKEN")).strip()
HEADERS = {"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Content-Type": "application/json"}

def fire_order(sec_id, qty, side):
    """सबसे शुद्ध आर्डर: सिर्फ ID और Quantity"""
    url = "https://api.dhan.co/orders"
    payload = {
        "dhanClientId": CLIENT_ID,
        "transactionType": side,
        "exchangeSegment": "NSE_EQ",
        "productType": "INTRADAY",
        "orderType": "MARKET",
        "quantity": int(qty),
        "securityId": str(sec_id), # सटीक ID
        "price": 0
    }
    res = requests.post(url, headers=HEADERS, json=payload)
    print(f"📡 ID: {sec_id} | Status: {res.status_code} | Result: {res.text}")

def execution_engine():
    # फंड चेक
    f_res = requests.get("https://api.dhan.co/fundlimit", headers=HEADERS)
    cash = float(f_res.json().get('availabelBalance', 0))
    print(f"💰 फंड: ₹{cash}")

    # टारगेट: आनंद राठी (ID: 13637) - जो आज गिर रहा है
    target_id = "13637" 
    target_symbol = "ANANDRATHI.NS"
    
    df = yf.Ticker(target_symbol).history(period="1d", interval="5m")
    if not df.empty:
        ltp = df['Close'].iloc[-1]
        change = ((ltp - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
        print(f"📊 भाव: {ltp} | बदलाव: {change:.2f}%")

        # आक्रामक शर्त: 1% गिरते ही सीधा SELL
        if change < -1.0:
            qty = int((cash * 4) / ltp)
            fire_order(target_id, qty, "SELL")

if __name__ == "__main__":
    execution_engine()
