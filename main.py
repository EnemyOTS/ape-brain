from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import yfinance as yf
import httpx
import asyncio
import logging

# Set up logging to track the heartbeat
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ApeBrain")

# 🦍 THE SELF-PRESERVATION PROTOCOL
# This function runs in the background to keep Render awake
async def keep_alive():
    url = "https://ape-brain.onrender.com"  # <--- ⚠️ REPLACE WITH YOUR EXACT RENDER URL
    while True:
        try:
            await asyncio.sleep(840)  # Sleep for 14 minutes (Render sleeps at 15)
            async with httpx.AsyncClient() as client:
                # Ping the home endpoint
                response = await client.get(url)
                logger.info(f"❤️ Heartbeat Sent: {response.status_code}")
        except Exception as e:
            logger.error(f"💔 Heartbeat Failed: {e}")

# Lifespan manager to handle startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch the heartbeat
    logger.info("🦍 Ape Brain Waking Up...")
    asyncio.create_task(keep_alive())
    yield
    # Shutdown logic (if any)
    logger.info("🦍 Ape Brain Sleeping...")

app = FastAPI(lifespan=lifespan)

# CORS Config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Ape Brain Online 🦍"}

@app.get("/quote/{symbol}")
def get_quote(symbol: str):
    try:
        # Fetch the live data
        ticker = yf.Ticker(symbol)
        
        # Get the fast price data
        price = ticker.fast_info.last_price
        prev_close = ticker.fast_info.previous_close
        
        # Calculate percentage change
        if prev_close and prev_close != 0:
            change_percent = ((price - prev_close) / prev_close) * 100
        else:
            change_percent = 0.0
        
        return {
            "symbol": symbol.upper(),
            "price": price,
            "changePercent": change_percent
        }
    except Exception as e:
        # If the stock doesn't exist or YF fails
        logger.error(f"Error fetching {symbol}: {e}")
        raise HTTPException(status_code=404, detail="Stock not found")
