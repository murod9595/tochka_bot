import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class MomentumBot:
    def __init__(self):
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}})
        self.leverage = int(os.getenv('LEVERAGE', 15))
        
        # 200+ coin ro'yxati
        self.coins = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "MATIC/USDT", "DOT/USDT", "AVAX/USDT",
            "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "ETC/USDT",
            "XLM/USDT", "NEAR/USDT", "ALGO/USDT", "BCH/USDT", "FIL/USDT",
            "ONDO/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT", "APT/USDT",
            "INJ/USDT", "TIA/USDT", "SEI/USDT", "PEPE/USDT", "FLOKI/USDT",
            "SHIB/USDT", "WIF/USDT", "BONK/USDT", "BOME/USDT", "MYRO/USDT",
            "POPCAT/USDT", "MEW/USDT", "WEN/USDT", "JUP/USDT", "STRK/USDT",
            "DYM/USDT", "PYTH/USDT", "TNSR/USDT", "SAGA/USDT", "TAO/USDT",
            "OMNI/USDT", "REZ/USDT", "BB/USDT", "NOT/USDT", "IO/USDT",
            "ZK/USDT", "ZRO/USDT", "G/USDT", "AAVE/USDT", "MKR/USDT",
            "SNX/USDT", "CRV/USDT", "COMP/USDT", "SUSHI/USDT", "YFI/USDT",
            "1INCH/USDT", "BAL/USDT", "REN/USDT", "KNC/USDT", "ZRX/USDT",
            "LRC/USDT", "STORJ/USDT", "SAND/USDT", "MANA/USDT", "AXS/USDT",
            "GALA/USDT", "ENJ/USDT", "CHZ/USDT", "IMX/USDT", "GMT/USDT",
            "GST/USDT", "SLP/USDT", "ALICE/USDT", "TLM/USDT", "PYR/USDT",
            "TRX/USDT", "VET/USDT", "FTM/USDT", "HBAR/USDT", "ICP/USDT",
            "THETA/USDT", "EGLD/USDT", "FLOW/USDT", "XTZ/USDT", "EOS/USDT",
            "KLAY/USDT", "MINA/USDT", "AR/USDT", "ROSE/USDT", "ONE/USDT",
            "CELO/USDT", "ZIL/USDT", "WAVES/USDT", "ICX/USDT", "ONT/USDT",
            "FET/USDT", "AGIX/USDT", "OCEAN/USDT", "RNDR/USDT", "AKT/USDT",
            "GRT/USDT", "NMR/USDT", "CTSI/USDT", "RLC/USDT", "SKL/USDT",
            "ANKR/USDT", "BAND/USDT", "NKN/USDT", "OGN/USDT", "CTK/USDT",
            "DENT/USDT", "CELR/USDT", "HOT/USDT", "WIN/USDT", "BTT/USDT",
            "STMX/USDT", "DUSK/USDT", "KEY/USDT", "ARDR/USDT", "MDT/USDT",
            "STPT/USDT", "WRX/USDT", "LTO/USDT", "MBL/USDT", "COTI/USDT",
            "PERL/USDT", "TROY/USDT", "VITE/USDT", "FTT/USDT", "EUR/USDT",
            "ONG/USDT", "NULS/USDT", "TCT/USDT", "WTC/USDT", "DATA/USDT",
            "XZC/USDT", "SOL/USDT", "CTXC/USDT", "BCH/USDT", "TROY/USDT",
            "VITE/USDT", "FTT/USDT", "EUR/USDT", "RVN/USDT", "DCR/USDT",
            "MCO/USDT", "LSK/USDT", "BNT/USDT", "LUNC/USDT", "USTC/USDT",
            "NANO/USDT", "DGB/USDT", "SC/USDT", "ZEN/USDT", "RVN/USDT",            "WAN/USDT", "FUN/USDT", "CVC/USDT", "CHR/USDT", "BAND/USDT",
            "BEAM/USDT", "XTZ/USDT", "REN/USDT", "RVN/USDT", "HC/USDT",
            "HBAR/USDT", "NKN/USDT", "STX/USDT", "KAVA/USDT", "ARPA/USDT",
            "IOTX/USDT", "RLC/USDT", "MCO/USDT", "CTXC/USDT", "BCH/USDT",
            "TROY/USDT", "VITE/USDT", "FTT/USDT", "EUR/USDT", "RVN/USDT",
            "DCR/USDT", "MCO/USDT", "LSK/USDT", "BNT/USDT", "LUNC/USDT",
            "USTC/USDT", "NANO/USDT", "DGB/USDT", "SC/USDT", "ZEN/USDT",
            "RVN/USDT", "WAN/USDT", "FUN/USDT", "CVC/USDT", "CHR/USDT",
        ]
    
    def get_data(self, symbol):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=50)
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            return df
        except Exception:
            return None
    
    def check_momentum(self, symbol):
        df = self.get_data(symbol)
        if df is None or len(df) < 20:
            return None
        
        # Volatility hisoblash
        returns = df['close'].pct_change()
        volatility = returns.std() * 100
        
        # Faqat yuqori volatillikli coinlarni olamiz
        if volatility < 5:
            return None
        
        # Volume spike tekshirish
        avg_volume = df['volume'].tail(20).mean()
        current_volume = df['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # Volume kam bo'lsa o'tkazamiz
        if volume_ratio < 1.5:
            return None
        
        # Indikatorlar
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema7'] = ta.ema(df['close'], length=7)
        df['ema25'] = ta.ema(df['close'], length=25)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        last = df.iloc[-1]
        price = last['close']
        rsi = last['rsi']        atr = last['atr']
        
        # Breakout tekshirish
        high_20 = df['high'].tail(20).max()
        low_20 = df['low'].tail(20).min()
        
        # Signal hisoblash
        score = 0
        direction = None
        
        # RSI signal
        if rsi < 35:
            score += 30
            direction = "LONG"
        elif rsi > 65:
            score -= 30
            direction = "SHORT"
        
        # EMA crossover
        if last['ema7'] > last['ema25']:
            score += 25
            if direction is None:
                direction = "LONG"
        else:
            score -= 25
            if direction is None:
                direction = "SHORT"
        
        # Volume signal
        if volume_ratio > 3:
            score += 25
        elif volume_ratio > 2:
            score += 15
        
        # Breakout signal
        if price > high_20 * 1.02:
            score += 20
            direction = "LONG"
        elif price < low_20 * 0.98:
            score -= 20
            direction = "SHORT"
        
        # Agar signal kuchli bo'lsa
        if abs(score) >= 50 and direction:
            if direction == "LONG":
                signal = "🟢 BUY"
                tp1 = price * 1.03
                tp2 = price * 1.06
                tp3 = price * 1.10
                sl = price - (atr * 2)                entry_low = price * 0.985
                entry_high = price * 0.995
                trailing = price * 0.95
            else:
                signal = "🔴 SELL"
                tp1 = price * 0.97
                tp2 = price * 0.94
                tp3 = price * 0.90
                sl = price + (atr * 2)
                entry_low = price * 1.005
                entry_high = price * 1.015
                trailing = price * 1.05
            
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
                'trailing': trailing,
                'leverage': self.leverage,
                'volatility': volatility,
                'volume_ratio': volume_ratio,
                'rsi': rsi,
                'time': datetime.now().strftime('%H:%M')
            }
        
        return None
    
    def send_message(self, text):
        token = os.getenv("BOT_TOKEN")
        chat_id = os.getenv("CHAT_ID")
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
            print("✅ Xabar yuborildi")
        except Exception as e:
            print(f"❌ Xatolik: {e}")
    
    def run(self):
        print("🚀 Momentum Bot ishga tushdi!")
        print(f"📊 {len(self.coins)} ta coin skanerlanmoqda")
        
        self.send_message(f"🚀 <b>Momentum Bot ishga tushdi!</b>\n📊 Coins: {len(self.coins)}\n⚡ Leverage: {self.leverage}x\n🔍 Strategy: Volume + Breakout")
                while True:
            try:
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Skanerlash boshlandi...")
                signals_found = 0
                
                for coin in self.coins:
                    try:
                        result = self.check_momentum(coin)
                        if result:
                            signals_found += 1
                            print(f"✅ {coin}: {result['signal']} | Vol: {result['volatility']:.1f}% | VolRatio: {result['volume_ratio']:.1f}x")
                            
                            msg = f"""
🚨 <b>YANGI SIGNAL!</b>

💎 <b>Coin:</b> {result['symbol']}
📊 <b>Signal:</b> {result['signal']}
🎯 <b>Direction:</b> {result['direction']}

💰 <b>Narx:</b> ${result['price']:.6f}

🎯 <b>Limit Entry:</b>
${result['entry_low']:.6f} - ${result['entry_high']:.6f}

📈 <b>Take Profit:</b>
  TP1: ${result['tp1']:.6f} (+3%)
  TP2: ${result['tp2']:.6f} (+6%)
  TP3: ${result['tp3']:.6f} (+10%)

🛑 <b>Stop Loss:</b> ${result['sl']:.6f}

📉 <b>Trailing Stop 5%:</b> ${result['trailing']:.6f}

⚡ <b>Leverage:</b> {result['leverage']}x

📊 <b>Statistika:</b>
  • Volatility: {result['volatility']:.1f}%
  • Volume: {result['volume_ratio']:.1f}x
  • RSI: {result['rsi']:.1f}

⏰ {result['time']}
"""
                            self.send_message(msg)
                            time.sleep(1)
                    except Exception:
                        continue
                
                print(f"✅ Jami: {signals_found} ta signal topildi")
                print("⏳ 5 daqiqa kutish...")
                time.sleep(300)                
            except Exception as e:
                print(f"❌ Xatolik: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = MomentumBot()
    bot.run()