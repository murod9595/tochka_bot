from flask import Flask, jsonify
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
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}})
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
        """Candles ma'lumot"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [candle[4] for candle in ohlcv]  # close prices
        except:
            return None
    
    def calculate_rsi(self, prices, period=14):
        """RSI hisoblash"""
        if len(prices) < period + 1:
            return 50        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
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
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_ema(self, prices, period):
        """EMA hisoblash"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_atr(self, symbol, timeframe, period=14):
        """ATR hisoblash"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=period+1)
            highs = [c[1] for c in ohlcv]
            lows = [c[2] for c in ohlcv]
            closes = [c[4] for c in ohlcv]
            
            trs = []
            for i in range(1, len(highs)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),                    abs(lows[i] - closes[i-1])
                )
                trs.append(tr)
            
            return sum(trs[-period:]) / period
        except:
            return 0
    
    def analyze_multi_timeframe(self, symbol):
        """15m, 1h, 4h tahlil"""
        prices_15m = self.get_ohlcv(symbol, '15m')
        prices_1h = self.get_ohlcv(symbol, '1h')
        prices_4h = self.get_ohlcv(symbol, '4h')
        
        if not all([prices_15m, prices_1h, prices_4h]):
            return None
        
        current_price = prices_15m[-1]
        
        # RSI
        rsi_15m = self.calculate_rsi(prices_15m)
        rsi_1h = self.calculate_rsi(prices_1h)
        rsi_4h = self.calculate_rsi(prices_4h)
        
        # EMA
        ema_7 = self.calculate_ema(prices_15m, 7)
        ema_25 = self.calculate_ema(prices_15m, 25)
        ema_99 = self.calculate_ema(prices_15m, 99)
        
        # ATR
        atr = self.calculate_atr(symbol, '15m')
        
        # Score
        score = 0
        
        # RSI score
        if rsi_15m < 30 and rsi_1h < 40:
            score += 30
        elif rsi_15m < 40:
            score += 15
        elif rsi_15m > 70 and rsi_1h > 60:
            score -= 30
        elif rsi_15m > 60:
            score -= 15
        
        # EMA trend
        if ema_7 > ema_25 > ema_99:
            score += 30
        elif ema_7 < ema_25 < ema_99:
            score -= 30        elif ema_7 > ema_25:
            score += 15
        else:
            score -= 15
        
        # 4h trend
        ema_4h = self.calculate_ema(prices_4h, 25)
        if current_price > ema_4h:
            score += 20
        else:
            score -= 20
        
        # Signal
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
            sl = current_price - (atr * 2) if atr else current_price * 0.96
            entry_low = current_price * 0.99
            entry_high = current_price * 0.995
        else:
            tp1 = current_price * 0.97
            tp2 = current_price * 0.94
            tp3 = current_price * 0.90
            sl = current_price + (atr * 2) if atr else current_price * 1.04
            entry_low = current_price * 1.005
            entry_high = current_price * 1.01
        
        # Expected time
        if rsi_15m < 30 or rsi_15m > 70:
            expected_time = "1-3 soat"
        else:
            expected_time = "3-6 soat"
        
        return {
            'symbol': symbol,
            'signal': signal_type,
            'direction': direction,
            'price': current_price,
            'entry_low': entry_low,            'entry_high': entry_high,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'sl': sl,
            'rsi_15m': rsi_15m,
            'rsi_1h': rsi_1h,
            'rsi_4h': rsi_4h,
            'score': score,
            'expected_time': expected_time,
            'time': datetime.now().strftime('%H:%M'),
            'timeframes': f"15m: {rsi_15m:.1f} | 1h: {rsi_1h:.1f} | 4h: {rsi_4h:.1f}"
        }
    
    def send_telegram(self, message):
        """Telegramga yuborish"""
        if not BOT_TOKEN or not CHAT_ID:
            return False
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            requests.post(url, json=data, timeout=10)
            return True
        except:
            return False
    
    def format_message(self, s):
        """Xabar formati"""
        return f"""
{s['signal']} | 15m/1h/4h
💎 {s['symbol']}
🎯 {s['direction']}

💰 Narx: ${s['price']:.6f}
⏱️ Kutilayotgan: {s['expected_time']}

📊 RSI: {s['timeframes']}
📈 Score: {s['score']}/100

🎯 ENTRY ZONE:
${s['entry_low']:.6f} - ${s['entry_high']:.6f}

