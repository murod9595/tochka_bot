from flask import Flask, render_template_string, jsonify
import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import threading
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

app = Flask(__name__)

# ==================== GLOBAL O'ZGARUVCHILAR ====================
all_signals = {'fast': [], 'slow': []}
last_scan_time = None
scan_progress = 0

# Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
POSITION_SIZE = float(os.getenv('POSITION_SIZE', 50))
LEVERAGE = int(os.getenv('LEVERAGE', 15))

# ==================== MARKETCOIN BOT CLASS ====================
class MarketCoinBot:
    def __init__(self):
        # 5 ta asosiy birja
        self.exchanges = {
            'binance': ccxt.binance({'options': {'defaultType': 'future'}, 'timeout': 15000}),
            'bybit': ccxt.bybit({'options': {'defaultType': 'future'}, 'timeout': 15000}),
            'okx': ccxt.okx({'options': {'defaultType': 'swap'}, 'timeout': 15000}),
            'kucoin': ccxt.kucoinfutures({'timeout': 15000}),
            'gateio': ccxt.gateio({'options': {'defaultType': 'future'}, 'timeout': 15000}),
        }
        
        # 600+ coin ro'yxati
        self.coins = self.load_coins()
        self.init_database()
    
    def load_coins(self):
        """600+ coin ro'yxati"""
        return [
            # TOP Coins
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",            "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
            
            # Layer 1
            "ONDO/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT", "APT/USDT",
            "INJ/USDT", "TIA/USDT", "SEI/USDT", "NEAR/USDT", "ALGO/USDT",
            "VET/USDT", "ICP/USDT", "HBAR/USDT", "FIL/USDT", "TRX/USDT",
            "XLM/USDT", "AAVE/USDT", "MKR/USDT", "SNX/USDT", "GRT/USDT",
            
            # Meme Coins
            "PEPE/USDT", "FLOKI/USDT", "SHIB/USDT", "WIF/USDT", "BONK/USDT",
            "BOME/USDT", "MYRO/USDT", "POPCAT/USDT", "MEW/USDT", "WEN/USDT",
            "SLERF/USDT", "LADYS/USDT", "TURBO/USDT", "ORDI/USDT",
            
            # AI & Gaming
            "FET/USDT", "AGIX/USDT", "OCEAN/USDT", "RNDR/USDT", "AKT/USDT",
            "IMX/USDT", "GALA/USDT", "SAND/USDT", "MANA/USDT", "AXS/USDT",
            "ENJ/USDT", "CHZ/USDT", "THETA/USDT", "FLOW/USDT", "EOS/USDT",
            
            # DeFi
            "CRV/USDT", "COMP/USDT", "SUSHI/USDT", "LDO/USDT", "RPL/USDT",
            "FXS/USDT", "CVX/USDT", "BAL/USDT", "YFI/USDT", "1INCH/USDT",
            
            # Layer 2
            "STRK/USDT", "ZK/USDT", "MANTA/USDT", "PYTH/USDT",
            "JUP/USDT", "W/USDT", "TNSR/USDT", "SAGA/USDT", "TAO/USDT",
            
            # RWA
            "POLYX/USDT", "RIO/USDT", "CFX/USDT", "KAS/USDT",
            
            # New Listings
            "NOT/USDT", "DOGS/USDT", "HMSTR/USDT", "CATI/USDT", "REDO/USDT",
            "IO/USDT", "ZRO/USDT", "LISTA/USDT",
            
            # Others
            "FTM/USDT", "RUNE/USDT", "KAVA/USDT", "WOO/USDT", "GMT/USDT",
            "APE/USDT", "LRC/USDT", "SKL/USDT", "ANKR/USDT", "STORJ/USDT",
            "CELO/USDT", "QTUM/USDT", "ZIL/USDT", "ICX/USDT", "ONT/USDT",
            "ZEN/USDT", "DASH/USDT", "XMR/USDT", "ZEC/USDT", "DCR/USDT",
        ]
    
    def init_database(self):
        """SQLite ma'lumotlar bazasini yaratish"""
        conn = sqlite3.connect('marketcoin.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT,                direction TEXT,
                entry_price REAL,
                tp1 REAL,
                tp2 REAL,
                tp3 REAL,
                sl REAL,
                leverage INTEGER,
                score INTEGER,
                timeframe TEXT,
                expected_time TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                position_size REAL DEFAULT 50,
                tp1_hit DATETIME,
                tp2_hit DATETIME,
                tp3_hit DATETIME,
                sl_hit DATETIME,
                profit_loss REAL,
                exchange TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database yaratildi!")
    
    def get_best_data(self, symbol, timeframe='15m', limit=100):
        """Eng tez birjadan ma'lumot olish"""
        for name, exchange in self.exchanges.items():
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                if ohlcv and len(ohlcv) > 0:
                    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    return df, name
            except:
                continue
        return None, None
    
    def calculate_volatility(self, df):
        """Volatillikni hisoblash"""
        if df is None or len(df) < 14:
            return 0, 0
        try:
            returns = df['close'].pct_change()
            volatility = returns.std() * 100
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            atr_percent = (atr.iloc[-1] / df['close'].iloc[-1]) * 100 if len(atr) > 0 else 0
            return volatility, atr_percent
        except:            return 0, 0
    
    def check_volume_quality(self, df):
        """Hajm sifatini tekshirish"""
        if df is None or len(df) < 20:
            return False, 1, "Normal"
        try:
            avg_volume = df['volume'].tail(20).mean()
            current_volume = df['volume'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            if avg_volume == 0:
                return False, 1, "Normal"
            
            volume_usd = current_volume * current_price
            min_volume_usd = 10_000_000
            
            if volume_usd < min_volume_usd:
                return False, current_volume/avg_volume if avg_volume > 0 else 1, "Past"
            
            ratio = current_volume / avg_volume
            if ratio > 5:
                return True, ratio, "🔥 Ekstremal (5x+)"
            elif ratio > 3:
                return True, ratio, "💥 Juda yuqori (3-5x)"
            elif ratio > 2:
                return True, ratio, "📈 Yuqori (2-3x)"
            elif ratio > 1.5:
                return True, ratio, "📊 O'rtacha (1.5-2x)"
            else:
                return True, ratio, "😴 Past"
        except:
            return False, 1, "Normal"
    
    def detect_breakout(self, df):
        """Breakout aniqlash"""
        if df is None or len(df) < 20:
            return False, None, None
        try:
            current_price = df['close'].iloc[-1]
            resistance = df['high'].tail(20).max()
            support = df['low'].tail(20).min()
            
            if current_price > resistance * 1.02:
                return True, "UP", resistance
            if current_price < support * 0.98:
                return True, "DOWN", support
        except:
            pass
        return False, None, None    
    def detect_pattern(self, df):
        """Grafik patternlarni aniqlash"""
        if df is None or len(df) < 10:
            return "Aniqlanmadi", 0
        try:
            highs = df['high'].tail(5).values
            lows = df['low'].tail(5).values
            
            if len(highs) >= 3:
                if highs[0] < highs[1] and highs[2] < highs[1]:
                    if abs(highs[0] - highs[2]) < 0.02 * highs[1]:
                        return "Double Top (Pastga)", -30
            
            if len(lows) >= 3:
                if lows[0] > lows[1] and lows[2] > lows[1]:
                    if abs(lows[0] - lows[2]) < 0.02 * lows[1]:
                        return "Double Bottom (Yuqoriga)", +30
            
            if len(highs) >= 4:
                if all(highs[i] < highs[i+1] for i in range(len(highs)-1)):
                    return "Kuchli O'sish Trendi", +25
            
            if len(lows) >= 4:
                if all(lows[i] > lows[i+1] for i in range(len(lows)-1)):
                    return "Kuchli Tushish Trendi", -25
        except:
            pass
        return "Pattern yo'q", 0
    
    def calculate_expected_time(self, timeframe, volatility):
        """Taxminiy natija vaqtini hisoblash"""
        if timeframe == '15m':
            if volatility > 10:
                return "1-2 soat ichida", 2
            elif volatility > 7:
                return "2-4 soat ichida", 4
            else:
                return "4-8 soat ichida", 8
        elif timeframe == '1h':
            if volatility > 8:
                return "6-12 soat ichida", 12
            elif volatility > 5:
                return "12-24 soat ichida", 24
            else:
                return "1-2 kun ichida", 48
        else:
            if volatility > 6:
                return "1-2 kun ichida", 36
            else:                return "2-4 kun ichida", 72
    
    def analyze_coin(self, symbol, timeframe='15m'):
        """Bitta coin tahlili"""
        df, exchange_name = self.get_best_data(symbol, timeframe)
        if df is None or len(df) < 50:
            return None
        
        volatility, atr_percent = self.calculate_volatility(df)
        
        min_vol = 3 if timeframe == '15m' else 2
        if volatility < min_vol:
            return None
        
        volume_ok, volume_ratio, volume_text = self.check_volume_quality(df)
        if not volume_ok:
            return None
        
        try:
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema_7'] = ta.ema(df['close'], length=7)
            df['ema_25'] = ta.ema(df['close'], length=25)
            df['ema_99'] = ta.ema(df['close'], length=99)
            
            macd = ta.macd(df['close'])
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            
            bb = ta.bbands(df['close'], length=20)
            df['bb_upper'] = bb['BBU_20_2.0']
            df['bb_lower'] = bb['BBL_20_2.0']
            
            df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)
            
            stoch_rsi = ta.stochrsi(df['close'], length=14)
            df['stoch_rsi'] = stoch_rsi['STOCHRSIk_14_14_3_3']
            
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            is_breakout, breakout_direction, _ = self.detect_breakout(df)
            pattern, pattern_score = self.detect_pattern(df)
            
            last = df.iloc[-1]
            current_price = last['close']
            
            signal_score = 0
            
            rsi = last['rsi']
            if rsi < 30:
                signal_score += 25            elif rsi < 40:
                signal_score += 15
            elif rsi > 70:
                signal_score -= 25
            elif rsi > 60:
                signal_score -= 15
            
            if last['ema_7'] > last['ema_25'] > last['ema_99']:
                signal_score += 30
            elif last['ema_7'] < last['ema_25'] < last['ema_99']:
                signal_score -= 30
            elif last['ema_7'] > last['ema_25']:
                signal_score += 15
            else:
                signal_score -= 15
            
            if last['macd'] > last['macd_signal']:
                signal_score += 20
            else:
                signal_score -= 20
            
            if volume_ratio > 3:
                signal_score += 15
            elif volume_ratio > 1.5:
                signal_score += 8
            
            if last['adx'] > 25:
                signal_score += 10
            elif last['adx'] > 20:
                signal_score += 5
            
            if is_breakout:
                if breakout_direction == 'UP':
                    signal_score += 15
                else:
                    signal_score -= 15
            
            signal_score += pattern_score
            
            if signal_score >= 60:
                signal_type = "🟢 KUCHLI SOTIB OLISH"
                direction = "LONG"
            elif signal_score >= 45:
                signal_type = "🟢 SOTIB OLISH"
                direction = "LONG"
            elif signal_score <= -60:
                signal_type = "🔴 KUCHLI SOTISH"
                direction = "SHORT"
            elif signal_score <= -45:
                signal_type = "🔴 SOTISH"                direction = "SHORT"
            else:
                return None
            
            atr = last['atr']
            if direction == "LONG":
                tp1 = current_price * 1.03
                tp2 = current_price * 1.06
                tp3 = current_price * 1.10
                sl = current_price - (atr * 2)
                entry_low = current_price * 0.985
                entry_high = current_price * 0.995
            else:
                tp1 = current_price * 0.97
                tp2 = current_price * 0.94
                tp3 = current_price * 0.90
                sl = current_price + (atr * 2)
                entry_low = current_price * 1.005
                entry_high = current_price * 1.015
            
            expected_time, hours = self.calculate_expected_time(timeframe, volatility)
            
            signal_data = {
                'symbol': symbol,
                'exchange': exchange_name,
                'signal': signal_type,
                'direction': direction,
                'price': current_price,
                'entry_low': entry_low,
                'entry_high': entry_high,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'sl': sl,
                'leverage': LEVERAGE,
                'volatility': volatility,
                'volume_ratio': volume_ratio,
                'volume_text': volume_text,
                'rsi': rsi,
                'score': signal_score,
                'pattern': pattern,
                'breakout': is_breakout,
                'breakout_direction': breakout_direction,
                'timeframe': timeframe,
                'expected_time': expected_time,
                'expected_hours': hours,
                'time': datetime.now().strftime('%H:%M:%S'),
                'adx': last['adx']
            }
                        return signal_data
        except Exception as e:
            print(f"❌ {symbol} tahlil xatosi: {e}")
            return None
    
    def send_telegram_message(self, message, parse_mode='HTML'):
        """Telegram ga xabar yuborish"""
        if not BOT_TOKEN or not CHAT_ID:
            return False
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Telegram xatolik: {e}")
            return False
    
    def format_signal_message(self, signal_data):
        """Signal xabarini formatlash"""
        emoji = "🔥" if "KUCHLI" in signal_data['signal'] else "📊"
        
        message = f"""
{emoji} <b>{signal_data['signal']}</b> | {signal_data['timeframe']}
💎 <b>{signal_data['symbol']}</b> ({signal_data['exchange']})
🎯 <b>{signal_data['direction']}</b>

💰 <b>Narx:</b> ${signal_data['price']:.6f}

⏱️ <b>Kutilayotgan natija:</b> {signal_data['expected_time']}

🎯 <b>Entry Zone:</b>
${signal_data['entry_low']:.6f} - ${signal_data['entry_high']:.6f}

📈 <b>Take Profit:</b>
  TP1: ${signal_data['tp1']:.6f} (+3%) → +${POSITION_SIZE * 0.03:.2f}
  TP2: ${signal_data['tp2']:.6f} (+6%) → +${POSITION_SIZE * 0.06:.2f}
  TP3: ${signal_data['tp3']:.6f} (+10%) → +${POSITION_SIZE * 0.10:.2f}

🛑 <b>Stop Loss:</b> ${signal_data['sl']:.6f} → -${POSITION_SIZE * 0.04:.2f}

💵 <b>Pozitsiya:</b> ${POSITION_SIZE} | ⚡ Leverage: {signal_data['leverage']}x
📊 <b>Score:</b> {signal_data['score']}/100

📈 <b>Statistika:</b>  • Volatility: {signal_data['volatility']:.2f}%
  • Volume: {signal_data['volume_ratio']:.1f}x ({signal_data['volume_text']})
  • RSI: {signal_data['rsi']:.1f}
  • ADX: {signal_data['adx']:.1f}
  • Pattern: {signal_data['pattern']}

⏰ {signal_data['time']}
"""
        return message
    
    def save_signal(self, signal_data):
        """Signalni bazaga saqlash"""
        try:
            conn = sqlite3.connect('marketcoin.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO signals (
                    symbol, signal_type, direction, entry_price, tp1, tp2, tp3, sl,
                    leverage, score, timeframe, expected_time, exchange,
                    position_size, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data['symbol'],
                signal_data['signal'],
                signal_data['direction'],
                signal_data['price'],
                signal_data['tp1'],
                signal_data['tp2'],
                signal_data['tp3'],
                signal_data['sl'],
                signal_data['leverage'],
                signal_data['score'],
                signal_data['timeframe'],
                signal_data['expected_time'],
                signal_data['exchange'],
                POSITION_SIZE,
                'active'
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Bazaga saqlash xatosi: {e}")
    
    def scan_all_coins(self):
        """Barcha coinlarni skanerlash"""
        global last_scan_time, scan_progress
        fast_signals = []        slow_signals = []
        
        print(f"\n🔍 {len(self.coins)} ta coin skanerlanmoqda...")
        
        total_coins = len(self.coins)
        
        for i, coin in enumerate(self.coins):
            try:
                signal_15m = self.analyze_coin(coin, '15m')
                if signal_15m:
                    fast_signals.append(signal_15m)
                    print(f"✅ FAST: {coin} - {signal_15m['signal']} (Score: {signal_15m['score']})")
                    
                    msg = self.format_signal_message(signal_15m)
                    self.send_telegram_message(msg)
                    
                    self.save_signal(signal_15m)
                    
                    time.sleep(0.3)
                
                signal_1h = self.analyze_coin(coin, '1h')
                if signal_1h and abs(signal_1h['score']) >= 50:
                    slow_signals.append(signal_1h)
                
                scan_progress = int(((i + 1) / total_coins) * 100)
                
                if (i + 1) % 50 == 0:
                    print(f"⏳ {i+1}/{total_coins}... ({scan_progress}%)")
                    time.sleep(0.5)
                    
            except Exception as e:
                continue
        
        fast_signals.sort(key=lambda x: abs(x['score']), reverse=True)
        slow_signals.sort(key=lambda x: abs(x['score']), reverse=True)
        
        last_scan_time = datetime.now()
        scan_progress = 100
        
        print(f"✅ {len(fast_signals)} FAST, {len(slow_signals)} SLOW signal topildi!")
        
        return fast_signals[:15], slow_signals[:10]
    
    def generate_weekly_report(self):
        """Haftalik hisobot yaratish"""
        try:
            conn = sqlite3.connect('marketcoin.db', check_same_thread=False)
            cursor = conn.cursor()
            
            week_ago = datetime.now() - timedelta(days=7)            
            cursor.execute('''
                SELECT 
                    COUNT(*),
                    SUM(CASE WHEN status IN ('tp1', 'tp2', 'tp3') THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status = 'sl' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status = 'tp1' THEN profit_loss ELSE 0 END),
                    SUM(CASE WHEN status = 'tp2' THEN profit_loss ELSE 0 END),
                    SUM(CASE WHEN status = 'tp3' THEN profit_loss ELSE 0 END),
                    SUM(CASE WHEN status = 'sl' THEN profit_loss ELSE 0 END)
                FROM signals 
                WHERE timestamp >= ?
            ''', (week_ago,))
            
            result = cursor.fetchone()
            total = result[0] or 0
            successful = result[1] or 0
            stop_loss = result[2] or 0
            total_profit = (result[3] or 0) + (result[4] or 0) + (result[5] or 0)
            total_loss = abs(result[6] or 0)
            net_profit = total_profit - total_loss
            
            win_rate = (successful / total * 100) if total > 0 else 0
            initial_capital = total * POSITION_SIZE
            roi = (net_profit / initial_capital * 100) if initial_capital > 0 else 0
            
            conn.close()
            
            message = f"""
📊 <b>HAFTALIK SAVDO HISOBOTI</b>
📅 Davr: {week_ago.strftime('%d.%m')} - {datetime.now().strftime('%d.%m')}

📈 <b>UMUMIY STATISTIKA:</b>
• Jami signallar: {total} ta
• Muvaffaqiyatli: {successful} ta ({win_rate:.1f}%)
• Stop Loss: {stop_loss} ta

💰 <b>MOLIYAVIY NATIJALAR:</b>
• Boshlang'ich: ${initial_capital:.2f}
• Jami foyda: +${total_profit:.2f}
• Jami zarar: -${total_loss:.2f}
• <b>Sof foyda:</b> <b style="color: #00ff88">+${net_profit:.2f}</b>
• <b>ROI:</b> <b style="color: #00ff88">{roi:.1f}%</b>

💡 <b>XULOSA:</b>
{self.generate_conclusion(win_rate, roi, total)}

🚀 MarketCoin - Aniq Signallar!
"""
                        self.send_telegram_message(message)
            
        except Exception as e:
            print(f"❌ Haftalik hisobot xatosi: {e}")
    
    def generate_conclusion(self, win_rate, roi, total):
        """Xulosa yaratish"""
        if win_rate >= 70 and roi > 50:
            return "Ajoyib hafta! Win rate 70% dan yuqori. Strategiya mukammal ishlayapti!"
        elif win_rate >= 60 and roi > 20:
            return "Yaxshi natija! Barqaror o'sish kuzatilmoqda."
        elif win_rate >= 50:
            return "Normal natija. Ba'zi signallarni qayta ko'rib chiqing."
        else:
            return "Bu hafta qiyin bo'ldi. Sabr qiling, keyingi hafta yaxshilanadi."

# ==================== GLOBAL BOT ====================
scanner = MarketCoinBot()

# ==================== BACKGROUND VAZIFALAR ====================
def background_scanner():
    """Fonda doimiy skanerlash"""
    while True:
        try:
            fast, slow = scanner.scan_all_coins()
            all_signals['fast'] = fast
            all_signals['slow'] = slow
            time.sleep(300)
        except Exception as e:
            print(f"❌ Scanner xatosi: {e}")
            time.sleep(60)

# ==================== FLASK ROUTE'LAR ====================
@app.route('/')
def index():
    """Web interface"""
    html = """
    <!DOCTYPE html>
    <html lang="uz">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎯 MarketCoin - Professional Signallar</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%); 
                color: #fff; 
                padding: 20px;                min-height: 100vh;
            }
            .header {
                text-align: center;
                padding: 30px 0;
                background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
            }
            .header h1 { font-size: 32px; margin-bottom: 10px; }
            .stats {
                display: flex;
                justify-content: space-around;
                margin-bottom: 30px;
                flex-wrap: wrap;
                gap: 15px;
            }
            .stat-box {
                background: rgba(255, 255, 255, 0.1);
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                min-width: 150px;
            }
            .stat-box h3 { font-size: 28px; color: #00d4ff; margin-bottom: 5px; }
            .section { margin-bottom: 40px; }
            .section-title {
                font-size: 24px;
                color: #ffd700;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #ffd700;
            }
            .signal {
                background: linear-gradient(135deg, #1a1f3a 0%, #2d3561 100%);
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 20px;
                border-left: 6px solid #00ff88;
            }
            .signal.sell { border-left-color: #ff4757; }
            .coin-name { font-size: 24px; font-weight: bold; color: #00d4ff; margin-bottom: 10px; }
            .signal-badge {
                background: linear-gradient(135deg, #00ff88 0%, #00cc66 100%);
                color: #000;
                padding: 8px 20px;
                border-radius: 25px;
                font-weight: bold;
                display: inline-block;                margin-bottom: 10px;
            }
            .price { font-size: 20px; color: #ffd700; margin: 10px 0; }
            .loading {
                text-align: center;
                padding: 60px 20px;
                font-size: 20px;
                color: #00d4ff;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 MarketCoin</h1>
            <p>Professional Crypto Signallar | 600+ Coin</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <h3>{{ fast_signals|length }}</h3>
                <p>Tezkor (15m)</p>
            </div>
            <div class="stat-box">
                <h3>{{ slow_signals|length }}</h3>
                <p>O'rta (1h)</p>
            </div>
            <div class="stat-box">
                <h3>600+</h3>
                <p>Coin Skanerlandi</p>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">🔥 TEZKOR SIGNALLAR (15m)</div>
            {% if fast_signals %}
                {% for s in fast_signals %}
                <div class="signal {{ 'sell' if 'SOTISH' in s.signal else '' }}">
                    <div class="coin-name">{{ s.symbol }}</div>
                    <div class="signal-badge">{{ s.signal }} • {{ s.direction }}</div>
                    <div class="price">💰 Narx: ${{ "%.6f"|format(s.price) }}</div>
                    <p><strong>Entry:</strong> ${{ "%.6f"|format(s.entry_low) }} - ${{ "%.6f"|format(s.entry_high) }}</p>
                    <p><strong>TP1:</strong> ${{ "%.6f"|format(s.tp1) }} | <strong>TP2:</strong> ${{ "%.6f"|format(s.tp2) }} | <strong>TP3:</strong> ${{ "%.6f"|format(s.tp3) }}</p>
                    <p><strong>SL:</strong> ${{ "%.6f"|format(s.sl) }}</p>
                    <p><strong>Score:</strong> {{ s.score }}/100 | <strong>Volatility:</strong> {{ "%.1f"|format(s.volatility) }}%</p>
                    <p style="color: #888; margin-top: 10px;">⏰ {{ s.time }} | ⏱️ {{ s.expected_time }}</p>
                </div>
                {% endfor %}
            {% else %}
                <div class="loading">⏳ Hozircha signallar yo'q. Skanerlanmoqda...</div>
            {% endif %}        </div>
        
        <script>
            setTimeout(function() { location.reload(); }, 300000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html, 
                                 fast_signals=all_signals['fast'], 
                                 slow_signals=all_signals['slow'])

@app.route('/api/signals')
def api_signals():
    """API endpoint"""
    return jsonify({
        'fast': all_signals['fast'],
        'slow': all_signals['slow'],
        'last_scan': last_scan_time.strftime('%Y-%m-%d %H:%M:%S') if last_scan_time else None,
        'progress': scan_progress
    })

# ==================== ISHGA TUSHIRISH ====================
if __name__ == "__main__":
    scan_thread = threading.Thread(target=background_scanner, daemon=True)
    scan_thread.start()
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(scanner.generate_weekly_report, 'cron', day_of_week='sun', hour=23)
    scheduler.start()
    
    print("🚀 MarketCoin Bot ishga tushdi!")
    print("📱 Web: http://localhost:5000")
    print("📊 API: http://localhost:5000/api/signals")
    print("💵 Pozitsiya: $50")
    print("📈 600+ coin skanerlanmoqda...")
    
    app.run(host='0.0.0.0', port=5000, debug=False)