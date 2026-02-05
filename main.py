from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Optional
import yfinance as yf
import httpx
import asyncio
import logging
import pandas as pd

# ---------------------------------------------------------
# 🔐 SECRETS (ARMED & READY)
# ---------------------------------------------------------
TELEGRAM_TOKEN = "8151699023:AAE-S5zM6rigQwaQMJ3AXgYHJzxPQaaS9W0"
TELEGRAM_CHAT_ID = "7086092666"
RENDER_URL = "https://ape-brain.onrender.com" 
# ---------------------------------------------------------

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ApeSentinel")

# 🧠 MEMORY (The Watchlist lives here for now)
WATCHLIST = {}

# Data Models
class StockData(BaseModel):
    symbol: str
    target1: Optional[float] = None
    target2: Optional[float] = None
    target3: Optional[float] = None
    stopLoss: Optional[float] = None

class SyncRequest(BaseModel):
    stocks: List[StockData]

# 📡 TELEGRAM SENDER
async def send_telegram_alert(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})
            logger.info(f"📨 Sent: {message}")
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram: {e}")

# 👁️ THE SENTINEL (Background Loop - Checks every 60s)
async def monitor_market():
    logger.info("👁️ Sentinel Started Watching...")
    await send_telegram_alert("🦍 APE SENTINEL IS ONLINE. WATCHING MARKETS.")
    
    while True:
        try:
            await asyncio.sleep(60) # Check every 60 seconds
            
            if not WATCHLIST:
                continue 

            for symbol, data in list(WATCHLIST.items()):
                try:
                    ticker = yf.Ticker(symbol)
                    price = ticker.fast_info.last_price
                    
                    if price is None: continue

                    # 1. CHECK TARGET 1
                    if data['t1'] and price >= data['t1'] and 't1' not in data['alerted']:
                        await send_telegram_alert(f"🚀 {symbol} HIT TARGET 1 @ ${price:.2f}")
                        WATCHLIST[symbol]['alerted'].append('t1')

                    # 2. CHECK TARGET 2
                    if data['t2'] and price >= data['t2'] and 't2' not in data['alerted']:
                        await send_telegram_alert(f"💰 {symbol} SMASHED TARGET 2 @ ${price:.2f}")
                        WATCHLIST[symbol]['alerted'].append('t2')

                    # 3. CHECK TARGET 3
                    if data['t3'] and price >= data['t3'] and 't3' not in data['alerted']:
                        await send_telegram_alert(f"💸 {symbol} NUCLEAR TARGET 3 @ ${price:.2f}")
                        WATCHLIST[symbol]['alerted'].append('t3')
                    
                    # 4. CHECK STOP LOSS
                    if data['stop'] and price <= data['stop'] and 'stop' not in data['alerted']:
                        await send_telegram_alert(f"🩸 {symbol} STOP LOSS HIT @ ${price:.2f}")
                        WATCHLIST[symbol]['alerted'].append('stop')

                except Exception as e:
                    logger.error(f"⚠️ Error checking {symbol}: {e}")

        except Exception as e:
            logger.error(f"Sentinel Loop Error: {e}")

# 🦍 SELF-PRESERVATION
async def keep_alive():
    while True:
        try:
            await asyncio.sleep(840) # 14 mins
            async with httpx.AsyncClient() as client:
                await client.get(RENDER_URL)
                logger.info("❤️ Heartbeat")
        except:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(monitor_market())
    asyncio.create_task(keep_alive())
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Ape Sentinel Online 👁️", "watching": len(WATCHLIST)}

# 🔄 SYNC ENDPOINT (Flutter calls this)
@app.post("/sync")
def sync_watchlist(request: SyncRequest):
    global WATCHLIST
    new_watchlist = {}
    
    for stock in request.stocks:
        # Preserve history if exists
        existing_alerts = []
        if stock.symbol in WATCHLIST:
            existing_alerts = WATCHLIST[stock.symbol].get('alerted', [])
            
        new_watchlist[stock.symbol] = {
            "t1": stock.target1,
            "t2": stock.target2,
            "t3": stock.target3,
            "stop": stock.stopLoss,
            "alerted": existing_alerts
        }
    
    WATCHLIST = new_watchlist
    logger.info(f"📥 Synced {len(WATCHLIST)} stocks from App")
    return {"status": "ok", "watching": len(WATCHLIST)}

@app.get("/quote/{symbol}")
def get_quote(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.last_price
        prev_close = ticker.fast_info.previous_close
        
        change_percent = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0

        # Weinstein Logic
        hist = ticker.history(period="1y", interval="1wk")
        sma_30 = None
        stage = "UNKNOWN"
        if len(hist) >= 30:
            hist['SMA_30'] = hist['Close'].rolling(window=30).mean()
            sma_30 = hist['SMA_30'].iloc[-1]
            if sma_30 and price > sma_30: stage = "UPTREND"
            elif sma_30 and price < sma_30: stage = "DOWNTREND"

        return {
            "symbol": symbol.upper(),
            "price": price,
            "changePercent": change_percent,
            "sma30": sma_30 if sma_30 else 0.0,
            "stage": stage
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Stock not found")
