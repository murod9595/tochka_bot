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
        # 15 ta birja
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
        
        # 300+ coin
        self.all_coins = [
            # Top 20
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",
            "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
            "XLM/USDT", "NEAR/USDT", "ALGO/USDT", "BCH/USDT", "FIL/USDT",
            
            # Trending (50 ta)
            "ONDO/USDT", "SPACE/USDT", "PROM/USDT", "ARB/USDT", "OP/USDT",
            "SUI/USDT", "APT/USDT", "INJ/USDT", "TIA/USDT", "SEI/USDT",
            "ORDI/USDT", "SATS/USDT", "RATS/USDT", "BONK/USDT", "PEPE/USDT",
            "FLOKI/USDT", "SHIB/USDT", "WIF/USDT", "BOME/USDT", "SLERF/USDT",
            "MYRO/USDT", "POPCAT/USDT", "MEW/USDT", "WEN/USDT", "JUP/USDT",
            "STRK/USDT", "DYM/USDT", "PYTH/USDT", "TNSR/USDT", "SAGA/USDT",            "TAO/USDT", "OMNI/USDT", "REZ/USDT", "BB/USDT", "NOT/USDT",
            "IO/USDT", "ZK/USDT", "ZRO/USDT", "G/USDT", "BANANA/USDT",
            
            # DeFi (30 ta)
            "AAVE/USDT", "MKR/USDT", "SNX/USDT", "CRV/USDT", "COMP/USDT",
            "SUSHI/USDT", "YFI/USDT", "1INCH/USDT", "BAL/USDT", "REN/USDT",
            "KNC/USDT", "ZRX/USDT", "LRC/USDT", "STORJ/USDT", "ANT/USDT",
            
            # Gaming (30 ta)
            "SAND/USDT", "MANA/USDT", "AXS/USDT", "GALA/USDT", "ENJ/USDT",
            "CHZ/USDT", "IMX/USDT", "GMT/USDT", "GST/USDT", "SLP/USDT",
            "ALICE/USDT", "TLM/USDT", "PYR/USDT", "SKILL/USDT", "NAX/USDT",
            
            # Layer 1 (40 ta)
            "TRX/USDT", "VET/USDT", "FTM/USDT", "HBAR/USDT", "ICP/USDT",
            "THETA/USDT", "EGLD/USDT", "FLOW/USDT", "XTZ/USDT", "EOS/USDT",
            "KLAY/USDT", "MINA/USDT", "AR/USDT", "ROSE/USDT", "ONE/USDT",
            "CELO/USDT", "ZIL/USDT", "WAVES/USDT", "ICX/USDT", "ONT/USDT",
            
            # Meme (20 ta)
            "DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "FLOKI/USDT", "BONK/USDT",
            "WIF/USDT", "BOME/USDT", "MYRO/USDT", "POPCAT/USDT", "MEW/USDT",
            "BOME/USDT", "SLERF/USDT", "WEN/USDT", "BONK/USDT", "POPCAT/USDT",
            
            # AI (20 ta)
            "FET/USDT", "AGIX/USDT", "OCEAN/USDT", "RNDR/USDT", "AKT/USDT",
            "GRT/USDT", "NMR/USDT", "CTSI/USDT", "RLC/USDT", "FET/USDT",
            "OCEAN/USDT", "AGIX/USDT", "SINGULAR/USDT", "DEEP/USDT", "AI/USDT",
            
            # RWA (20 ta)
            "ONDO/USDT", "PENDLE/USDT", "POLYX/USDT", "DYM/USDT", "STRK/USDT",
            "PORTAL/USDT", "PIXEL/USDT", "ALT/USDT", "MANTA/USDT", "AEVO/USDT",
        ]
    
    def get_best_data(self, symbol):
        """Eng tez birjadan ma'lumot olish"""
        for exchange_name in list(self.exchanges.keys())[:5]:
            try:
                exchange = self.exchanges[exchange_name]
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                if ohlcv and len(ohlcv) > 0:
                    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    return df
            except Exception:
                continue
        return None
    
    def calculate_volatility(self, df):
        """Volatillikni hisoblash"""        if df is None or len(df) < 14:
            return 0
        try:
            returns = df['close'].pct_change()
            volatility = returns.std() * 100
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            atr_percent = (atr.iloc[-1] / df['close'].iloc[-1]) * 100 if len(atr) > 0 else 0
            return volatility + atr_percent
        except Exception:
            return 0
    
    def detect_breakout(self, df):
        """Breakout (sinniish) aniqlash"""
        if df is None or len(df) < 20:
            return False, None
        try:
            current_price = df['close'].iloc[-1]
            resistance = df['high'].tail(20).max()
            support = df['low'].tail(20).min()
            if current_price > resistance * 1.02:
                return True, "UP"
            if current_price < support * 0.98:
                return True, "DOWN"
        except Exception:
            pass
        return False, None
    
    def analyze_volume(self, df):
        """Hajm tahlili"""
        if df is None or len(df) < 20:
            return 0
        try:
            avg_volume = df['volume'].tail(20).mean()
            current_volume = df['volume'].iloc[-1]
            if avg_volume == 0:
                return 0
            return current_volume / avg_volume
        except Exception:
            return 0
    
    def detect_pattern(self, df):
        """Grafik patternlarni aniqlash"""
        if df is None or len(df) < 10:
            return "Unknown", 0
        try:
            highs = df['high'].tail(5).values
            lows = df['low'].tail(5).values
            
            # Double Top
            if len(highs) >= 3:                if highs[0] < highs[1] and highs[2] < highs[1] and abs(highs[0] - highs[2]) < 0.02 * highs[1]:
                    return "Double Top (Bearish)", -30
            
            # Double Bottom
            if len(lows) >= 3:
                if lows[0] > lows[1] and lows[2] > lows[1] and abs(lows[0] - lows[2]) < 0.02 * lows[1]:
                    return "Double Bottom (Bullish)", +30
            
            # Higher Highs
            if len(highs) >= 4:
                if all(highs[i] < highs[i+1] for i in range(len(highs)-1)):
                    return "Uptrend", +20
            
            # Lower Lows
            if len(lows) >= 4:
                if all(lows[i] > lows[i+1] for i in range(len(lows)-1)):
                    return "Downtrend", -20
        except Exception:
            pass
        return "No clear pattern", 0
    
    def calculate_indicators(self, df):
        """Barcha texnik indikatorlar"""
        if df is None or len(df) < 50:
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
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            df['vol_ma'] = ta.sma(df['volume'], length=20)
            return df
        except Exception:
            return None
    
    def calculate_risk(self, symbol, score):
        """AI Risk Score"""
        df = self.get_best_data(symbol)
        if df is None:
            return "HIGH", 80
        try:
            volatility = df['close'].pct_change().std() * 100
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)            current_price = df['close'].iloc[-1]
            atr_percent = (atr.iloc[-1] / current_price) * 100 if len(atr) > 0 else 0
            
            if volatility > 5 or atr_percent > 3:
                return "HIGH", 80
            elif volatility > 3 or atr_percent > 2:
                return "MEDIUM", 50
            else:
                return "LOW", 20
        except Exception:
            return "MEDIUM", 50
    
    def get_sentiment(self, coin_name):
        """Yangiliklar va sentiment tahlili"""
        try:
            url = f"https://api.coingecko.com/api/v3/search?query={coin_name}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if 'coins' in data and len(data['coins']) > 0:
                    rank = data['coins'][0].get('market_cap_rank', 'N/A')
                    return 60, f"Trending #{rank}"
        except Exception:
            pass
        return 50, "Neutral"
    
    def generate_signal_explanation(self, signal_type, indicators, volume_ratio, breakout, pattern):
        """Signal uchun tushuntirish (izoh)"""
        explanations = []
        
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            explanations.append("📊 RSI oversold (30 dan past) - narx arzonlashgan")
        elif rsi > 70:
            explanations.append("📊 RSI overbought (70 dan yuqori) - narx qimmatlashgan")
        
        if indicators.get('ema_trend') == 'bullish':
            explanations.append("📈 EMA trend yuqoriga (7>25>99) - kuchli o'sish")
        elif indicators.get('ema_trend') == 'bearish':
            explanations.append("📉 EMA trend pastga (7<25<99) - kuchli tushish")
        
        if volume_ratio > 3:
            explanations.append(f"💥 Hajm {volume_ratio:.1f}x oshdi - katta o'yinchi kirayapti!")
        elif volume_ratio > 1.5:
            explanations.append(f"📊 Hajm oshmoqda ({volume_ratio:.1f}x)")
        
        if breakout:
            if indicators.get('direction') == 'UP':
                explanations.append("🚀 Resistance (qarshilik) sindi - yuqoriga harakat")
            else:                explanations.append("💥 Support (tayanch) sindi - pastga harakat")
        
        if pattern != "Unknown" and pattern != "No clear pattern":
            explanations.append(f"📊 Pattern: {pattern}")
        
        if indicators.get('macd_signal_type') == 'bullish':
            explanations.append(" MACD bullish crossover - o'sish signali")
        elif indicators.get('macd_signal_type') == 'bearish':
            explanations.append("📊 MACD bearish crossover - tushish signali")
        
        return "\n".join(explanations) if explanations else "📊 Texnik indikatorlar ijobiy"
    
    def analyze_coin(self, symbol):
        """Bitta coin tahlili"""
        coin_name = symbol.split('/')[0]
        
        df = self.get_best_data(symbol)
        if df is None:
            return None
        
        volatility = self.calculate_volatility(df)
        if volatility < 5:
            return None
        
        df = self.calculate_indicators(df)
        if df is None:
            return None
        
        is_breakout, direction = self.detect_breakout(df)
        volume_ratio = self.analyze_volume(df)
        pattern, pattern_score = self.detect_pattern(df)
        sentiment_score, sentiment_text = self.get_sentiment(coin_name)
        
        last = df.iloc[-1]
        current_price = last['close']
        
        signal_score = 0
        signal_details = {
            'rsi': last['rsi'],
            'ema_trend': 'neutral',
            'macd_signal_type': 'neutral',
            'direction': direction
        }
        
        if last['rsi'] < 30:
            signal_score += 25
        elif last['rsi'] < 40:
            signal_score += 15
        elif last['rsi'] > 70:
            signal_score -= 25        elif last['rsi'] > 60:
            signal_score -= 15
        
        if last['ema_7'] > last['ema_25'] > last['ema_99']:
            signal_score += 30
            signal_details['ema_trend'] = 'bullish'
        elif last['ema_7'] < last['ema_25'] < last['ema_99']:
            signal_score -= 30
            signal_details['ema_trend'] = 'bearish'
        elif last['ema_7'] > last['ema_25']:
            signal_score += 15
        else:
            signal_score -= 15
        
        if last['macd'] > last['macd_signal']:
            signal_score += 20
            signal_details['macd_signal_type'] = 'bullish'
        else:
            signal_score -= 20
            signal_details['macd_signal_type'] = 'bearish'
        
        if volume_ratio > 3:
            signal_score += 20
        elif volume_ratio > 1.5:
            signal_score += 10
        
        if is_breakout:
            if direction == 'UP':
                signal_score += 25
            else:
                signal_score -= 25
        
        signal_score += pattern_score
        signal_score += (sentiment_score - 50) * 0.2
        
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
            tp1 = current_price * 1.03            tp2 = current_price * 1.06
            tp3 = current_price * 1.10
            sl = current_price - (atr * 2)
            entry_low = current_price * 0.985
            entry_high = current_price * 0.995
            trailing_3 = current_price * 0.97
            trailing_5 = current_price * 0.95
            trailing_7 = current_price * 0.93
            direction_text = "LONG"
        else:
            tp1 = current_price * 0.97
            tp2 = current_price * 0.94
            tp3 = current_price * 0.90
            sl = current_price + (atr * 2)
            entry_low = current_price * 1.005
            entry_high = current_price * 1.015
            trailing_3 = current_price * 1.03
            trailing_5 = current_price * 1.05
            trailing_7 = current_price * 1.07
            direction_text = "SHORT"
        
        risk_level, risk_score = self.calculate_risk(symbol, signal_score)
        
        explanation = self.generate_signal_explanation(
            signal_type, signal_details, volume_ratio, is_breakout, pattern
        )
        
        return {
            'symbol': symbol,
            'signal': signal_type,
            'direction': direction_text,
            'price': current_price,
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
            'risk_level': risk_level,
            'pattern': pattern,
            'explanation': explanation,
            'time': datetime.now().strftime('%H:%M:%S')
        }    
    def format_signal_message(self, data):
        """Signal xabarini formatlash"""
        message = f"""
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

📉 <b>Trailing Stop (Tavsiya):</b>
  • 3%: ${data['trailing_3']:.6f}
  • 5%: ${data['trailing_5']:.6f} ⭐
  • 7%: ${data['trailing_7']:.6f}

⚡ <b>Leverage:</b> {data['leverage']}x
⚠️ <b>Risk:</b> {data['risk_level']}

📊 <b>Statistika:</b>
  • Volatility: {data['volatility']:.2f}%
  • Volume: {data['volume_ratio']:.1f}x
  • RSI: {data['rsi']:.1f}
  • Pattern: {data['pattern']}

📝 <b>Sabab:</b>
{data['explanation']}

⏰ {data['time']}
"""
        return message
    
    def send_message(self, text):
        """Telegram ga xabar yuborish"""
        BOT_TOKEN = os.getenv("BOT_TOKEN")
        CHAT_ID = os.getenv("CHAT_ID")
        
        try:            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
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
                
                if i % 10 == 0:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ {coin} xatolik: {e}")
                continue
        
        return signals
    
    def run(self):
        """Botni ishga tushirish"""
        print("🚀 Advanced Crypto Signal Bot ishga tushdi!")
        print(f"📊 {len(self.all_coins)}+ ta coin kuzatilmoqda")
        print(f"⚡ Leverage: {self.leverage}x")
        print(f"🔄 Har 5 daqiqada yangilanadi\n")
        
        self.send_message(f"""
🚀 <b>Professional Crypto Signal Bot ishga tushdi!</b>

📊 Coins: {len(self.all_coins)}+
⚡ Leverage: {self.leverage}x
🔄 Update: Har 5 daqiqa
📈 Strategy: Short-term (1 kun ichida)
🎯 Limit Entry Zone: ✅
📉 Trailing Stop: 3%, 5%, 7%
⚠️ Risk Management: ✅
Botingiz ishlayapti! ✅
        """)
        
        while True:
            try:
                print(f"\n{'='*60}")
                print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                signals = self.scan_all_coins()
                
                if signals:
                    print(f"\n🎯 {len(signals)} ta signal topildi!")
                    
                    sorted_signals = sorted(signals, key=lambda x: abs(x.get('volatility', 0)), reverse=True)
                    
                    for signal in sorted_signals[:5]:
                        message = self.format_signal_message(signal)
                        self.send_message(message)
                        time.sleep(1)
                else:
                    print("📊 Hozircha kuchli signal yo'q")
                
                print(f"\n⏳ Keyingi skaner 5 daqiqadan keyin...")
                time.sleep(300)
                
            except Exception as e:
                print(f"❌ Xatolik: {e}")
                print("⏳ 1 daqiqa kutib qayta uriniladi...")
                time.sleep(60)

if __name__ == "__main__":
    bot = AdvancedCryptoBot()
    bot.run()