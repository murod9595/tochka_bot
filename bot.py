import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class CryptoBot:
    def __init__(self):
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}})
        self.leverage = int(os.getenv('LEVERAGE', 15))
        self.coins = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]
    
    def get_data(self, symbol):
        ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        return df
    
    def analyze(self, symbol):
        df = self.get_data(symbol)
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # EMA
        df['ema7'] = ta.ema(df['close'], length=7)
        df['ema25'] = ta.ema(df['close'], length=25)
        
        last = df.iloc[-1]
        price = last['close']
        rsi = last['rsi']
        
        # Signal
        if rsi < 30 and last['ema7'] > last['ema25']:
            signal = "BUY"
            tp = price * 1.05
            sl = price * 0.97
            entry = price * 0.99
        elif rsi > 70 and last['ema7'] < last['ema25']:
            signal = "SELL"
            tp = price * 0.95
            sl = price * 1.03
            entry = price * 1.01
        else:
            return None
        
        return {
            'coin': symbol,
            'signal': signal,
            'price': price,
            'entry': entry,
            'tp': tp,
            'sl': sl
        }
    
    def send_msg(self, text):
        token = os.getenv("BOT_TOKEN")
        chat = os.getenv("CHAT_ID")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat, "text": text, "parse_mode": "HTML"})
        except:
            pass
    
    def run(self):
        print("Bot started!")
        self.send_msg("Bot ishga tushdi!")
        
        while True:
            for coin in self.coins:
                try:
                    result = self.analyze(coin)
                    if result:
                        msg = f"""
🚨 {result['coin']}
{result['signal']}
Price: ${result['price']}
Entry: ${result['entry']}
TP: ${result['tp']}
SL: ${result['sl']}
"""
                        self.send_msg(msg)
                        time.sleep(1)
                except:
                    pass
            
            time.sleep(300)

if __name__ == "__main__":
    bot = CryptoBot()
    bot.run()