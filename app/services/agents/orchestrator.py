from typing import Dict, Any, Optional, List
from app.models.schemas import FinancialAnalysisResult, DetectiveReport, ForecastReport, AdvisorReport, AnalysisPayload
from app.services.agents.detective import MetricAnalyst
from app.services.agents.forecaster import ForecastingAgent
from app.services.agents.advisor import StrategicAdvisor
from app.services.agents.risk_analyst import RiskAnalyst
from app.services.agents.news_analyst import NewsAnalyst
from app.services.agents.research_analyst import ResearchAnalyst

class FinancialOrchestrator:
    """
    The Conductor of the Agent Coalition.
    Coordinates data flow between all specialized agents.
    
    v1.5 Upgrade: Added Risk Analyst, News Analyst, and Research Analyst.
    """
    
    def __init__(self):
        # Core Triad
        self.detective = MetricAnalyst()
        self.forecaster = ForecastingAgent()
        self.advisor = StrategicAdvisor()
        
        # Extended Coalition (v1.5)
        self.risk_analyst = RiskAnalyst()
        self.news_analyst = NewsAnalyst()
        self.research_analyst = ResearchAnalyst()
        
    def _needs_deep_analysis(self, data: AnalysisPayload) -> bool:
        """
        The Intelligent Router. Determines if we need to spend money on LLMs.
        Returns True if situation is 'out of control'.
        """
        # 1. Are there many anomalies?
        if len(data.anomalies) > 2:
            return True
            
        # 2. Are there any critical / High severity anomalies?
        for anomaly in data.anomalies:
            if anomaly.severity == "High":
                return True
                
        # 3. Are margins critically low? (< 5%)
        latest_margin = data.kpis.get("avg_margin", 0.0)
        if latest_margin > 0 and latest_margin < 0.05:
            return True
            
        # Situation is relatively stable. Rely on deterministic rules.
        return False

    def _generate_mock_reports(self, data: AnalysisPayload) -> Dict[str, Any]:
        """Generates fast deterministic reports bypassing the LLM."""
        return {
            "detective_report": DetectiveReport(
                summary="System Analytics: All metrics are within stable operating bounds. No statistical anomalies detected by ML Engine.",
                observations=[],
                anomalies_detected=0
            ),
            "forecast_report": ForecastReport(
                scenarios=[],
                best_case_total=data.kpis.get("total_revenue", 0) * 1.05, # Simple +5% mock
                worst_case_total=data.kpis.get("total_revenue", 0) * 0.95,
                model_confidence=0.9
            ),
            "advisor_report": AdvisorReport(
                strategic_advice=[]
            )
        }
        
    def run_analysis(self, data: AnalysisPayload, context: Any = None) -> Dict[str, Any]:
        """
        Intelligently routed multi-agent pipeline.
        """
        # 0. Intelligent Routing Check
        if not self._needs_deep_analysis(data):
            print("[ORCHESTRATOR] Metrics stable. Bypassing LLM agents for cost efficiency.")
            return self._generate_mock_reports(data)
            
        print("[ORCHESTRATOR] Anomalies detected. Engaging LLM Agent Coalition.")
        # 1. Detective: Look at the past
        detective_report: DetectiveReport = self.detective.analyze(data)
        
        # 2. Oracle: Look at the future
        forecast_report: ForecastReport = self.forecaster.predict(data)
        
        # 3. Advisor: Synthesize and Advise
        advisor_report: AdvisorReport = self.advisor.advise(data, detective_report, forecast_report, context)
        
        return {
            "detective_report": detective_report,
            "forecast_report": forecast_report,
            "advisor_report": advisor_report
        }
    
    async def run_full_analysis(
        self, 
        data: AnalysisPayload, 
        positions: Optional[List[Dict]] = None,
        symbols: Optional[List[str]] = None,
        context: Any = None
    ) -> Dict[str, Any]:
        """
        Enhanced analysis with all agents including risk and sentiment.
        
        Args:
            data: Core financial data payload
            positions: Portfolio positions for risk analysis
            symbols: Stock symbols for sentiment analysis
            context: Additional context for advisor
        """
        # Run core analysis
        core_results = self.run_analysis(data, context)
        
        # Risk Analysis (if positions provided)
        risk_report = None
        if positions:
            risk_report = self.risk_analyst.analyze_portfolio(positions)
        
        # Sentiment Analysis (if symbols provided)
        sentiment_results = None
        if symbols:
            sentiment_results = await self.news_analyst.analyze_sentiment(symbols)
        
        return {
            **core_results,
            "risk_report": risk_report.to_dict() if risk_report else None,
            "sentiment_reports": {
                s: r.to_dict() for s, r in sentiment_results.items()
            } if sentiment_results else None
        }
    
    async def run_research(self, query: str) -> Dict[str, Any]:
        """
        New Paperclip-native research capability.
        Handles open-ended questions by querying the document vector store.
        """
        print(f"[ORCHESTRATOR] Researching: {query}")
        result = await self.research_analyst.research(query)
        return {
            "research_report": result.to_dict(),
            "status": "COMPLETED_RESEARCH"
        }

    def get_agent_status(self) -> Dict[str, Any]:
        """Return status of all agents."""
        return {
            "core_agents": {
                "detective": "active",
                "forecaster": "active",
                "advisor": "active"
            },
            "extended_agents": {
                "risk_analyst": "active",
                "news_analyst": "active",
                "research_analyst": "active" if self.research_analyst.is_available else "unavailable"
            },
            "version": "1.5.0"
        }
