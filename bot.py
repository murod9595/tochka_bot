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
            'binance': ccxt.binance({'options': {'defaultType': 'future'}, 'timeout': 10000}),
            'bybit': ccxt.bybit({'options': {'defaultType': 'future'}, 'timeout': 10000}),
            'kucoin': ccxt.kucoinfutures({'timeout': 10000}),
            'okx': ccxt.okx({'options': {'defaultType': 'swap'}, 'timeout': 10000}),
            'gateio': ccxt.gateio({'options': {'defaultType': 'future'}, 'timeout': 10000}),
        }
        
        self.leverage = int(os.getenv('LEVERAGE', 15))
        
        self.all_coins = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",
            "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
            "ONDO/USDT", "SPACE/USDT", "PROM/USDT", "ARB/USDT", "OP/USDT",
            "SUI/USDT", "APT/USDT", "INJ/USDT", "TIA/USDT", "SEI/USDT",
            "PEPE/USDT", "FLOKI/USDT", "SHIB/USDT", "WIF/USDT", "BONK/USDT",
        ]
    
    def get_best_data(self, symbol):
        try:
            for exchange_name in list(self.exchanges.keys())[:3]:
                try:
                    exchange = self.exchanges[exchange_name]
                    ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                    if ohlcv and len(ohlcv) > 0:
                        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                        df['time'] = pd.to_datetime(df['time'], unit='ms')
                        return df
                except:
                    continue
        except:
            pass
        return None
    
    def calculate_volatility(self, df):
        try:            if df is None or len(df) < 14:
                return 0
            returns = df['close'].pct_change()
            volatility = returns.std() * 100
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            atr_percent = (atr.iloc[-1] / df['close'].iloc[-1]) * 100 if len(atr) > 0 else 0
            return volatility + atr_percent
        except:
            return 0
    
    def detect_breakout(self, df):
        try:
            if df is None or len(df) < 20:
                return False, None
            current_price = df['close'].iloc[-1]
            resistance = df['high'].tail(20).max()
            support = df['low'].tail(20).min()
            if current_price > resistance * 1.02:
                return True, "UP"
            if current_price < support * 0.98:
                return True, "DOWN"
        except:
            pass
        return False, None
    
    def analyze_volume(self, df):
        try:
            if df is None or len(df) < 20:
                return 0
            avg_volume = df['volume'].tail(20).mean()
            current_volume = df['volume'].iloc[-1]
            if avg_volume == 0:
                return 0
            return current_volume / avg_volume
        except:
            return 0
    
    def calculate_indicators(self, df):
        try:
            if df is None or len(df) < 50:
                return None
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema_7'] = ta.ema(df['close'], length=7)
            df['ema_25'] = ta.ema(df['close'], length=25)
            df['ema_99'] = ta.ema(df['close'], length=99)
            macd = ta.macd(df['close'])
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            return df        except:
            return None
    
    def analyze_coin(self, symbol):
        try:
            df = self.get_best_data(symbol)
            if df is None or len(df) < 50:
                return None
            
            volatility = self.calculate_volatility(df)
            if volatility < 5:
                return None
            
            df = self.calculate_indicators(df)
            if df is None:
                return None
            
            is_breakout, direction = self.detect_breakout(df)
            volume_ratio = self.analyze_volume(df)
            
            last = df.iloc[-1]
            current_price = last['close']
            
            signal_score = 0
            if last['rsi'] < 30:
                signal_score += 25
            elif last['rsi'] < 40:
                signal_score += 15
            elif last['rsi'] > 70:
                signal_score -= 25
            elif last['rsi'] > 60:
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
                signal_score += 20
            elif volume_ratio > 1.5:                signal_score += 10
            
            if is_breakout:
                if direction == 'UP':
                    signal_score += 25
                else:
                    signal_score -= 25
            
            if signal_score >= 60:
                signal_type = "🟢 STRONG BUY"
            elif signal_score >= 40:
                signal_type = "🟢 BUY"
            elif signal_score <= -60:
                signal_type = "🔴 STRONG SELL"
            elif signal_score <= -40:
                signal_type = "🔴 SELL"
            else:
                return None
            
            atr = last['atr']
            
            if "BUY" in signal_type:
                direction_text = "LONG"
                tp1 = current_price * 1.03
                tp2 = current_price * 1.06
                tp3 = current_price * 1.10
                sl = current_price - (atr * 2)
                entry_low = current_price * 0.985
                entry_high = current_price * 0.995
            else:
                direction_text = "SHORT"
                tp1 = current_price * 0.97
                tp2 = current_price * 0.94
                tp3 = current_price * 0.90
                sl = current_price + (atr * 2)
                entry_low = current_price * 1.005
                entry_high = current_price * 1.015
            
            trailing_3 = current_price * 0.97 if "BUY" in signal_type else current_price * 1.03
            trailing_5 = current_price * 0.95 if "BUY" in signal_type else current_price * 1.05
            trailing_7 = current_price * 0.93 if "BUY" in signal_type else current_price * 1.07
            
            explanation = f"Volatility: {volatility:.1f}%\nVolume: {volume_ratio:.1f}x\nRSI: {last['rsi']:.1f}"
            if is_breakout:
                explanation += f"\nBreakout: {direction}"
            
            return {
                'symbol': symbol,
                'signal': signal_type,
                'direction': direction_text,                'price': current_price,
                'entry_low': entry_low,
                'entry_high': entry_high,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'sl': sl,
                'trailing_3': trailing_3,
                'trailing_5': trailing_5,
                'trailing_7': trailing_7,
                'leverage': self.leverage,
                'volatility': volatility,
                'volume_ratio': volume_ratio,
                'rsi': last['rsi'],
                'explanation': explanation,
                'time': datetime.now().strftime('%H:%M:%S')
            }
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None
    
    def format_signal_message(self, data):
        return f"""
🚨 <b>YANGI SIGNAL!</b>

💎 <b>Coin:</b> {data['symbol']}
📊 <b>Signal:</b> {data['signal']}
🎯 <b>Direction:</b> {data['direction']}

💰 <b>Narx:</b> ${data['price']:.6f}

🎯 <b>Limit Entry Zone:</b>
${data['entry_low']:.6f} - ${data['entry_high']:.6f}
⚠️ <i>Shu oraliqda limit order qo'ying</i>

📈 <b>Take Profit:</b>
  TP1: ${data['tp1']:.6f} (+3%)
  TP2: ${data['tp2']:.6f} (+6%)
  TP3: ${data['tp3']:.6f} (+10%)

🛑 <b>Stop Loss:</b> ${data['sl']:.6f}

📉 <b>Trailing Stop:</b>
  • 3%: ${data['trailing_3']:.6f}
  • 5%: ${data['trailing_5']:.6f} ⭐
  • 7%: ${data['trailing_7']:.6f}

⚡ <b>Leverage:</b> {data['leverage']}x

📊 <b>Statistika:</b>{data['explanation']}

⏰ {data['time']}
"""
    
    def send_message(self, text):
        BOT_TOKEN = os.getenv("BOT_TOKEN")
        CHAT_ID = os.getenv("CHAT_ID")
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            })
            print("✅ Xabar yuborildi")
        except Exception as e:
            print(f"❌ Xabar yuborilmadi: {e}")
    
    def run(self):
        print("🚀 Advanced Crypto Signal Bot ishga tushdi!")
        print(f"📊 {len(self.all_coins)} ta coin kuzatilmoqda")
        
        self.send_message(f"🚀 <b>Bot ishga tushdi!</b>\n📊 Coins: {len(self.all_coins)}\n⚡ Leverage: {self.leverage}x")
        
        while True:
            try:
                print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                signals = []
                
                for coin in self.all_coins:
                    try:
                        signal = self.analyze_coin(coin)
                        if signal:
                            signals.append(signal)
                            print(f"✅ {coin}: {signal['signal']}")
                    except:
                        continue
                
                if signals:
                    print(f"🎯 {len(signals)} ta signal topildi!")
                    for signal in signals[:5]:
                        message = self.format_signal_message(signal)
                        self.send_message(message)
                        time.sleep(1)
                else:
                    print("📊 Hozircha signal yo'q")
                
                print("⏳ 5 daqiqa kutish...")
                time.sleep(300)                
            except Exception as e:
                print(f"❌ Xatolik: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = AdvancedCryptoBot()
    bot.run()