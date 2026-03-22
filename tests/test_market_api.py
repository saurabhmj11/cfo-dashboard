"""
Test script to verify market API functionality.
Run: python tests/test_market_api.py
"""
import asyncio
import sys
sys.path.insert(0, ".")

async def test_market_service():
    from app.services.market_data_service import market_data_service
    
    print("=" * 60)
    print("Testing Market Data Service")
    print("=" * 60)
    
    # Test 1: Service availability
    print(f"\n[1] yfinance available: {market_data_service.is_available}")
    
    if not market_data_service.is_available:
        print("FAILED: yfinance not installed")
        return False
    
    # Test 2: Get quote
    print("\n[2] Testing get_quote('AAPL')...")
    quote = await market_data_service.get_quote("AAPL")
    if quote:
        print(f"   Symbol: {quote.symbol}")
        print(f"   Price: ${quote.price:.2f}")
        print(f"   Change: {quote.change_percent:.2f}%")
        print(f"   Volume: {quote.volume:,}")
        print("   ✓ PASSED")
    else:
        print("   FAILED: Could not get quote")
        return False
    
    # Test 3: Get historical data
    print("\n[3] Testing get_historical('AAPL', '5d')...")
    history = await market_data_service.get_historical("AAPL", "5d", "1d")
    if history:
        print(f"   Got {len(history)} records")
        print(f"   Latest: {history[-1].date} - Close: ${history[-1].close:.2f}")
        print("   ✓ PASSED")
    else:
        print("   FAILED: Could not get history")
        return False
    
    # Test 4: Multiple quotes
    print("\n[4] Testing get_multiple_quotes(['AAPL', 'GOOGL', 'MSFT'])...")
    quotes = await market_data_service.get_multiple_quotes(["AAPL", "GOOGL", "MSFT"])
    print(f"   Got quotes for: {list(quotes.keys())}")
    for symbol, q in quotes.items():
        print(f"   {symbol}: ${q.price:.2f}")
    print("   ✓ PASSED")
    
    # Test 5: Market status
    print("\n[5] Testing get_market_status()...")
    status = market_data_service.get_market_status()
    print(f"   Market Open: {status['is_open']}")
    print(f"   Current UTC: {status['current_time_utc']}")
    print("   ✓ PASSED")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_market_service())
    sys.exit(0 if success else 1)
