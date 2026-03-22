import pytest
from datetime import date, timedelta
from app.models.db_models import Transaction
from app.services.analytics import AnalyticsEngine

@pytest.fixture
def analytics_engine():
    return AnalyticsEngine()

def create_transactions(start_date: date, count: int, daily_amount: float = 1000.0) -> list[Transaction]:
    """Helper to generate dense transactions"""
    txns = []
    for i in range(count):
        txns.append(Transaction(
            txn_date=start_date + timedelta(days=i),
            revenue=daily_amount,
            expenses=daily_amount * 0.8,
            category="Sales"
        ))
    return txns

def test_perfect_confidence(analytics_engine):
    """Test that full dense data yields 1.0 confidence"""
    # Create 30 days of data
    start = date(2024, 1, 1)
    txns = create_transactions(start, 31)
    
    result = analytics_engine.compute_metrics(txns)
    payload = result["payload"]
    
    print(f"\nPerfect Score Issues: {payload.data_quality_issues}")
    assert payload.confidence_score == 1.0
    assert len(payload.data_quality_issues) == 0

def test_low_density_penalty(analytics_engine):
    """Test that sparse data (few txns per month) lowers confidence"""
    # Create only 2 txns in a month
    txns = [
        Transaction(txn_date=date(2024, 2, 1), revenue=1000, expenses=500, category="A"),
        Transaction(txn_date=date(2024, 2, 28), revenue=1000, expenses=500, category="B")
    ]
    
    result = analytics_engine.compute_metrics(txns)
    payload = result["payload"]
    
    print(f"\nLow Density Issues: {payload.data_quality_issues}")
    # Should penalize for low density (<5 txns/month)
    # And potentially gap detection depending on logic
    assert payload.confidence_score < 1.0
    assert any("Low data density" in issue for issue in payload.data_quality_issues)

def test_data_gaps(analytics_engine):
    """Test that missing months lower confidence"""
    # Data in Jan and March, but missing Feb
    txns = create_transactions(date(2024, 1, 1), 31) + create_transactions(date(2024, 3, 1), 31)
    
    result = analytics_engine.compute_metrics(txns)
    payload = result["payload"]
    
    print(f"\nGap Issues: {payload.data_quality_issues}")
    # Should detect gap
    assert payload.confidence_score < 1.0
    assert any("Data gaps detected" in issue for issue in payload.data_quality_issues)

def test_volatility_penalty(analytics_engine):
    """Test extreme volatility penalty"""
    # Month 1: Normal
    start = date(2024, 1, 1)
    txns = create_transactions(start, 31, daily_amount=100.0) # ~3100 total
    
    # Month 2: Massive spike (300% growth)
    spike_txns = create_transactions(date(2024, 2, 1), 29, daily_amount=10000.0) # ~290,000 total
    
    all_txns = txns + spike_txns
    
    result = analytics_engine.compute_metrics(all_txns)
    payload = result["payload"]
    
    print(f"\nVolatility Issues: {payload.data_quality_issues}")
    assert payload.confidence_score < 1.0
    assert any("Extreme volatility" in issue for issue in payload.data_quality_issues)
