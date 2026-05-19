import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class OptimizedBot:
    def __init__(self):
        # 5 ta asosiy birja (yetarli!)
        self.exchanges = {
            'binance': ccxt.binance({'options': {'defaultType': 'future'}}),
            'bybit': ccxt.bybit({'options': {'defaultType': 'future'}}),
            'okx': ccxt.okx({'options': {'defaultType': 'swap'}}),
        }
        
        self.leverage = int(os.getenv('LEVERAGE', 15))
        
        # 50 ta eng muhim coin
        self.coins = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",
            "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ONDO/USDT",
            "ARB/USDT", "OP/USDT", "SUI/USDT", "APT/USDT", "INJ/USDT",
            "PEPE/USDT", "FLOKI/USDT", "SHIB/USDT", "WIF/USDT", "BONK/USDT",
        ]
        
        # Yangiliklar API
        self.cryptopanic_token = os.getenv('CRYPTOPANIC_TOKEN', '')
    
    def get_fear_greed(self):
        """Fear & Greed Index"""
        try:
            url = "https://api.alternative.me/fng/"
            resp = requests.get(url, timeout=5).json()
            value = int(resp['data'][0]['value'])
            
            if value < 30:
                return f"Extreme Fear ({value}) - Sotib olish vaqti!", 20
            elif value < 50:
                return f"Fear ({value}) - Ehtiyot bo'ling", 10
            elif value < 70:
                return f"Greed ({value}) - Ehtiyot", -10
            else:
                return f"Extreme Greed ({value}) - Sotish vaqti!", -20
        except:            return "Unknown", 0
    
    def get_trending_coins(self):
        """CoinGecko trending"""
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            data = requests.get(url, timeout=5).json()
            trending = [coin['name'] for coin in data['coins'][:5]]
            return trending
        except:
            return []
    
    def get_news_sentiment(self, coin_name):
        """Yangiliklar sentiment (CryptoPanic)"""
        if not self.cryptopanic_token:
            return 0, "No token"
        
        try:
            url = f"https://cryptopanic.com/api/v1/posts/"
            params = {
                "auth_token": self.cryptopanic_token,
                "currencies": coin_name,
                "kind": "news"
            }
            resp = requests.get(url, params=params, timeout=5).json()
            
            positive = 0
            negative = 0
            
            for post in resp.get('results', [])[:10]:
                if post.get('sentiment') == 'positive':
                    positive += 1
                elif post.get('sentiment') == 'negative':
                    negative += 1
            
            score = positive - negative
            return score, f"+{positive}/-{negative}"
        except:
            return 0, "Error"
    
    def get_data(self, symbol):
        """Eng tez birjadan ma'lumot"""
        for name, exchange in self.exchanges.items():
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                return df
            except:
           return None
    
    def analyze(self, symbol):
        df = self.get_data(symbol)
        if df is None or len(df) < 50:
            return None
        
        # Indicators
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema7'] = ta.ema(df['close'], length=7)
        df['ema25'] = ta.ema(df['close'], length=25)
        df['ema99'] = ta.ema(df['close'], length=99)
        macd = ta.macd(df['close'])
        df['macd'] = macd['MACD_12_26_9']
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
        coin_name = symbol.split('/')[0]
        
        # News sentiment
        news_score, news_text = self.get_news_sentiment(coin_name)
        
        # Signal
        score = 0
        
        if last['rsi'] < 30:
            score += 25
        elif last['rsi'] > 70:
            score -= 25
        
        if last['ema7'] > last['ema25'] > last['ema99']:
            score += 30
        elif last['ema7'] < last['ema25'] < last['ema99']:
            score -= 30
        
        if last['macd'] > last['macd_signal']:            score += 20
        else:
            score -= 20
        
        if vol_ratio > 2:
            score += 20
        
        # News ta'siri
        score += news_score * 5
        
        if score >= 50:
            signal = "🟢 BUY"
            direction = "LONG"
            tp1 = price * 1.03
            tp2 = price * 1.06
            tp3 = price * 1.10
            sl = price - (last['atr'] * 2)
            entry_low = price * 0.985
            entry_high = price * 0.995
        elif score <= -50:
            signal = "🔴 SELL"
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
            'news': news_text,
            'time': datetime.now().strftime('%H:%M')        }
    
    def send_msg(self, text):
        token = os.getenv("BOT_TOKEN")
        chat = os.getenv("CHAT_ID")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat, "text": text, "parse_mode": "HTML"})
        except:
            pass
    
    def run(self):
        print("🚀 Optimized Bot ishga tushdi!")
        
        # Fear & Greed
        fear_greed, fg_score = self.get_fear_greed()
        self.send_msg(f"🚀 <b>Bot ishga tushdi!</b>\n📊 {fear_greed}")
        
        while True:
            try:
                # Trending coins
                trending = self.get_trending_coins()
                
                for coin in self.coins:
                    result = self.analyze(coin)
                    if result:
                        coin_name = result['symbol'].split('/')[0]
                        is_trending = "🔥" if coin_name in trending else ""
                        
                        msg = f"""
🚨 {result['symbol']} {is_trending}
{result['signal']} | {result['direction']}

💰 Narx: ${result['price']:.6f}
🎯 Entry: ${result['entry_low']:.6f} - ${result['entry_high']:.6f}

📈 TP1: ${result['tp1']:.6f}
📈 TP2: ${result['tp2']:.6f}
📈 TP3: ${result['tp3']:.6f}

🛑 SL: ${result['sl']:.6f}
📉 Trailing 5%: ${result['trailing_5']:.6f}

⚡ Leverage: {result['leverage']}x
📊 Volatility: {result['volatility']:.1f}%
📰 News: {result['news']}
⏰ {result['time']}
"""
                        self.send_msg(msg)
                        time.sleep(1)                
                time.sleep(300)  # 5 daqiqa
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = OptimizedBot()
    bot.run()