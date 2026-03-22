"""
Market Data Service
Real-time and historical market data integration via yfinance.
Supports quotes, historical OHLCV, and streaming price updates.
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

# yfinance for Yahoo Finance data (no API key required)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[MARKET WARNING] yfinance not installed. Run: pip install yfinance")


@dataclass
class StockQuote:
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    day_high: float
    day_low: float
    open_price: float
    previous_close: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change": self.change,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "market_cap": self.market_cap,
            "pe_ratio": self.pe_ratio,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "open": self.open_price,
            "previous_close": self.previous_close,
            "timestamp": self.timestamp
        }


@dataclass
class OHLCV:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


class MarketDataService:
    """
    Real-time and historical market data service.
    Uses yfinance (Yahoo Finance) - no API key required.
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 60  # Cache for 60 seconds
    
    @property
    def is_available(self) -> bool:
        return YFINANCE_AVAILABLE
    
    def _is_cache_valid(self, symbol: str) -> bool:
        if symbol not in self._cache:
            return False
        cached = self._cache[symbol]
        return (datetime.now() - cached["timestamp"]).seconds < self._cache_ttl
    
    async def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """
        Get real-time stock quote using yf.download (more reliable).
        """
        if not self.is_available:
            return None
        
        # Check cache first
        if self._is_cache_valid(symbol):
            return self._cache[symbol]["quote"]
        
        try:
            loop = asyncio.get_event_loop()
            
            # Use download - more reliable than Ticker
            hist = await loop.run_in_executor(
                None, 
                lambda: yf.download(symbol, period="5d", interval="1d", progress=False)
            )
            
            if hist.empty:
                return None
            
            latest = hist.iloc[-1]
            prev_close = float(hist.iloc[-2]["Close"]) if len(hist) > 1 else float(latest["Open"])
            
            price = float(latest["Close"])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0
            
            quote = StockQuote(
                symbol=symbol.upper(),
                price=round(price, 2),
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                volume=int(latest["Volume"]),
                market_cap=None,
                pe_ratio=None,
                day_high=round(float(latest["High"]), 2),
                day_low=round(float(latest["Low"]), 2),
                open_price=round(float(latest["Open"]), 2),
                previous_close=round(prev_close, 2),
                timestamp=datetime.now().isoformat()
            )
            
            self._cache[symbol] = {"quote": quote, "timestamp": datetime.now()}
            return quote
            
        except Exception as e:
            print(f"[MARKET ERROR] Failed to fetch quote for {symbol}: {e}")
            return None
    
    async def get_historical(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> List[OHLCV]:
        """
        Get historical OHLCV data using yf.download.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            period: Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        """
        if not self.is_available:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            hist = await loop.run_in_executor(
                None, 
                lambda: yf.download(symbol, period=period, interval=interval, progress=False)
            )
            
            if hist.empty:
                return []
            
            result = []
            for date, row in hist.iterrows():
                result.append(OHLCV(
                    date=date.strftime("%Y-%m-%d"),
                    open=round(float(row["Open"]), 2),
                    high=round(float(row["High"]), 2),
                    low=round(float(row["Low"]), 2),
                    close=round(float(row["Close"]), 2),
                    volume=int(row["Volume"])
                ))
            
            return result
            
        except Exception as e:
            print(f"[MARKET ERROR] Failed to fetch history for {symbol}: {e}")
            return []
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, StockQuote]:
        """
        Get quotes for multiple symbols concurrently.
        """
        tasks = [self.get_quote(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return {
            symbols[i]: r 
            for i, r in enumerate(results) 
            if r is not None
        }
    
    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """
        Search for stock symbols by company name.
        """
        if not self.is_available:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, lambda: yf.Ticker(query))
            info = await loop.run_in_executor(None, lambda: ticker.info)
            
            if info and "symbol" in info:
                return [{
                    "symbol": info.get("symbol", query.upper()),
                    "name": info.get("shortName", ""),
                    "exchange": info.get("exchange", ""),
                    "type": info.get("quoteType", "EQUITY")
                }]
            return []
            
        except Exception:
            return []
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        Check if US market is currently open.
        """
        now = datetime.utcnow()
        # NYSE hours: 9:30 AM - 4:00 PM ET (14:30 - 21:00 UTC)
        market_open = now.replace(hour=14, minute=30, second=0)
        market_close = now.replace(hour=21, minute=0, second=0)
        
        is_weekday = now.weekday() < 5
        is_market_hours = market_open <= now <= market_close
        
        return {
            "is_open": is_weekday and is_market_hours,
            "current_time_utc": now.isoformat(),
            "next_open": market_open.isoformat() if not is_market_hours else None,
            "next_close": market_close.isoformat() if is_market_hours else None
        }


# Singleton instance
market_data_service = MarketDataService()