📈 TAKE PROFIT:
  TP1: ${s['tp1']:.6f} (+3%) → +${POSITION_SIZE*0.03:.2f}
  TP2: ${s['tp2']:.6f} (+6%) → +${POSITION_SIZE*0.06:.2f}
  TP3: ${s['tp3']:.6f} (+10%) → +${POSITION_SIZE*0.10:.2f}
🛑 STOP LOSS: ${s['sl']:.6f}

💵 Pozitsiya: ${POSITION_SIZE} | ⚡ {LEVERAGE}x

⏰ {s['time']}
━━━━━━━━━━━━━━━━
"""
    
    def scan(self):
        """Barcha coinlarni skanerlash"""
        global all_signals, last_scan
        
        print(f"\n🔍 {len(self.coins)} coin skanerlanmoqda...")
        signals = []
        
        for coin in self.coins:
            try:
                signal = self.analyze_multi_timeframe(coin)
                if signal and abs(signal['score']) >= 50:
                    signals.append(signal)
                    print(f"✅ {coin} - {signal['signal']} ({signal['score']})")
                    
                    msg = self.format_message(signal)
                    self.send_telegram(msg)
                    
                    time.sleep(1)  # Telegram limit
            except Exception as e:
                print(f"❌ {coin}: {e}")
                continue
        
        # Eng kuchlilarini saralash
        signals.sort(key=lambda x: abs(x['score']), reverse=True)
        all_signals = signals[:15]  # Top 15
        last_scan = datetime.now()
        
        print(f"✅ {len(all_signals)} signal topildi!")
        return all_signals

bot = SimpleBot()

def background_scan():
    """Fon skanerlash"""
    while True:
        try:
            bot.scan()
            time.sleep(900)  # 15 daqiqa
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)
@app.route('/')
def index():
    """Web interface"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>MarketCoin Bot</title>
        <style>
            body { background: #0a0e27; color: #fff; font-family: Arial; padding: 20px; }
            .header { text-align: center; padding: 30px; background: linear-gradient(135deg, #00d4ff, #0099cc); border-radius: 15px; margin-bottom: 30px; }
            .signal { background: #1a1f3a; padding: 20px; margin: 15px 0; border-radius: 10px; border-left: 5px solid #00ff88; }
            .signal.sell { border-left-color: #ff4757; }
            h1 { margin: 0; }
            .stats { display: flex; gap: 20px; margin-bottom: 30px; }
            .stat-box { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; text-align: center; flex: 1; }
            .stat-box h3 { color: #00d4ff; font-size: 28px; margin: 0 0 10px 0; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 MarketCoin Bot</h1>
            <p>Multi-Timeframe Signals | 15m/1h/4h</p>
        </div>
        <div class="stats">
            <div class="stat-box"><h3>{{ signals|length }}</h3><p>Signallar</p></div>
            <div class="stat-box"><h3>45+</h3><p>Coin</p></div>
            <div class="stat-box"><h3>15m/1h/4h</h3><p>Timeframe</p></div>
        </div>
        <h2>🔥 Oxirgi Signallar</h2>
        {% for s in signals %}
        <div class="signal {{ 'sell' if 'SHORT' in s.signal else '' }}">
            <h3>{{ s.symbol }} - {{ s.signal }}</h3>
            <p>Narx: ${{ "%.6f"|format(s.price) }}</p>
            <p>RSI: {{ s.timeframes }}</p>
            <p>Entry: ${{ "%.6f"|format(s.entry_low) }} - ${{ "%.6f"|format(s.entry_high) }}</p>
            <p>TP1: ${{ "%.6f"|format(s.tp1) }} | TP2: ${{ "%.6f"|format(s.tp2) }} | TP3: ${{ "%.6f"|format(s.tp3) }}</p>
            <p>SL: ${{ "%.6f"|format(s.sl) }}</p>
            <p>Score: {{ s.score }}/100 | {{ s.expected_time }}</p>
        </div>
        {% endfor %}
        <script>setTimeout(function(){location.reload();}, 300000);</script>
    </body>
    </html>
    """
    return render_template_string(html, signals=all_signals)

@app.route('/api/signals')def api_signals():
    return jsonify({
        'signals': all_signals,
        'last_scan': last_scan.strftime('%Y-%m-%d %H:%M:%S') if last_scan else None
    })

if __name__ == "__main__":
    threading.Thread(target=background_scan, daemon=True).start()
    
    print("🚀 MarketCoin Bot ishga tushdi!")
    print("📱 Web: http://localhost:5000")
    print("💵 Pozitsiya: $50")
    print("📈 45+ coin, 3 timeframe...")
    
    app.run(host='0.0.0.0', port=5000, debug=False)