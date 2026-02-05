from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import yfinance as yf
import httpx
import asyncio
import logging
import pandas as pd # Needed for calculations

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ApeBrain")

# 🦍 SELF-PRESERVATION PROTOCOL
async def keep_alive():
    url = "https://ape-brain.onrender.com"  # <--- CONFIRM THIS IS YOUR URL
    while True:
        try:
            await asyncio.sleep(840)  # 14 minutes
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                logger.info(f"❤️ Heartbeat Sent: {response.status_code}")
        except Exception as e:
            logger.error(f"💔 Heartbeat Failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🦍 Ape Brain Waking Up...")
    asyncio.create_task(keep_alive())
    yield
    logger.info("🦍 Ape Brain Sleeping...")

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
    return {"message": "Ape Brain Online & Thinking 🧠"}

@app.get("/quote/{symbol}")
def get_quote(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        
        # 1. Get Live Data
        price = ticker.fast_info.last_price
        prev_close = ticker.fast_info.previous_close
        
        if prev_close and prev_close != 0:
            change_percent = ((price - prev_close) / prev_close) * 100
        else:
            change_percent = 0.0

        # 2. THE WEINSTEIN CALCULATION (SMA 30)
        # Fetch 1 year of weekly data to calculate 30-week MA
        hist = ticker.history(period="1y", interval="1wk")
        
        sma_30 = None
        stage = "UNKNOWN"
        
        if len(hist) >= 30:
            # Calculate the 30-week Simple Moving Average
            hist['SMA_30'] = hist['Close'].rolling(window=30).mean()
            sma_30 = hist['SMA_30'].iloc[-1] # Get the latest value
            
            # Determine Basic Stage
            if sma_30 and price > sma_30:
                stage = "UPTREND" # Potential Stage 2
            elif sma_30 and price < sma_30:
                stage = "DOWNTREND" # Potential Stage 4

        return {
            "symbol": symbol.upper(),
            "price": price,
            "changePercent": change_percent,
            "sma30": sma_30, # Sending the calculated MA to Flutter
            "stage": stage   # Sending the verdict
        }

    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        raise HTTPException(status_code=404, detail="Stock not found")
