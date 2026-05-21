from flask import Flask
import ccxt
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv
import threading

# Load variables
load_dotenv()

app = Flask(__name__)

# Config
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
LEVERAGE = os.getenv('LEVERAGE', '15')
POSITION_SIZE = os.getenv('POSITION_SIZE', '50')

last_scan = None

def send_msg(text):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def get_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    gains, losses = 0, 0
    for i in range(1, period + 1):
        diff = prices[-i] - prices[-i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    if losses == 0: return 100
    return 100 - (100 / (1 + (gains / losses)))

def get_ema(prices, period):
    if len(prices) < period: return prices[-1]
    mult = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = (p - ema) * mult + ema
    return ema

def scan():
    global last_scan
    coins = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT", "LINK/USDT"]
    print("Scanning...")
    
    for coin in coins:
        try:
            ex = ccxt.binance({'options': {'defaultType': 'future'}})
            candles = ex.fetch_ohlcv(coin, '15m', limit=50)
            closes = [c[4] for c in candles]
            price = closes[-1]
            
            rsi = get_rsi(closes)
            ema7 = get_ema(closes, 7)
            ema25 = get_ema(closes, 25)
            
            score = 0
            if rsi < 30: score += 30
            if rsi > 70: score -= 30
            if ema7 > ema25: score += 20
            else: score -= 20
            
            if score >= 40:
                msg = f"🟢 LONG: {coin}\nPrice: {price}\nRSI: {rsi}\nTP: {price*1.05}"
                send_msg(msg)
            elif score <= -40:
                msg = f"🔴 SHORT: {coin}\nPrice: {price}\nRSI: {rsi}\nTP: {price*0.95}"
                send_msg(msg)
                
            time.sleep(1)
        except:
            continue
            
    last_scan = datetime.now()
    print("Scan done.")

def run_loop():
    while True:
        scan()
        time.sleep(300)

@app.route('/')
def home():
    return f"<h1>Bot Running!</h1><p>Last scan: {last_scan}</p>"

if __name__ == "__main__":
    threading.Thread(target=run_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)