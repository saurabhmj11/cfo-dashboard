import pandas as pd
import numpy as np
from typing import List, Dict, Any
from app.models.db_models import Transaction, MonthlyAggregate
from app.models.schemas import FinancialAnalysisResult, MonthlyMetric, Anomaly, AnalysisPayload
from app.services.analytics.ml_anomaly import ml_anomaly_detector

class AnalyticsEngine:
    """
    Layer 3: The Deterministic Math Engine.
    Principles:
    1. Zero Hallucination (Pure Math).
    2. Input: Validated Golden Data (Transactions).
    3. Output: Structured Metrics (FinancialAnalysisResult).
    """

    def compute_metrics(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """
        Aggregates raw transactions into monthly summaries and KPIs.
        Returns: { "legacy": FinancialAnalysisResult, "payload": AnalysisPayload }
        """
        if not transactions:
            return self._empty_result()

        # Convert ORM objects to DataFrame for vectorized math
        data = [
            {"date": t.txn_date, "revenue": t.revenue, "expenses": t.expenses, "category": t.category}
            for t in transactions
        ]
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period("M")

        # 1. Monthly Aggregation
        monthly = df.groupby('month').agg({
            'revenue': 'sum',
            'expenses': 'sum'
        }).reset_index()
        
        monthly['net_profit'] = monthly['revenue'] - monthly['expenses']
        monthly['margin_percent'] = np.where(monthly['revenue'] > 0, monthly['net_profit'] / monthly['revenue'], 0.0)
        
        # 2. Growth Calculation (MoM)
        monthly['revenue_growth'] = monthly['revenue'].pct_change().fillna(0.0) * 100

        # 3. Overall Summaries
        total_rev = monthly['revenue'].sum()
        total_exp = monthly['expenses'].sum()
        total_profit = total_rev - total_exp
        avg_margin = float(total_profit / total_rev) if total_rev > 0 else 0.0

        # 4. Anomaly Detection (Pre-Trained ML Model)
        anomalies = ml_anomaly_detector.detect_anomalies(monthly)
        
        # 6. Calculate Confidence & Trust
        confidence_result = self._calculate_data_confidence(monthly, df)

        # 5. Format Output (Legacy)
        monthly_metrics = []
        for _, row in monthly.iterrows():
            monthly_metrics.append(MonthlyMetric(
                month=str(row['month']),
                revenue=float(row['revenue']),
                expenses=float(row['expenses']),
                net_profit=float(row['net_profit']),
                margin_percent=float(row['margin_percent']),
                growth_mom=float(row['revenue_growth'])
            ))

        legacy_result = FinancialAnalysisResult(
            summary_revenue=float(total_rev),
            summary_expenses=float(total_exp),
            summary_profit=float(total_profit),
            avg_margin=avg_margin,
            monthly_data=monthly_metrics,
            anomalies=anomalies,
            confidence_score=confidence_result["score"]
        )

        # 7. Construct Strict AnalysisPayload
        payload = AnalysisPayload(
            kpis={
                "total_revenue": float(total_rev),
                "total_expenses": float(total_exp),
                "net_profit": float(total_profit),
                "avg_margin": avg_margin
            },
            trends={
                "revenue_growth_mom": [float(x) for x in monthly['revenue_growth'].tolist()],
                "latest_growth": float(monthly['revenue_growth'].iloc[-1]) if not monthly.empty else 0.0,
                "monthly_revenue": [float(x) for x in monthly['revenue'].tolist()] 
            },
            anomalies=anomalies,
            confidence_score=confidence_result["score"],
            data_quality_issues=confidence_result["issues"]
        )

        return {"legacy": legacy_result, "payload": payload}

    def _calculate_data_confidence(self, monthly_agg: pd.DataFrame, raw_df: pd.DataFrame) -> Dict[str, Any]:
        score = 1.0
        issues = []
        
        if monthly_agg.empty:
            return {"score": 0.0, "issues": ["No data available"]}

        avg_txns_per_month = len(raw_df) / len(monthly_agg)
        if avg_txns_per_month < 5:
            score -= 0.2
            issues.append(f"Low data density: Only {avg_txns_per_month:.1f} txns/month avg")

        if len(monthly_agg) > 1:
            full_range = pd.period_range(start=monthly_agg['month'].min(), end=monthly_agg['month'].max(), freq='M')
            if len(monthly_agg) < len(full_range):
                missing_count = len(full_range) - len(monthly_agg)
                score -= (0.1 * missing_count)
                issues.append(f"Data gaps detected: {missing_count} missing months")

        if 'revenue_growth' in monthly_agg.columns:
             high_volatility = monthly_agg[abs(monthly_agg['revenue_growth']) > 200]
             if not high_volatility.empty:
                 score -= 0.15
                 issues.append("Extreme volatility detected (>200% MoM swings)")

        return {"score": max(0.0, round(score, 2)), "issues": issues}

    def _empty_result(self) -> Dict[str, Any]:
        legacy = FinancialAnalysisResult(
            summary_revenue=0.0, summary_expenses=0.0, summary_profit=0.0,
            avg_margin=0.0, monthly_data=[], anomalies=[], confidence_score=0.0
        )
        payload = AnalysisPayload(kpis={}, trends={}, anomalies=[])
        return {"legacy": legacy, "payload": payload}
