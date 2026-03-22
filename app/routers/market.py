"""
Market Data Router
Endpoints for real-time stock quotes, historical data, and market status.
"""
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import List, Optional
import asyncio
import json

from app.services.market_data_service import market_data_service

router = APIRouter(
    prefix="/api/v1/market",
    tags=["market"]
)


@router.get("/status")
async def get_market_status():
    """
    Get current market status (open/closed).
    """
    return market_data_service.get_market_status()


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """
    Get real-time stock quote.
    
    Example: GET /api/v1/market/quote/AAPL
    """
    if not market_data_service.is_available:
        raise HTTPException(
            status_code=503, 
            detail="Market data service unavailable. Install yfinance: pip install yfinance"
        )
    
    quote = await market_data_service.get_quote(symbol.upper())
    
    if not quote:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
    
    return {
        "status": "success",
        "data": quote.to_dict()
    }


@router.get("/quotes")
async def get_multiple_quotes(symbols: str = Query(..., description="Comma-separated symbols")):
    """
    Get quotes for multiple symbols.
    
    Example: GET /api/v1/market/quotes?symbols=AAPL,GOOGL,MSFT
    """
    if not market_data_service.is_available:
        raise HTTPException(status_code=503, detail="Market data service unavailable")
    
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    if len(symbol_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 symbols per request")
    
    quotes = await market_data_service.get_multiple_quotes(symbol_list)
    
    return {
        "status": "success",
        "count": len(quotes),
        "data": {k: v.to_dict() for k, v in quotes.items()}
    }


@router.get("/history/{symbol}")
async def get_historical_data(
    symbol: str,
    period: str = Query("1mo", description="1d, 5d, 1mo, 3mo, 6mo, 1y, 5y, max"),
    interval: str = Query("1d", description="1m, 5m, 15m, 1h, 1d, 1wk, 1mo")
):
    """
    Get historical OHLCV data for a symbol.
    
    Example: GET /api/v1/market/history/AAPL?period=3mo&interval=1d
    """
    if not market_data_service.is_available:
        raise HTTPException(status_code=503, detail="Market data service unavailable")
    
    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    valid_intervals = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
    
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail=f"Invalid period. Valid: {valid_periods}")
    
    if interval not in valid_intervals:
        raise HTTPException(status_code=400, detail=f"Invalid interval. Valid: {valid_intervals}")
    
    history = await market_data_service.get_historical(symbol.upper(), period, interval)
    
    if not history:
        raise HTTPException(status_code=404, detail=f"No historical data for '{symbol}'")
    
    return {
        "status": "success",
        "symbol": symbol.upper(),
        "period": period,
        "interval": interval,
        "count": len(history),
        "data": [h.to_dict() for h in history]
    }


@router.get("/search")
async def search_symbols(q: str = Query(..., min_length=1, description="Search query")):
    """
    Search for stock symbols.
    
    Example: GET /api/v1/market/search?q=Apple
    """
    if not market_data_service.is_available:
        raise HTTPException(status_code=503, detail="Market data service unavailable")
    
    results = await market_data_service.search_symbols(q)
    
    return {
        "status": "success",
        "query": q,
        "results": results
    }


# WebSocket for real-time streaming
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time price streaming.
    
    Send: {"symbols": ["AAPL", "GOOGL"]}
    Receive: {"AAPL": {...quote...}, "GOOGL": {...quote...}}
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Wait for client to send symbols to track
            data = await websocket.receive_json()
            symbols = data.get("symbols", [])
            
            if not symbols:
                await websocket.send_json({"error": "No symbols provided"})
                continue
            
            # Stream quotes every 5 seconds
            while True:
                try:
                    quotes = await market_data_service.get_multiple_quotes(symbols[:10])
                    await websocket.send_json({
                        "type": "quotes",
                        "data": {k: v.to_dict() for k, v in quotes.items()},
                        "timestamp": market_data_service.get_market_status()["current_time_utc"]
                    })
                    await asyncio.sleep(5)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    await websocket.send_json({"error": str(e)})
                    await asyncio.sleep(5)
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
