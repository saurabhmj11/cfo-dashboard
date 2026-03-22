from app.services.llm_client import llm_client
from app.services.report_generator import report_generator
from app.models.db_models import AnalysisRun
from datetime import datetime
import json
import os

def test_llm_client():
    print("Testing LLM Client...")
    if llm_client.is_available:
        print("   ✅ Ollama Connected.")
        response = llm_client.generate_text("Test", "Say 'Hello'")
        print(f"   Response: {response}")
        assert response is not None
    else:
        print("   ⚠️ Ollama Offline (Fallback Mode Active). Passing test as this is expected behavior if no local LLM.")

def test_pdf_generation():
    print("\nTesting PDF Report Generation...")
    
    # Mock Analysis Run
    mock_run = AnalysisRun(
        id=999,
        run_date=datetime.now(),
        metrics_result={
            "financials": {"summary_revenue": 1000},
            "detective": {"summary": "Test Summary of Financials", "observations": [{"metric": "Revenue", "trend": "Growing", "detail": "Up 10%"}]}
        },
        advisor_result={
            "strategic_advice": [{"decision": "Buy", "impact": "High ROI"}]
        }
    )
    
    # Generate
    pdf_buffer = report_generator.generate_pdf(mock_run)
    pdf_size = len(pdf_buffer.getvalue())
    
    print(f"   Generated PDF Size: {pdf_size} bytes")
    assert pdf_size > 1000, "PDF seems too small"
    
    with open("test_report.pdf", "wb") as f:
        f.write(pdf_buffer.getvalue())
    print("   ✅ PDF saved to test_report.pdf")

if __name__ == "__main__":
    test_llm_client()
    test_pdf_generation()
    if os.path.exists("test_report.pdf"):
        os.remove("test_report.pdf")
