from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf

app = FastAPI()

# This allows your Flutter app to talk to this Python script
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Ape Brain Online"}

@app.get("/quote/{symbol}")
def get_quote(symbol: str):
    try:
        # Fetch the live data
        ticker = yf.Ticker(symbol)
        
        # Get the fast price data
        price = ticker.fast_info.last_price
        prev_close = ticker.fast_info.previous_close
        
        # Calculate percentage change
        change_percent = ((price - prev_close) / prev_close) * 100
        
        return {
            "symbol": symbol.upper(),
            "price": price,
            "changePercent": change_percent
        }
    except Exception as e:
        # If the stock doesn't exist
        raise HTTPException(status_code=404, detail="Stock not found")