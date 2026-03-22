from mcp.server.fastmcp import FastMCP
from app.services.agents.orchestrator import FinancialOrchestrator
from app.models.schemas import FinancialAnalysisResult, MonthlyMetric
from app.database import engine, Base
import json

# Initialize Database
Base.metadata.create_all(bind=engine)

# Create MCP Server
mcp = FastMCP("Financial Analyst")

# Initialize Agents
orchestrator = FinancialOrchestrator()

@mcp.tool()
def analyze_financial_data(data: str) -> str:
    """
    Runs the full Financial Analyst Triad (Detective, Oracle, Advisor) on the provided data.
    Args:
        data: JSON string conforming to FinancialAnalysisResult schema.
    Returns:
        JSON string with the full analysis report.
    """
    try:
        # Parse input
        data_dict = json.loads(data)
        financial_data = FinancialAnalysisResult(**data_dict)
        
        # Run Analysis
        results = orchestrator.run_analysis(financial_data)
        
        # Convert Pydantic models to dict for JSON serialization
        return json.dumps({
            "detective": results["detective_report"].model_dump(),
            "forecast": results["forecast_report"].model_dump(),
            "advisor": results["advisor_report"].model_dump()
        }, default=str)
    except Exception as e:
        return f"Error running analysis: {str(e)}"

@mcp.tool()
def get_metrics_analysis(data: str) -> str:
    """
    Runs the Detective Agent to identify trends and anomalies.
    """
    try:
        data_dict = json.loads(data)
        financial_data = FinancialAnalysisResult(**data_dict)
        report = orchestrator.detective.analyze(financial_data)
        return report.model_dump_json()
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_forecast(data: str) -> str:
    """
    Runs the Oracle Agent to generate 3 scenarios (Conservative, Neutral, Aggressive).
    """
    try:
        data_dict = json.loads(data)
        financial_data = FinancialAnalysisResult(**data_dict)
        report = orchestrator.forecaster.predict(financial_data)
        return report.model_dump_json()
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
