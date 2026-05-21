from flask import Flask, jsonify, render_template_string
import ccxt
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv
import threading

load_dotenv()

app = Flask(__name__)

# CONFIG
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
LEVERAGE = int(os.getenv('LEVERAGE', 15))
POSITION_SIZE = float(os.getenv('POSITION_SIZE', 50))

# GLOBAL
all_signals = []
last_scan = None

class SimpleBot:
    def __init__(self):
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}, 'timeout': 20000})
        self.coins = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",
            "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
            "ARB/USDT", "OP/USDT", "SUI/USDT", "APT/USDT", "INJ/USDT",
            "TIA/USDT", "SEI/USDT", "NEAR/USDT", "PEPE/USDT", "FLOKI/USDT",
            "SHIB/USDT", "WIF/USDT", "BONK/USDT", "FET/USDT", "RNDR/USDT",
            "IMX/USDT", "GALA/USDT", "SAND/USDT", "CRV/USDT", "LDO/USDT",
            "STRK/USDT", "PYTH/USDT", "JUP/USDT", "FTM/USDT", "RUNE/USDT",
            "NOT/USDT", "DOGS/USDT", "WIF/USDT", "BOME/USDT", "WEN/USDT"
        ]
    
    def get_ohlcv(self, symbol, timeframe='15m', limit=50):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [candle[4] for candle in ohlcv]
        except:
            return None
    
    def calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50
        gains = []
        losses = []        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_ema(self, prices, period):
        if len(prices) < period:
            return prices[-1] if prices else 0
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def analyze_multi_timeframe(self, symbol):
        prices_15m = self.get_ohlcv(symbol, '15m')
        prices_1h = self.get_ohlcv(symbol, '1h')
        prices_4h = self.get_ohlcv(symbol, '4h')
        
        if not all([prices_15m, prices_1h, prices_4h]):
            return None
        
        current_price = prices_15m[-1]
        rsi_15m = self.calculate_rsi(prices_15m)
        rsi_1h = self.calculate_rsi(prices_1h)
        
        ema_7 = self.calculate_ema(prices_15m, 7)
        ema_25 = self.calculate_ema(prices_15m, 25)
        ema_99 = self.calculate_ema(prices_15m, 99)
        
        ema_4h = self.calculate_ema(prices_4h, 25)
        
        # ATR Approximation
        atr = (max(prices_15m[-20:]) - min(prices_15m[-20:])) * 0.5
        
        score = 0
        
        # RSI Score
        if rsi_15m < 30:
            score += 25        elif rsi_15m > 70:
            score -= 25
            
        # Trend Score
        if ema_7 > ema_25 > ema_99:
            score += 30
        elif ema_7 < ema_25 < ema_99:
            score -= 30
        elif ema_7 > ema_25:
            score += 15
        else:
            score -= 15
            
        # 4H Trend
        if current_price > ema_4h:
            score += 20
        else:
            score -= 20
            
        # Signal Type
        if score >= 50:
            signal_type = "🔥 KUCHLI LONG" if score >= 70 else "🟢 LONG"
            direction = "LONG"
        elif score <= -50:
            signal_type = "🔥 KUCHLI SHORT" if score <= -70 else "🔴 SHORT"
            direction = "SHORT"
        else:
            return None
        
        # TP/SL
        if direction == "LONG":
            tp1 = current_price * 1.03
            tp2 = current_price * 1.06
            tp3 = current_price * 1.10
            sl = current_price - (atr * 2)
            entry_low = current_price * 0.99
            entry_high = current_price * 0.995
        else:
            tp1 = current_price * 0.97
            tp2 = current_price * 0.94
            tp3 = current_price * 0.90
            sl = current_price + (atr * 2)
            entry_low = current_price * 1.005
            entry_high = current_price * 1.01
        
        expected_time = "1-3 soat" if rsi_15m < 30 or rsi_15m > 70 else "3-6 soat"
        
        return {
            'symbol': symbol,
            'signal': signal_type,            'direction': direction,
            'price': current_price,
            'entry_low': entry_low,
            'entry_high': entry_high,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'sl': sl,
            'rsi': rsi_15m,
            'score': score,
            'expected_time': expected_time,
            'time': datetime.now().strftime('%H:%M')
        }
    
    def send_telegram(self, message):
        if not BOT_TOKEN or not CHAT_ID:
            return False
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
            return True
        except:
            return False
    
    def format_message(self, s):
        return f"""
{s['signal']} | 15m/1h/4h
💎 {s['symbol']}
🎯 {s['direction']}

💰 Narx: ${s['price']:.6f}
⏱️ Kutilayotgan: {s['expected_time']}

📊 RSI: {s['rsi']:.1f} | Score: {s['score']}

🎯 ENTRY ZONE:
${s['entry_low']:.6f} - ${s['entry_high']:.6f}

📈 TAKE PROFIT:
  TP1: ${s['tp1']:.6f} (+3%)
  TP2: ${s['tp2']:.6f} (+6%)
  TP3: ${s['tp3']:.6f} (+10%)

🛑 STOP LOSS: ${s['sl']:.6f}

💵 Pozitsiya: ${POSITION_SIZE} | ⚡ {LEVERAGE}x

⏰ {s['time']}
"""
        def scan(self):
        global all_signals, last_scan
        print(f"\n🔍 Skanerlanmoqda...")
        signals = []
        
        for coin in self.coins:
            try:
                signal = self.analyze_multi_timeframe(coin)
                if signal and abs(signal['score']) >= 50:
                    signals.append(signal)
                    print(f"✅ {coin} - {signal['signal']}")
                    self.send_telegram(self.format_message(signal))
                    time.sleep(1)
            except:
                continue
        
        signals.sort(key=lambda x: abs(x['score']), reverse=True)
        all_signals = signals[:15]
        last_scan = datetime.now()
        print(f"✅ {len(all_signals)} signal topildi!")
        return all_signals

bot = SimpleBot()

def background_scan():
    while True:
        try:
            bot.scan()
            time.sleep(900)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

@app.route('/')
def index():
    return "<h1>🚀 Tochka Bot is running!</h1>"

@app.route('/api/signals')
def api_signals():
    return jsonify({'signals': all_signals})

if __name__ == "__main__":
    threading.Thread(target=background_scan, daemon=True).start()
    print("🚀 MarketCoin Bot ishga tushdi!")
    app.run(host='0.0.0.0', port=5000, debug=False)