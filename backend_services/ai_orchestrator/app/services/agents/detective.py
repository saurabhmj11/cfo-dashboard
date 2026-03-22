from app.models.schemas import AnalysisPayload, DetectiveReport, Observation
from app.services.llm_client import llm_client
import json

class MetricAnalyst:
    """
    The 'Detective' Agent (Layer 4).
    Role: Narrative Explainer of Layer 3 Math.
    Principle: "The Math is Truth. I explain the Meaning."
    
    Input: AnalysisPayload (Strict Truth)
    Output: DetectiveReport (Narrative Observations)
    """
    
    def analyze(self, data: AnalysisPayload) -> DetectiveReport:
        """
        Synthesizes trusted metrics into a narrative.
        """
        observations: List[Observation] = []
        
        # 1. Interpret Revenue Growth
        observations.append(self._narrate_revenue(data))
        
        # 2. Interpret Margins
        observations.append(self._narrate_margin(data.kpis.get("avg_margin", 0.0), data.confidence_score))
            
        # 3. Contextualize Anomalies
        for anomaly in data.anomalies:
            observations.append(Observation(
                metric=anomaly.metric.title(),
                trend="Anomaly",
                confidence=0.95 if anomaly.severity == "High" else 0.80,
                detail=f"Statistical Alert ({anomaly.severity}): {anomaly.metric} deviated by {anomaly.deviation_percent:.1f}% on {anomaly.date}. {anomaly.description}"
            ))
            
        # 4. Burn Rate / OpEx Context
        total_exp = data.kpis.get("total_expenses", 0.0)
        total_rev = data.kpis.get("total_revenue", 0.0)
        
        if total_exp > 0:
             ratio = total_exp / total_rev if total_rev else 1.0
             if ratio > 0.85:
                 observations.append(Observation(
                     metric="Efficiency",
                     trend="High Risk",
                     confidence=0.9,
                     detail="Operational efficiency warning. For every $1.00 earned, $0.85 is spent. This leaves little room for capital reinvestment."
                 ))

        
        # 5. Generative Summary (The "Intelligence" Upgrade)
        fallback_summary = f"Analysis detailed {len(data.trends.get('revenue_growth_mom', []))} historical periods. {len(data.anomalies)} statistical anomalies flagged for review."
        
        narrative_summary = fallback_summary
        
        if llm_client.is_available:
            system_prompt = "You are a seasoned CFO. Summarize these financial results for the CEO. Be concise, professional, and highlight the most critical risk or opportunity."
            
            # Create a localized context for the LLM
            context_str = json.dumps({
                "kpis": data.kpis,
                "anomalies": [a.model_dump() for a in data.anomalies],
                "latest_trend": observations[0].detail if observations else "No specific trend detected."
            }, indent=2)
            
            gen_summary = llm_client.generate_text(system_prompt, f"Data: {context_str}")
            if gen_summary:
                narrative_summary = gen_summary

        return DetectiveReport(
            summary=narrative_summary,
            observations=observations,
            anomalies_detected=len(data.anomalies)
        )

    def _narrate_revenue(self, data: AnalysisPayload) -> Observation:
        growth_rates = data.trends.get("revenue_growth_mom", [])
        if not growth_rates:
             return Observation(metric="Revenue", trend="Unknown", confidence=0.0, detail="Insufficient data.")

        latest_growth = data.trends.get("latest_growth", 0.0)
        
        trend = "Growing" if latest_growth > 1.0 else "Declining" if latest_growth < -1.0 else "Stable"
        
        narrative = f"Revenue is {trend.lower()} (MoM change: {latest_growth:+.1f}%)."
        if trend == "Growing":
            narrative += " Positive momentum detected in latest period."
        elif trend == "Declining":
            narrative += " Recent contraction requires immediate pipeline analysis."
            
        # Trusted Math, but capped by Data Confidence
        base_confidence = 1.0
        final_confidence = min(base_confidence, data.confidence_score)
            
        return Observation(
            metric="Revenue",
            trend=trend,
            confidence=final_confidence,
            detail=narrative
        )

    def _narrate_margin(self, margin: float, data_confidence: float) -> Observation:
        # Industry standard comparison logic
        trend = "Healthy" if margin > 0.20 else "Concern"
        narrative = f"Net Profit Margin is {margin*100:.1f}%."
        
        if trend == "Healthy":
             narrative += " This is above the robust 20% benchmark."
        else:
             narrative += " This is below the 20% healthy benchmark, indicating potential pricing or cost control issues."
             
        # Trusted Math, but capped by Data Confidence
        base_confidence = 1.0
        final_confidence = min(base_confidence, data_confidence)
             
        return Observation(
            metric="Margin",
            trend=trend,
            confidence=final_confidence,
            detail=narrative
        )
