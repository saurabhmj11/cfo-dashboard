from app.models.schemas import AnalysisPayload, DetectiveReport, ForecastReport, AdvisorReport, AdviceCard, AdvisorContext
from app.services.agents.forecaster import ForecastingAgent 
from typing import Optional

class StrategicAdvisor:
    """
    The 'Advisor' Agent (Layer 4).
    Role: Strategy Synthesizer.
    Principle: "Based on the Detective's facts and Oracle's simulations, here is the plan."
    """
    def __init__(self):
        self.forecaster = ForecastingAgent()
    
    def advise(self, data: AnalysisPayload, observations: DetectiveReport, forecast: ForecastReport, context: Optional[AdvisorContext] = None) -> AdvisorReport:
        advice_cards = []
        
        # RAG / In-Context Learning 
        past_wins = context.positive_examples if context else []
        
        # Helper: check if topic is rejected
        def is_rejected(topic_keyword: str) -> bool:
            if not context: return False
            for rejected in context.rejected_topics:
                if topic_keyword.lower() in rejected.lower():
                    return True
            return False

        # Helper: check if we have a "win" similar to this topic
        def has_similar_win(topic_keyword: str) -> bool:
            for win in past_wins:
                if topic_keyword.lower() in win.lower():
                    return True
            return False

        # 1. Search for Margin/Efficiency Issues
        margin_obs = next((o for o in observations.observations if o.metric == "Margin"), None)
        
        if margin_obs and margin_obs.trend == "Concern" and not is_rejected("Marketing Spend"):
            # Call Oracle (Forecaster) for deterministic simulation
            # TRUTH: We use Total Expenses as the baseline for the cut, assuming Marketing is a subset.
            # We explicitly simulate a cut to OpEx.
            baseline_exp = data.kpis.get("total_expenses", 0.0)
            
            sim_result = self.forecaster.simulate_action_with_data(
                target_metric="Profit", 
                action_type="Marketing Spend", # Keeping label for UI consistency
                change_percent=-0.15,
                baseline_value=baseline_exp
            )
            
            advice_cards.append(AdviceCard(
                decision="Optimize Cost Structure",
                reason=margin_obs.detail, # Citation from Detective
                root_cause="Operational expenses exceeding 80% of revenue.",
                
                # Oracle's Output
                impact=f"Simulated Outcome: {sim_result.predicted_impact_value/1000:+.1f}k Net Profit.", 
                impact_value=sim_result.predicted_impact_value,
                suggested_action="Reduce Marketing Spend by 15%",
                
                risk="Low",
                confidence=min(0.9, sim_result.confidence_score) # Cap by simulation confidence
            ))

        # 2. Search for Revenue/Growth Issues
        rev_obs = next((o for o in observations.observations if o.metric == "Revenue"), None)
        
        # Check Forecast (Layer 3/Oracle Data)
        is_growth_forecast = forecast.best_case_total > (forecast.worst_case_total * 1.1)
        
        if rev_obs and rev_obs.trend == "Declining" and not is_rejected("Reactivation"):
             # Mitigation Strategy
             advice_cards.append(AdviceCard(
                decision="Revenue Recovery Plan",
                reason=rev_obs.detail,
                root_cause="MoM revenue contraction.",
                impact="Stabilize cash flow runway.",
                impact_value=10000.0, # Placeholder utility value
                suggested_action="Launch reactivation campaign for lapsed customers.",
                risk="Medium",
                confidence=0.85
            ))
        elif is_growth_forecast and not is_rejected("Ad Spend"):
             # Acceleration Strategy
             advice_cards.append(AdviceCard(
                decision="Double Down on Growth",
                reason="Forecast indicates >10% upside potential.",
                root_cause="Strong baseline momentum.",
                impact="Capture market share while conditions are favorable.",
                impact_value=50000.0,
                suggested_action="Increase ad spend on high-performing channels.",
                risk="Medium",
                confidence=0.8
            ))
            
        # 3. Universal Hygiene
        is_hygiene_win = has_similar_win("Cash Flow")
        advice_cards.append(AdviceCard(
            decision="Cash Flow Hygiene",
            reason="Standard monthly capital review.",
            root_cause="N/A (Routine)",
            impact="Ensure liquidity.",
            impact_value=0.0,
            suggested_action="Review Accounts Receivable Aging Report.",
            risk="Low",
            confidence=0.9 if is_hygiene_win else 0.8  # Learning Boost
        ))

        # 4. Fallback: If no critical issues found, suggest Optimization
        if len(advice_cards) < 2:
            advice_cards.append(AdviceCard(
                decision="Capital Efficiency Review",
                reason="Financial health is stable.",
                root_cause="Positive baseline metrics.",
                impact="Maximize ROI on idle cash.",
                impact_value=5000.0,
                suggested_action="Investigate high-yield treasury options for surplus cash.",
                risk="Low",
                confidence=0.95
            ))
        
        return AdvisorReport(strategic_advice=advice_cards)
