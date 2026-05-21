from flask import Flask
import ccxt
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv
import threading

load_dotenv()

app = Flask(__name__)

# SOZLAMALAR
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
LEVERAGE = os.getenv('LEVERAGE', '15')
POSITION_SIZE = os.getenv('POSITION_SIZE', '50')

# GLOBAL O'ZGARUVCHILAR
last_scan_time = None

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains = 0
    losses = 0
    for i in range(1, period + 1):
        diff = prices[-i] - prices[-i-1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    if losses == 0:
        return 100
    rs = gains / losses
    return 100 - (100 / (1 + rs))

def get_ema(prices, period):
    if len(prices) < period:
        return prices[-1]    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def analyze_coin(symbol):
    try:
        exchange = ccxt.binance({'options': {'defaultType': 'future'}, 'timeout': 20000})
        
        # 15m, 1h, 4h ma'lumotlari
        ohlcv_15m = exchange.fetch_ohlcv(symbol, '15m', limit=50)
        ohlcv_1h = exchange.fetch_ohlcv(symbol, '1h', limit=50)
        ohlcv_4h = exchange.fetch_ohlcv(symbol, '4h', limit=50)
        
        closes_15m = [c[4] for c in ohlcv_15m]
        closes_1h = [c[4] for c in ohlcv_1h]
        closes_4h = [c[4] for c in ohlcv_4h]
        
        current_price = closes_15m[-1]
        
        # Indicators
        rsi_15m = get_rsi(closes_15m)
        rsi_1h = get_rsi(closes_1h)
        
        ema_7 = get_ema(closes_15m, 7)
        ema_25 = get_ema(closes_15m, 25)
        ema_99 = get_ema(closes_15m, 99)
        
        # ATR (Approx)
        high_20 = max([c[1] for c in ohlcv_15m[-20:]])
        low_20 = min([c[2] for c in ohlcv_15m[-20:]])
        atr = (high_20 - low_20) * 0.5
        
        score = 0
        
        # RSI Logic
        if rsi_15m < 30: score += 25
        elif rsi_15m > 70: score -= 25
        
        # Trend Logic
        if ema_7 > ema_25 > ema_99: score += 30
        elif ema_7 < ema_25 < ema_99: score -= 30
        elif ema_7 > ema_25: score += 15
        else: score -= 15
        
        # 4H Trend
        ema_4h = get_ema(closes_4h, 25)
        if current_price > ema_4h: score += 20
        else: score -= 20        
        # Signal
        if score >= 50:
            direction = "LONG"
            signal_emoji = "🔥 KUCHLI LONG" if score >= 70 else "🟢 LONG"
            tp1 = current_price * 1.03
            tp2 = current_price * 1.06
            tp3 = current_price * 1.10
            sl = current_price - (atr * 2)
            entry_low = current_price * 0.99
            entry_high = current_price * 0.995
        elif score <= -50:
            direction = "SHORT"
            signal_emoji = "🔥 KUCHLI SHORT" if score <= -70 else "🔴 SHORT"
            tp1 = current_price * 0.97
            tp2 = current_price * 0.94
            tp3 = current_price * 0.90
            sl = current_price + (atr * 2)
            entry_low = current_price * 1.005
            entry_high = current_price * 1.01
        else:
            return None
            
        msg = f"""
{signal_emoji} | 15m/1h/4h
💎 <b>{symbol}</b>
🎯 {direction}

💰 Narx: ${current_price:.6f}
⏱️ Vaqt: {datetime.now().strftime('%H:%M')}

📊 RSI (15m): {rsi_15m:.1f} | Score: {score}

🎯 ENTRY ZONE:
${entry_low:.6f} - ${entry_high:.6f}

📈 TAKE PROFIT:
  TP1: ${tp1:.6f} (+3%)
  TP2: ${tp2:.6f} (+6%)
  TP3: ${tp3:.6f} (+10%)

🛑 STOP LOSS: ${sl:.6f}

💵 Pozitsiya: ${POSITION_SIZE} | ⚡ {LEVERAGE}x
"""
        return msg
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None
def scan_market():
    global last_scan_time
    coins = [
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
        "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",
        "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
        "ARB/USDT", "OP/USDT", "SUI/USDT", "APT/USDT", "INJ/USDT",
        "TIA/USDT", "SEI/USDT", "NEAR/USDT", "PEPE/USDT", "FLOKI/USDT",
        "SHIB/USDT", "WIF/USDT", "BONK/USDT", "FET/USDT", "RNDR/USDT"
    ]
    
    print("🔍 Skanerlash boshlandi...")
    count = 0
    
    for coin in coins:
        msg = analyze_coin(coin)
        if msg:
            print(f"✅ Signal: {coin}")
            send_telegram(msg)
            count += 1
            time.sleep(1.5) # Telegram limit
    
    last_scan_time = datetime.now()
    print(f"✅ {count} ta signal topildi!")

def run_bot():
    while True:
        try:
            scan_market()
            time.sleep(300) # 5 daqiqa kutish
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(60)

@app.route('/')
def home():
    return f"<h1>🚀 Tochka Bot Ishlamoqda!</h1><p>Oxirgi skan: {last_scan_time}</p>"

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    print("🚀 Bot Started!")
    app.run(host='0.0.0.0', port=5000, debug=False)