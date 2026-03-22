"""
Test script to verify v1.5 components are properly integrated.
Run: python tests/test_v1_5_components.py
"""
import sys
sys.path.insert(0, ".")


def test_imports():
    """Test that all new components can be imported."""
    print("=" * 60)
    print("Testing v1.5 Component Imports")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # Test Market Data Service
    try:
        from app.services.market_data_service import market_data_service
        print(f"✓ market_data_service - available: {market_data_service.is_available}")
        passed += 1
    except Exception as e:
        print(f"✗ market_data_service - {e}")
        failed += 1
    
    # Test Vector Service
    try:
        from app.services.vector_service import vector_service
        print(f"✓ vector_service - available: {vector_service.is_available}")
        passed += 1
    except Exception as e:
        print(f"✗ vector_service - {e}")
        failed += 1
    
    # Test Search Router
    try:
        from app.routers.search import router
        print(f"✓ search router - prefix: {router.prefix}")
        passed += 1
    except Exception as e:
        print(f"✗ search router - {e}")
        failed += 1
    
    # Test Market Router
    try:
        from app.routers.market import router
        print(f"✓ market router - prefix: {router.prefix}")
        passed += 1
    except Exception as e:
        print(f"✗ market router - {e}")
        failed += 1
    
    # Test Risk Analyst
    try:
        from app.services.agents.risk_analyst import risk_analyst
        print(f"✓ risk_analyst - capabilities: {risk_analyst.capabilities}")
        passed += 1
    except Exception as e:
        print(f"✗ risk_analyst - {e}")
        failed += 1
    
    # Test News Analyst
    try:
        from app.services.agents.news_analyst import news_analyst
        print(f"✓ news_analyst - capabilities: {news_analyst.capabilities}")
        passed += 1
    except Exception as e:
        print(f"✗ news_analyst - {e}")
        failed += 1
    
    # Test Research Analyst
    try:
        from app.services.agents.research_analyst import research_analyst
        print(f"✓ research_analyst - available: {research_analyst.is_available}")
        passed += 1
    except Exception as e:
        print(f"✗ research_analyst - {e}")
        failed += 1
    
    # Test Orchestrator
    try:
        from app.services.agents.orchestrator import FinancialOrchestrator
        orchestrator = FinancialOrchestrator()
        status = orchestrator.get_agent_status()
        print(f"✓ orchestrator - version: {status['version']}")
        passed += 1
    except Exception as e:
        print(f"✗ orchestrator - {e}")
        failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


def test_risk_analyst():
    """Test risk analyst with sample data."""
    print("\n" + "=" * 60)
    print("Testing Risk Analyst")
    print("=" * 60)
    
    from app.services.agents.risk_analyst import risk_analyst
    
    # Sample portfolio
    positions = [
        {"symbol": "AAPL", "value": 50000, "expected_return": 0.12, "volatility": 0.25},
        {"symbol": "GOOGL", "value": 30000, "expected_return": 0.10, "volatility": 0.22},
        {"symbol": "MSFT", "value": 20000, "expected_return": 0.11, "volatility": 0.20},
    ]
    
    report = risk_analyst.analyze_portfolio(positions)
    print(f"Portfolio Total: $100,000")
    print(f"Risk Score: {report.overall_score}/100 ({report.risk_level})")
    print(f"VaR (95%): ${report.metrics.var_95:,.0f}")
    print(f"Sharpe Ratio: {report.metrics.sharpe_ratio}")
    print(f"Concentration: {report.metrics.concentration_risk}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Recommendations: {len(report.recommendations)}")
    
    return True


if __name__ == "__main__":
    success = test_imports()
    
    if success:
        test_risk_analyst()
    
    sys.exit(0 if success else 1)
