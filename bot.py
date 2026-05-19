import os
import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# .env faylni yuklash
load_dotenv()

# Telegram sozlamalari
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

class CryptoSignalBot:
    def __init__(self):
        self.exchange = ccxt.binance()
        
    def get_data(self, symbol, timeframe='4h', limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            return df
        except Exception as e:
            print(f"Xatolik: {e}")
            return None
    
    def calculate_indicators(self, df):
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema_7'] = ta.ema(df['close'], length=7)
        df['ema_25'] = ta.ema(df['close'], length=25)
        macd = ta.macd(df['close'])
        df['macd'] = macd['MACD_12_26_9']
        df['macd_signal'] = macd['MACDs_12_26_9']
        df['vol_ma'] = ta.sma(df['volume'], length=20)
        return df
    
    def generate_signal(self, df):
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = "HOLD"
        strength = 0
        
        if last['rsi'] < 30:
            strength += 2
        elif last['rsi'] < 40:            strength += 1
        elif last['rsi'] > 70:
            strength -= 2
        elif last['rsi'] > 60:
            strength -= 1
        
        if prev['ema_7'] <= prev['ema_25'] and last['ema_7'] > last['ema_25']:
            strength += 2
        elif prev['ema_7'] >= prev['ema_25'] and last['ema_7'] < last['ema_25']:
            strength -= 2
        elif last['ema_7'] > last['ema_25']:
            strength += 1
        else:
            strength -= 1
        
        if last['volume'] > last['vol_ma'] * 1.5:
            strength += 1 if strength > 0 else -1
        
        if strength >= 3:
            signal = "🟢 STRONG BUY"
        elif strength == 2:
            signal = "🟢 BUY"
        elif strength <= -3:
            signal = "🔴 STRONG SELL"
        elif strength == -2:
            signal = "🔴 SELL"
        else:
            signal = "⚪ HOLD"
        
        return signal, strength
    
    def calculate_sl_tp(self, price, signal_type):
        if "BUY" in signal_type:
            sl = price * 0.97
            tp1 = price * 1.03
            tp2 = price * 1.06
            tp3 = price * 1.10
        else:
            sl = price * 1.03
            tp1 = price * 0.97
            tp2 = price * 0.94
            tp3 = price * 0.90
        return sl, tp1, tp2, tp3
    
    def send_message(self, text):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": text,                "parse_mode": "HTML"
            })
            print("✅ Xabar yuborildi")
        except Exception as e:
            print(f"❌ Xabar yuborilmadi: {e}")
    
    def analyze_coin(self, symbol):
        print(f"📊 {symbol} tahlil qilinmoqda...")
        df = self.get_data(symbol)
        if df is None:
            return False
        
        df = self.calculate_indicators(df)
        signal, strength = self.generate_signal(df)
        
        last = df.iloc[-1]
        sl, tp1, tp2, tp3 = self.calculate_sl_tp(last['close'], signal)
        
        message = f"""
📊 <b>{symbol}</b>
💰 Narx: <b>${last['close']:.4f}</b>
📈 Signal: <b>{signal}</b>
📊 RSI: {last['rsi']:.2f}

💡 <b>Recommendation:</b>
🔸 Entry: ${last['close']:.4f}
🔸 SL: ${sl:.4f}
🔸 TP1: ${tp1:.4f}
🔸 TP2: ${tp2:.4f}
🔸 TP3: ${tp3:.4f}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        if abs(strength) >= 2:
            self.send_message(message)
            return True
        return False
    
    def run(self):
        coins = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
        print("🚀 Crypto Signal Bot ishga tushdi...")
        self.send_message("<b>🚀 Bot ishga tushdi!</b>")
        
        while True:
            try:
                print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                signals_count = 0
                for coin in coins:
                    if self.analyze_coin(coin):                        signals_count += 1
                    time.sleep(2)
                print(f"📊 Signallar: {signals_count}")
                time.sleep(3600)
            except Exception as e:
                print(f"❌ Xatolik: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = CryptoSignalBot()
    bot.run()