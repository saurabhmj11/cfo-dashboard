import pytest
import pandas as pd
from app.models.schemas import AnalysisPayload, Anomaly
from app.services.agents.orchestrator import FinancialOrchestrator
from app.services.ml_anomaly import MLAnomalyDetector

def test_ml_anomaly_detector_stable():
    """Test that stable data yields no anomalies."""
    detector = MLAnomalyDetector()
    
    # Create 6 months of perfectly stable data
    data = []
    for i in range(1, 7):
        data.append({
            "month": f"2023-0{i}",
            "revenue": 10000,
            "expenses": 5000,
            "net_profit": 5000
        })
        
    df = pd.DataFrame(data)
    anomalies = detector.detect_anomalies(df)
    
    # Stable data should not produce severe outliers according to Isolation Forest
    # (Note: IF usually needs more data to train properly, but for this mock, 
    # we expect no catastrophic anomalies flagged as severe).
    assert len(anomalies) == 0

def test_ml_anomaly_detector_outlier():
    """Test that extreme data yields anomalies."""
    detector = MLAnomalyDetector(contamination=0.2) # Expect some outliers
    
    data = []
    for i in range(1, 6):
        data.append({
            "month": f"2023-0{i}",
            "revenue": 10000,
            "expenses": 5000,
            "net_profit": 5000
        })
        
    # Month 6: Catastrophic revenue drop
    data.append({
        "month": "2023-06",
        "revenue": 100,
        "expenses": 8000,
        "net_profit": -7900
    })
        
    df = pd.DataFrame(data)
    anomalies = detector.detect_anomalies(df)
    
    # Should detect the severe deviation
    assert len(anomalies) > 0
    assert anomalies[0].metric == "revenue" or anomalies[0].metric == "net_profit"
    assert anomalies[0].severity == "High"

def test_orchestrator_routing_stable_bypass():
    """Test that Orchestrator bypasses LLM if data is stable."""
    orchestrator = FinancialOrchestrator()
    
    # Stable Payload (High margin, positive growth, no anomalies)
    payload = AnalysisPayload(
        kpis={"avg_margin": 0.25, "total_revenue": 100000},
        trends={"latest_growth": 5.0},
        anomalies=[],
        confidence_score=1.0
    )
    
    assert orchestrator._needs_deep_analysis(payload) == False
    
    # Run analysis - should return fast mock
    result = orchestrator.run_analysis(payload)
    assert result["detective_report"].anomalies_detected == 0
    assert "System Analytics: All metrics are within stable" in result["detective_report"].summary

def test_orchestrator_routing_anomalous_trigger():
    """Test that Orchestrator triggers LLM if data is anomalous."""
    orchestrator = FinancialOrchestrator()
    
    # Anomalous Payload (Detected by ML)
    payload = AnalysisPayload(
        kpis={"avg_margin": 0.25, "total_revenue": 100000},
        trends={"latest_growth": 5.0},
        anomalies=[
            Anomaly(date="2023-06", metric="revenue", value=100, deviation_percent=-99, severity="High", description="Cratered")
        ],
        confidence_score=1.0
    )
    
    assert orchestrator._needs_deep_analysis(payload) == True
    
    # We do NOT call run_analysis here because it would actually hit the Gemini API.
    # We just assert the routing boolean.
