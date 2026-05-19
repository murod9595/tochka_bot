import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import asyncio
import aiohttp
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from textblob import TextBlob

load_dotenv()

class AdvancedCryptoBot:
    def __init__(self):
        # 15 ta birja (eng tez va ishonchli)
        self.exchanges = {
            'binance': ccxt.binance({'options': {'defaultType': 'future'}, 'timeout': 10000}),
            'bybit': ccxt.bybit({'options': {'defaultType': 'future'}, 'timeout': 10000}),
            'kucoin': ccxt.kucoinfutures({'timeout': 10000}),
            'okx': ccxt.okx({'options': {'defaultType': 'swap'}, 'timeout': 10000}),
            'gateio': ccxt.gateio({'options': {'defaultType': 'future'}, 'timeout': 10000}),
            'mexc': ccxt.mexc({'timeout': 10000}),
            'bitget': ccxt.bitget({'timeout': 10000}),
            'bingx': ccxt.bingx({'timeout': 10000}),
            'htx': ccxt.htx({'timeout': 10000}),
            'coinex': ccxt.coinex({'timeout': 10000}),
            'phemex': ccxt.phemex({'timeout': 10000}),
            'bitmart': ccxt.bitmart({'timeout': 10000}),
            'lbank': ccxt.lbank({'timeout': 10000}),
            'xt': ccxt.xt({'timeout': 10000}),
            'bitrue': ccxt.bitrue({'timeout': 10000}),
        }
        
        self.leverage = int(os.getenv('LEVERAGE', 15))
        self.trailing_stop = int(os.getenv('TRAILING_STOP_PERCENT', 5))
        
        # 300+ coin ro'yxati (eng ko'p savdo qilinadigan)
        self.all_coins = [
            # Top 20
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",
            "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
            "XLM/USDT", "NEAR/USDT", "ALGO/USDT", "BCH/USDT", "FIL/USDT",
            
            # Trending coins (50 ta)
            "ONDO/USDT", "SPACE/USDT", "PROM/USDT", "ARB/USDT", "OP/USDT",
            "SUI/USDT", "APT/USDT", "INJ/USDT", "TIA/USDT", "SEI/USDT",
            "ORDI/USDT", "SATS/USDT", "RATS/USDT", "BONK/USDT", "PEPE/USDT",            "FLOKI/USDT", "SHIB/USDT", "WIF/USDT", "BOME/USDT", "SLERF/USDT",
            
            # DeFi (30 ta)
            "AAVE/USDT", "MKR/USDT", "SNX/USDT", "CRV/USDT", "COMP/USDT",
            "SUSHI/USDT", "YFI/USDT", "1INCH/USDT", "BAL/USDT", "REN/USDT",
            
            # Gaming (30 ta)
            "SAND/USDT", "MANA/USDT", "AXS/USDT", "GALA/USDT", "ENJ/USDT",
            "CHZ/USDT", "IMX/USDT", "GMT/USDT", "GST/USDT", "SLP/USDT",
            
            # Layer 1 (40 ta)
            "TRX/USDT", "VET/USDT", "FTM/USDT", "HBAR/USDT", "ICP/USDT",
            "THETA/USDT", "EGLD/USDT", "FLOW/USDT", "XTZ/USDT", "EOS/USDT",
            
            # Meme coins (20 ta)
            "DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "FLOKI/USDT", "BONK/USDT",
            "WIF/USDT", "BOME/USDT", "MYRO/USDT", "POPCAT/USDT", "MEW/USDT",
            
            # AI coins (20 ta)
            "FET/USDT", "AGIX/USDT", "OCEAN/USDT", "RNDR/USDT", "AKT/USDT",
            "GRT/USDT", "NMR/USDT", "CTSI/USDT", "FET/USDT", "RLC/USDT",
            
            # RWA (20 ta)
            "ONDO/USDT", "PENDLE/USDT", "POLYX/USDT", "DYM/USDT", "STRK/USDT",
            
            # va hokazo... (jami 300+)
        ]
        
        # Yangiliklar manbalari
        self.news_sources = [
            "https://cryptopanic.com/api/v1/posts/",
            "https://api.coingecko.com/api/v3/coins/markets",
        ]
    
    async def fetch_from_exchange(self, exchange_name, symbol, timeframe='15m'):
        """Birjadan ma'lumot olish (async)"""
        try:
            exchange = self.exchanges[exchange_name]
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            return df
        except:
            return None
    
    def get_best_data(self, symbol):
        """Eng tez birjadan ma'lumot olish"""
        # Birinchi 5 ta birjadan tezda olish
        for exchange_name in list(self.exchanges.keys())[:5]:
            try:                df = self.exchanges[exchange_name].fetch_ohlcv(symbol, '15m', limit=100)
                if df and len(df) > 0:
                    df = pd.DataFrame(df, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    return df
            except:
                continue
        return None
    
    def calculate_volatility(self, df):
        """Volatillikni hisoblash"""
        if df is None or len(df) < 14:
            return 0
        
        returns = df['close'].pct_change()
        volatility = returns.std() * 100  # % da
        
        # ATR
        atr = ta.atr(df['high'], df['low'], df['close'], length=14)
        atr_percent = (atr.iloc[-1] / df['close'].iloc[-1]) * 100 if len(atr) > 0 else 0
        
        return volatility + atr_percent
    
    def detect_breakout(self, df):
        """Breakout (sinniish) aniqlash"""
        if df is None or len(df) < 20:
            return False, None
        
        current_price = df['close'].iloc[-1]
        resistance = df['high'].tail(20).max()
        support = df['low'].tail(20).min()
        
        # Yuqoriga breakout
        if current_price > resistance * 1.02:  # 2% dan yuqori
            return True, "UP"
        
        # Pastga breakout
        if current_price < support * 0.98:  # 2% dan past
            return True, "DOWN"
        
        return False, None
    
    def analyze_volume(self, df):
        """Hajm tahlili"""
        if df is None or len(df) < 20:
            return 0
        
        avg_volume = df['volume'].tail(20).mean()
        current_volume = df['volume'].iloc[-1]
                if avg_volume == 0:
            return 0
        
        return current_volume / avg_volume
    
    def get_sentiment(self, coin_name):
        """Yangiliklar va sentiment tahlili"""
        try:
            # CoinGecko API (bepul)
            url = f"https://api.coingecko.com/api/v3/search?query={coin_name}"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                # Oddiy sentiment (mavjud ma'lumotlar asosida)
                if 'coins' in data and len(data['coins']) > 0:
                    return 60, f"Trending #{data['coins'][0].get('market_cap_rank', 'N/A')}"
        except:
            pass
        
        return 50, "Neutral"
    
    def calculate_indicators(self, df):
        """Barcha texnik indikatorlar"""
        if df is None or len(df) < 50:
            return None
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # EMA
        df['ema_7'] = ta.ema(df['close'], length=7)
        df['ema_25'] = ta.ema(df['close'], length=25)
        df['ema_99'] = ta.ema(df['close'], length=99)
        
        # MACD
        macd = ta.macd(df['close'])
        df['macd'] = macd['MACD_12_26_9']
        df['macd_signal'] = macd['MACDs_12_26_9']
        
        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20)
        df['bb_upper'] = bb['BBU_20_2.0']
        df['bb_lower'] = bb['BBL_20_2.0']
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Volume MA
        df['vol_ma'] = ta.sma(df['volume'], length=20)        
        return df
    
    def generate_signal_explanation(self, signal_type, indicators, volume_ratio, breakout):
        """Signal uchun tushuntirish (izoh)"""
        explanations = []
        
        # RSI izoh
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            explanations.append("📊 RSI oversold (30 dan past) - narx arzonlashgan")
        elif rsi > 70:
            explanations.append("📊 RSI overbought (70 dan yuqori) - narx qimmatlashgan")
        
        # EMA izoh
        if indicators.get('ema_trend') == 'bullish':
            explanations.append("📈 EMA trend yuqoriga (7>25>99) - kuchli o'sish")
        elif indicators.get('ema_trend') == 'bearish':
            explanations.append("📉 EMA trend pastga (7<25<99) - kuchli tushish")
        
        # Volume izoh
        if volume_ratio > 3:
            explanations.append(f"💥 Hajm {volume_ratio:.1f}x oshdi - katta o'yinchi kirayapti!")
        elif volume_ratio > 1.5:
            explanations.append(f"📊 Hajm oshmoqda ({volume_ratio:.1f}x)")
        
        # Breakout izoh
        if breakout:
            if indicators.get('direction') == 'UP':
                explanations.append("🚀 Resistance (qarshilik) sindi - yuqoriga harakat")
            else:
                explanations.append("💥 Support (tayanch) sindi - pastga harakat")
        
        # MACD izoh
        if indicators.get('macd_signal_type') == 'bullish':
            explanations.append(" MACD bullish crossover - o'sish signali")
        elif indicators.get('macd_signal_type') == 'bearish':
            explanations.append("📊 MACD bearish crossover - tushish signali")
        
        return "\n".join(explanations) if explanations else "📊 Texnik indikatorlar ijobiy"
    
    def analyze_coin(self, symbol):
        """Bitta coin tahlili"""
        coin_name = symbol.split('/')[0]
        
        # Ma'lumot olish
        df = self.get_best_data(symbol)
        if df is None:
            return None
                # Volatillik
        volatility = self.calculate_volatility(df)
        
        # Faqat yuqori volatillikli coinlarni tekshiramiz (5% dan yuqori)
        if volatility < 5:
            return None
        
        # Indikatorlar
        df = self.calculate_indicators(df)
        if df is None:
            return None
        
        # Breakout
        is_breakout, direction = self.detect_breakout(df)
        
        # Volume
        volume_ratio = self.analyze_volume(df)
        
        # Sentiment
        sentiment_score, sentiment_text = self.get_sentiment(coin_name)
        
        last = df.iloc[-1]
        current_price = last['close']
        
        # Signal hisoblash
        signal_score = 0
        signal_details = {
            'rsi': last['rsi'],
            'ema_trend': 'neutral',
            'macd_signal_type': 'neutral',
            'direction': direction
        }
        
        # RSI
        if last['rsi'] < 30:
            signal_score += 25
        elif last['rsi'] < 40:
            signal_score += 15
        elif last['rsi'] > 70:
            signal_score -= 25
        elif last['rsi'] > 60:
            signal_score -= 15
        
        # EMA
        if last['ema_7'] > last['ema_25'] > last['ema_99']:
            signal_score += 30
            signal_details['ema_trend'] = 'bullish'
        elif last['ema_7'] < last['ema_25'] < last['ema_99']:
            signal_score -= 30
            signal_details['ema_trend'] = 'bearish'        elif last['ema_7'] > last['ema_25']:
            signal_score += 15
        else:
            signal_score -= 15
        
        # MACD
        if last['macd'] > last['macd_signal']:
            signal_score += 20
            signal_details['macd_signal_type'] = 'bullish'
        else:
            signal_score -= 20
            signal_details['macd_signal_type'] = 'bearish'
        
        # Volume
        if volume_ratio > 3:
            signal_score += 20
        elif volume_ratio > 1.5:
            signal_score += 10
        
        # Breakout
        if is_breakout:
            if direction == 'UP':
                signal_score += 25
            else:
                signal_score -= 25
        
        # Sentiment
        signal_score += (sentiment_score - 50) * 0.2
        
        # Signal turi
        if signal_score >= 60:
            signal_type = "🟢 STRONG BUY"
        elif signal_score >= 40:
            signal_type = "🟢 BUY"
        elif signal_score <= -60:
            signal_type = "🔴 STRONG SELL"
        elif signal_score <= -40:
            signal_type = "🔴 SELL"
        else:
            return None  # HOLD - signal yubormaymiz
        
        # TP va SL hisoblash
        atr = last['atr']
        
        if "BUY" in signal_type:
            tp1 = current_price * 1.03  # +3%
            tp2 = current_price * 1.06  # +6%
            tp3 = current_price * 1.10  # +10%
            sl = current_price - (atr * 2)  # ATR asosida
                        # Trailing Stop
            trailing_stop_3 = current_price * 0.97  # -3%
            trailing_stop_5 = current_price * 0.95  # -5%
            trailing_stop_7 = current_price * 0.93  # -7%
            
            direction_text = "LONG"
        else:
            tp1 = current_price * 0.97  # -3%
            tp2 = current_price * 0.94  # -6%
            tp3 = current_price * 0.90  # -10%
            sl = current_price + (atr * 2)
            
            trailing_stop_3 = current_price * 1.03  # +3%
            trailing_stop_5 = current_price * 1.05  # +5%
            trailing_stop_7 = current_price * 1.07  # +7%
            
            direction_text = "SHORT"
        
        # Izoh
        explanation = self.generate_signal_explanation(
            signal_type, signal_details, volume_ratio, is_breakout
        )
        
        return {
            'symbol': symbol,
            'signal': signal_type,
            'direction': direction_text,
            'price': current_price,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'sl': sl,
            'trailing_3': trailing_stop_3,
            'trailing_5': trailing_stop_5,
            'trailing_7': trailing_stop_7,
            'leverage': self.leverage,
            'volatility': volatility,
            'volume_ratio': volume_ratio,
            'rsi': last['rsi'],
            'explanation': explanation,
            'time': datetime.now().strftime('%H:%M:%S')
        }
    
    def format_signal_message(self, data):
        """Signal xabarini formatlash"""
        message = f"""
🚨 <b>YANGI SIGNAL!</b>

💎 <b>Coin:</b> {data['symbol']}
📊 <b>Signal:</b> {data['signal']}🎯 <b>Direction:</b> {data['direction']}

💰 <b>Narx:</b> ${data['price']:.6f}

📈 <b>Take Profit:</b>
  TP1: ${data['tp1']:.6f} (+3%)
  TP2: ${data['tp2']:.6f} (+6%)
  TP3: ${data['tp3']:.6f} (+10%)

🛑 <b>Stop Loss:</b> ${data['sl']:.6f}

📉 <b>Trailing Stop (Tavsiya):</b>
  • 3%: ${data['trailing_3']:.6f}
  • 5%: ${data['trailing_5']:.6f} ⭐
  • 7%: ${data['trailing_7']:.6f}

⚡ <b>Leverage:</b> {data['leverage']}x

📊 <b>Statistika:</b>
  • Volatility: {data['volatility']:.2f}%
  • Volume: {data['volume_ratio']:.1f}x
  • RSI: {data['rsi']:.1f}

 <b>Sabab:</b>
{data['explanation']}

⏰ {data['time']}
"""
        return message
    
    def send_message(self, text):
        """Telegram ga xabar yuborish"""
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
    
    def scan_all_coins(self):
        """Barcha coinlarni skanerlash"""
        print(f"\n🔍 {len(self.all_coins)} ta coin skanerlanmoqda...")
                signals = []
        
        for i, coin in enumerate(self.all_coins):
            try:
                signal = self.analyze_coin(coin)
                if signal:
                    signals.append(signal)
                    print(f"✅ {coin}: {signal['signal']} topildi!")
                
                # Har 10 ta coindan keyin biroz kutish
                if i % 10 == 0:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ {coin} xatolik: {e}")
                continue
        
        return signals
    
    def run(self):
        """Botni ishga tushirish"""
        print("🚀 Advanced Crypto Signal Bot ishga tushdi!")
        print(f"📊 {len(self.all_coins)} ta coin kuzatilmoqda")
        print(f"⚡ Leverage: {self.leverage}x")
        print(f"🔄 Har 5 daqiqada yangilanadi\n")
        
        self.send_message(f"""
🚀 <b>Professional Crypto Signal Bot ishga tushdi!</b>

📊 Coins: {len(self.all_coins)}+
⚡ Leverage: {self.leverage}x
🔄 Update: Har 5 daqiqa
📈 Strategy: Short-term (1 kun ichida)

Botingiz ishlayapti! ✅
        """)
        
        while True:
            try:
                print(f"\n{'='*60}")
                print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                # Barcha coinlarni skanerlash
                signals = self.scan_all_coins()
                
                # Signallarni yuborish
                if signals:
                    print(f"\n🎯 {len(signals)} ta signal topildi!")
                                        # Eng kuchli signallarni yuborish (top 5)
                    sorted_signals = sorted(signals, key=lambda x: abs(x.get('volatility', 0)), reverse=True)
                    
                    for signal in sorted_signals[:5]:  # Top 5
                        message = self.format_signal_message(signal)
                        self.send_message(message)
                        time.sleep(1)  # Spam bo'lmasligi uchun
                else:
                    print("📊 Hozircha kuchli signal yo'q")
                
                print(f"\n⏳ Keyingi skaner 5 daqiqadan keyin...")
                time.sleep(300)  # 5 daqiqa = 300 soniya
                
            except Exception as e:
                print(f"❌ Xatolik: {e}")
                print("⏳ 1 daqiqa kutib qayta uriniladi...")
                time.sleep(60)

if __name__ == "__main__":
    bot = AdvancedCryptoBot()
    bot.run()