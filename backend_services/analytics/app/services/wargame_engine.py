from typing import List, Dict, Optional
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
from app.models.schemas import FinancialAnalysisResult

fake = Faker()

class WargameEngine:
    """
    The Shadow CFO Engine.
    Generates synthetic "Future History" based on strategic parameters.
    """
    
    def simulate(self, 
                 baseline_metrics: Dict, 
                 strategy: str = "custom",
                 growth_factor: float = 1.0, 
                 churn_factor: float = 0.0,
                 months: int = 12) -> Dict:
        """
        Generates a shadow ledger for the next 12 months.
        
        Args:
            baseline_metrics: The 'financials' dict from the latest real analysis.
            growth_factor: Multiplier for revenue (e.g., 1.10 = 10% growth).
            churn_factor: Probability of losing a recurring revenue stream (0.0 - 1.0).
            months: How far to simulate.
            
        Returns:
            Dict containing 'shadow_ledger' and 'impact_analysis'.
        """
        
        # 1. extract Baseline DNA
        monthly_data = baseline_metrics.get("monthly_data", [])
        if not monthly_data:
            start_revenue = 10000
            start_expenses = 8000
        else:
            last_month = monthly_data[-1]
            # Handle if last_month is dict or object (Pydantic model dumped to dict)
            if isinstance(last_month, dict):
                 start_revenue = last_month.get("revenue", 10000)
                 start_expenses = last_month.get("expenses", 8000)
            else:
                 # Fallback if Pydantic object
                 start_revenue = getattr(last_month, "revenue", 10000)
                 start_expenses = getattr(last_month, "expenses", 8000)
        
        start_date = datetime.now().replace(day=1) + timedelta(days=32)
        start_date = start_date.replace(day=1) # First day of next month
        
        shadow_ledger = []
        monthly_summary = []
        
        current_rev = start_revenue
        current_exp = start_expenses
        
        total_sim_revenue = 0
        total_sim_profit = 0
        
        for i in range(months):
            curr_month_date = (start_date + timedelta(days=30*i)).replace(day=1)
            month_str = curr_month_date.strftime("%Y-%m")
            
            # Apply Growth Logic
            # Random noise + Strategic Trend
            noise = np.random.normal(0, 0.05) # +/- 5% monthly volatility
            
            # Revenue Calculation
            # If strategy is "Aggressive Growth", we compund growth
            # If "Cost Cutting", we reduce expenses
            
            step_growth = growth_factor - 1.0
            # Monthly compounding effect of the strategy
            # If 20% annual growth, that's ~1.5% monthly
            monthly_growth_rate = step_growth / 12.0
            
            current_rev = current_rev * (1 + monthly_growth_rate + noise)
            
            # Churn Impact (Random Revenue Drop)
            if random.random() < churn_factor:
                 loss = current_rev * random.uniform(0.05, 0.15) # Lose 5-15% of rev
                 current_rev -= loss
                 # Generate a specific "Churn Event" transaction
                 shadow_ledger.append({
                     "date": curr_month_date.strftime("%Y-%m-%d"),
                     "amount": -round(loss, 2),
                     "category": "Churn Loss",
                     "description": f"LOST CUSTOMER: {fake.company()} (Churn Event)",
                     "type": "loss"
                 })

            # Expense Calculation
            # If Strategy is Cost Cutting, expenses reduce
            expense_factor = 1.0
            if "cut" in strategy.lower():
                expense_factor = 0.98 # -2% expenses per month compounding
            
            current_exp = current_exp * (1 + noise) * expense_factor

            # Generate Granular Transactions for this month
            # We simulate ~10-20 transactions to make up the revenue
            num_txns = random.randint(10, 20)
            avg_ticket = current_rev / num_txns
            
            month_rev_actual = 0
            
            for _ in range(num_txns):
                val = avg_ticket * random.uniform(0.8, 1.2)
                month_rev_actual += val
                shadow_ledger.append({
                    "date": curr_month_date.strftime("%Y-%m-%d"),
                    "amount": round(val, 2),
                    "category": "Revenue",
                    "description": f"Sales: {fake.company()}",
                    "type": "revenue"
                })
                
            # Generate Expense Transactions
            shadow_ledger.append({
                "date": curr_month_date.strftime("%Y-%m-%d"),
                "amount": round(current_exp, 2),
                "category": "Operations",
                "description": "Monthly Operating Expenses",
                "type": "expense"
            })
            
            # Monthly Summary
            profit = month_rev_actual - current_exp
            monthly_summary.append({
                "month": month_str,
                "revenue": round(month_rev_actual, 2),
                "expenses": round(current_exp, 2),
                "profit": round(profit, 2)
            })
            
            total_sim_revenue += month_rev_actual
            total_sim_profit += profit

        return {
            "simulation_id": str(random.randint(10000, 99999)),
            "strategy_name": strategy,
            "summary": {
                "total_revenue": round(total_sim_revenue, 2),
                "total_profit": round(total_sim_profit, 2),
                "avg_margin": round((total_sim_profit/total_sim_revenue)*100, 1) if total_sim_revenue else 0
            },
            "monthly_projection": monthly_summary,
            "shadow_ledger": shadow_ledger
        }

wargame_engine = WargameEngine()
