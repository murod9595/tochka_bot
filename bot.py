import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class AdvancedCryptoBot:
    def __init__(self):
        self.exchanges = {
            'binance': ccxt.binance({'options': {'defaultType': 'future'}}),
            'bybit': ccxt.bybit({'options': {'defaultType': 'future'}}),
        }
        self.leverage = int(os.getenv('LEVERAGE', 15))
        self.all_coins = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",
            "ONDO/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT", "APT/USDT",
            "PEPE/USDT", "FLOKI/USDT", "SHIB/USDT", "WIF/USDT", "BONK/USDT",
        ]
    
    def get_data(self, symbol):
        for name, exchange in self.exchanges.items():
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                return df
            except:
                continue
        return None
    
    def analyze_coin(self, symbol):
        df = self.get_data(symbol)
        if df is None:
            return None
        
        if len(df) < 50:
            return None
        
        # Indicators
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema_7'] = ta.ema(df['close'], length=7)
        df['ema_25'] = ta.ema(df['close'], length=25)
        df['ema_99'] = ta.ema(df['close'], length=99)
        macd = ta.macd(df['close'])        df['macd'] = macd['MACD_12_26_9']
        df['macd_signal'] = macd['MACDs_12_26_9']
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Volatility
        returns = df['close'].pct_change()
        volatility = returns.std() * 100
        
        if volatility < 5:
            return None
        
        # Volume
        avg_vol = df['volume'].tail(20).mean()
        current_vol = df['volume'].iloc[-1]
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        
        last = df.iloc[-1]
        price = last['close']
        
        # Signal
        score = 0
        
        if last['rsi'] < 30:
            score += 25
        elif last['rsi'] > 70:
            score -= 25
        
        if last['ema_7'] > last['ema_25'] > last['ema_99']:
            score += 30
        elif last['ema_7'] < last['ema_25'] < last['ema_99']:
            score -= 30
        
        if last['macd'] > last['macd_signal']:
            score += 20
        else:
            score -= 20
        
        if vol_ratio > 2:
            score += 20
        
        if score >= 50:
            signal = "🟢 BUY"
            direction = "LONG"
            tp1 = price * 1.03
            tp2 = price * 1.06
            tp3 = price * 1.10
            sl = price - (last['atr'] * 2)
            entry_low = price * 0.985
            entry_high = price * 0.995
        elif score <= -50:            signal = "🔴 SELL"
            direction = "SHORT"
            tp1 = price * 0.97
            tp2 = price * 0.94
            tp3 = price * 0.90
            sl = price + (last['atr'] * 2)
            entry_low = price * 1.005
            entry_high = price * 1.015
        else:
            return None
        
        trailing_5 = price * 0.95 if "BUY" in signal else price * 1.05
        
        return {
            'symbol': symbol,
            'signal': signal,
            'direction': direction,
            'price': price,
            'entry_low': entry_low,
            'entry_high': entry_high,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'sl': sl,
            'trailing_5': trailing_5,
            'leverage': self.leverage,
            'volatility': volatility,
            'rsi': last['rsi'],
            'time': datetime.now().strftime('%H:%M')
        }
    
    def send_message(self, text):
        token = os.getenv("BOT_TOKEN")
        chat_id = os.getenv("CHAT_ID")
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
        except Exception as e:
            print(f"Error: {e}")
    
    def run(self):
        print("🚀 Bot ishga tushdi!")
        self.send_message("🚀 <b>Crypto Signal Bot ishga tushdi!</b>")
        
        while True:
            try:
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
                for coin in self.all_coins:
                    signal = self.analyze_coin(coin)
                    if signal:                        msg = f"""
🚨 <b>{signal['symbol']}</b>
📊 <b>Signal:</b> {signal['signal']}
🎯 <b>Direction:</b> {signal['direction']}

💰 <b>Narx:</b> ${signal['price']:.6f}
🎯 <b>Entry:</b> ${signal['entry_low']:.6f} - ${signal['entry_high']:.6f}

📈 <b>TP1:</b> ${signal['tp1']:.6f}
📈 <b>TP2:</b> ${signal['tp2']:.6f}
📈 <b>TP3:</b> ${signal['tp3']:.6f}

🛑 <b>SL:</b> ${signal['sl']:.6f}
📉 <b>Trailing 5%:</b> ${signal['trailing_5']:.6f}

⚡ <b>Leverage:</b> {signal['leverage']}x
📊 <b>Volatility:</b> {signal['volatility']:.1f}%
⏰ {signal['time']}
"""
                        self.send_message(msg)
                        time.sleep(1)
                
                print("⏳ 5 daqiqa kutish...")
                time.sleep(300)
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = AdvancedCryptoBot()
    bot.run()