from typing import Dict, Any, List
from app.models.schemas import AnalysisPayload, ForecastReport, ScenarioForecast, ImpactPrediction
import numpy as np
from sklearn.linear_model import LinearRegression
import warnings

class ForecastingAgent:
    """
    The 'Oracle' Agent.
    Role: Predict future trends and run simulations ("God Mode").
    Phase 2 Upgrade: Structured ForecastReport with Scenarios.
    """
    
    def predict(self, data: AnalysisPayload) -> ForecastReport:
        """
        Executes forecasting with 3 scenarios: Conservative, Neutral, Aggressive.
        Now uses actual historical data from AnalysisPayload if available, or falls back gracefully.
        """
        # 1. Extract Historical Data (Semantic Unit: Monthly Revenue)
        # We expect 'monthly_revenue' in trends.
        if not data.trends.get("monthly_revenue") or len(data.trends["monthly_revenue"]) < 3:
             # Not enough data for trusted regression
             return self._empty_report()
             
        revenues = np.array(data.trends.get("monthly_revenue")).reshape(-1, 1)
        months = np.array(range(len(revenues))).reshape(-1, 1)
        
        # 2. Train Model (Base Logic)
        model = LinearRegression()
        model.fit(months, revenues)
        
        # Calculate R^2 for Confidence
        r_squared = model.score(months, revenues)
        # Cap confidence based on data quality (Input Confidence * Model Fit)
        model_confidence = min(data.confidence_score, max(0.0, r_squared))

        # 3. Forecast Next 3 Months
        future_months = np.array(range(len(revenues), len(revenues) + 3)).reshape(-1, 1) 
        base_prediction = model.predict(future_months).flatten()
        
        # 4. Generate Scenarios (Confidence-Aware)
        scenarios = []
        
        # Neutral (Base Model)
        scenarios.append(ScenarioForecast(
            scenario_name="Neutral",
            predicted_revenue=[round(x, 2) for x in base_prediction],
            confidence_band_upper=[round(x * (1 + (1-model_confidence)), 2) for x in base_prediction], 
            confidence_band_lower=[round(x * (1 - (1-model_confidence)), 2) for x in base_prediction],
            assumptions={"growth": "Linear Trend", "volatility": f"R2={r_squared:.2f}"}
        ))
        
        # Conservative (Base - Volatility Penalty)
        # If confidence is low, the conservative estimate should be lower
        penalty = 0.10 + (1.0 - model_confidence) * 0.20 # 10% base + up to 20% more if low confidence
        cons_prediction = base_prediction * (1.0 - penalty)
        scenarios.append(ScenarioForecast(
            scenario_name="Conservative",
            predicted_revenue=[round(x, 2) for x in cons_prediction],
            confidence_band_upper=[round(x, 2) for x in base_prediction], # Upper is base
            confidence_band_lower=[round(x * (1.0 - penalty - 0.05), 2) for x in cons_prediction],
            assumptions={"growth": f"Trend -{penalty*100:.0f}%", "volatility": "Risk Adjusted"}
        ))
        
        # Aggressive (Base + 10%)
        agg_prediction = base_prediction * 1.10
        scenarios.append(ScenarioForecast(
            scenario_name="Aggressive",
            predicted_revenue=[round(x, 2) for x in agg_prediction],
            confidence_band_upper=[round(x * 1.15, 2) for x in agg_prediction],
            confidence_band_lower=[round(x * 0.98, 2) for x in agg_prediction],
            assumptions={"growth": "Trend + 10%", "volatility": "Optimistic"}
        ))
        
        # Construct Chart Data (Baseline + Confidence)
        forecast_data = [] 
        for m, rev, low, high in zip(future_months.flatten(), base_prediction, scenarios[0].confidence_band_lower, scenarios[0].confidence_band_upper):
             forecast_data.append({
                 "month": f"M{m+1}", # accurate relative month index
                 "predicted_revenue": round(rev, 2),
                 "confidence_low": round(low, 2),
                 "confidence_high": round(high, 2)
             })

        return ForecastReport(
            scenarios=scenarios,
            best_case_total=round(sum(agg_prediction), 2),
            worst_case_total=round(sum(cons_prediction), 2),
            forecast_data=forecast_data,
            model_confidence=round(model_confidence, 2)
        )

    def simulate_action(self, target_metric: str, action_type: str, change_percent: float) -> ImpactPrediction:
        """
        Simulates impact using regression logic where possible.
        Replaces 'OracleAgent' with deterministic estimates.
        """
        # Default / Fallback
        impact_value = 0.0
        confidence = 0.5 # Default low confidence for unmodeled actions
        details = "Generic simulation."
        
        # 1. Marketing Spend (ROI Model)
        if action_type == "Marketing Spend":
            # Assumption: ROI is roughly Revenue Growth / Expense Ratio? 
            # For MVP: Assume 3.0 ROI is a business truth unless data says otherwise.
            # Real Shadow CFO would calculate this from historical correlations.
            assumed_roi = 3.0
            
            # If we cut spending (-), we save cash (+) but loose revenue (-)
            # Net Impact on Profit = (Spend_Cut) - (Lost_Revenue_Margin)
            # Let's simplify: Direct Bottom Line Impact.
            # We must return PERCENTAGE impact if absolute is impossible, 
            # but usually the Caller (Advisor) has the absolute numbers.
            # Advisor Usage: simulate_action logic requires baseline.
            # Since strict signature match is required for now, we return 0.0 and Advisor fails?
            # Or we strictly demand the new signature. The Advisor is being updated next.
            # So I will define the method signature I WANT here, and update Advisor to match it next.
            pass 

        return ImpactPrediction(
            input_action=f"{action_type} {change_percent*100:+.0f}%",
            predicted_metric=target_metric,
            predicted_impact_value=0.0, # Placeholder
            confidence_score=0.0,
            explanation="Simulation requires baseline data."
        )

    def simulate_action_with_data(self, target_metric: str, action_type: str, change_percent: float, baseline_value: float) -> ImpactPrediction:
        """
        New Simulation Method requiring Baseline Data (Truth).
        """
        impact = 0.0
        confidence = 0.8 # Standard model confidence
        
        if action_type == "Marketing Spend":
            # ROI Model
            roi = 2.5
            # Cost Change = baseline * change (% change in spend)
            # If change is negative (cut), Cost Change is negative (savings = positive profit?)
            # Wait, strictly: Expenses Change = baseline * change.
            # Revenue Change = Expenses Change * roi.
            # Profit Change = Revenue Change - Expenses Change.
            
            # Example: Spend 100k. Cut 10% (-0.1).
            # Expenses Change = 100k * -0.1 = -10k (Expenses go DOWN)
            # Revenue Change = -10k * 2.5 = -25k (Revenue goes DOWN)
            # Profit Change = (-25k) - (-10k) = -15k (Profit goes DOWN)
            
            # Example: Spend 100k. Increase 10% (+0.1).
            # Expenses Change = +10k.
            # Revenue Change = +25k.
            # Profit Change = 25k - 10k = +15k.
            
            spend_change = baseline_value * change_percent
            rev_change = spend_change * roi
            profit_change = rev_change - spend_change
            
            impact = profit_change
            details = f"Modeled with ROI {roi}x. " 
            if impact > 0: details += "Investment yields net profit growth."
            else: details += "Cost savings outweighed by lost revenue."

        elif action_type == "Pricing":
            # Elasticity: -1.5 (Price up 1% -> Volume down 1.5%)
            elasticity = -1.5
            
            # Revenue = Price * Volume
            # New Rev = (P * 1.05) * (V * (1 + 0.05*elasticity))
            # New Rev ~= P*V * (1 + %p + %v) approx
            # Combined effect = change + (change * elasticity)
            
            # Revenue Impact %
            rev_impact_pct = change_percent + (change_percent * elasticity)
            # We need Revenue Baseline (baseline_value should be Revenue here)
            
            impact = baseline_value * rev_impact_pct
            details = f"Price Elasticity {elasticity}. "
            if impact > 0: details += "Price hike outweighs volume loss."
            else: details += "Volume loss outweighs price hike."
            
        return ImpactPrediction(
            input_action=f"{action_type} {change_percent*100:+.0f}%",
            predicted_metric=target_metric,
            predicted_impact_value=impact,
            confidence_score=confidence,
            explanation=details
        )
    
    def _empty_report(self) -> ForecastReport:
        empty_scenario = ScenarioForecast(
            scenario_name=" insufficient_data", predicted_revenue=[], 
            confidence_band_upper=[], confidence_band_lower=[], assumptions={}
        )
        return ForecastReport(
            scenarios=[empty_scenario],
            best_case_total=0.0,
            worst_case_total=0.0,
            forecast_data=[],
            model_confidence=0.0
        )
