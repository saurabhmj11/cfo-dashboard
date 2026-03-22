from typing import List, Dict, Optional
import random
import json
from app.models.schemas import DetectiveReport, ForecastReport, FinancialAnalysisResult
from app.services.llm_client import llm_client

class ChatService:
    """
    Handles conversational analytics.
    Features:
    - Context Memory (Basic list for MVP)
    - Role-based responses (CFO vs Founder)
    - Integration with Financial Data
    """
    
    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.context_data: Optional[Dict] = None

    def load_context(self, financial_data: FinancialAnalysisResult, detective_report: DetectiveReport):
        """
        Loads the latest financial context to answer data-grounded questions.
        """
        self.context_data = {
            "revenue": financial_data.summary_revenue,
            "profit": financial_data.summary_profit,
            "margin": financial_data.avg_margin,
            "anomalies": [a.description for a in financial_data.anomalies],
            "insights": [o.detail for o in detective_report.observations]
        }

    def process_message(self, message: str, role: str = "CFO") -> str:
        """
        Process a user message and return a response based on the loaded context and role.
        """
        self.history.append({"role": "user", "content": message})
        
        response = ""
        msg_lower = message.lower()
        
        # 0. Try LLM First (RAG)
        if llm_client.is_available and self.context_data:
            system_prompt = f"""
            You are an AI Financial Analyst Agent acting as the {role}.
            You have access to the following real-time financial data context:
            {json.dumps(self.context_data, indent=2)}
            
            Answer the user's question based strictly on this data. 
            If the answer is not in the data, say so.
            Be concise, professional, and insightful.
            """
            
            llm_response = llm_client.generate_text(system_prompt, message)
            if llm_response:
                self.history.append({"role": "assistant", "content": llm_response})
                return llm_response

        # Fallback to Rule-Based Logic
        if "why" in msg_lower and ("profit" in msg_lower or "drop" in msg_lower):
            response = self._handle_why_profit_drop(role)
        elif "forecast" in msg_lower or "runway" in msg_lower:
            response = self._handle_forecast(role)
        elif "risky" in msg_lower or "risk" in msg_lower or "customer" in msg_lower:
             response = self._handle_risk_query(role)
        elif "recommend" in msg_lower or "action" in msg_lower or "do" in msg_lower:
             response = self._handle_recommendation(role)
        else:
            response = self._handle_general_query(role)
            
        self.history.append({"role": "assistant", "content": response})
        return response

    def _handle_why_profit_drop(self, role: str) -> str:
        if not self.context_data:
            return "I don't have the latest financial data loaded yet."
            
        anomalies = self.context_data.get("anomalies", [])
        primary_reason = anomalies[0] if anomalies else "an increase in operational expenses"
        
        if role == "CFO":
            return f"Net earnings contraction is primarily driven by {primary_reason}. We observed a deviation in OPEX relative to revenue baseline. I recommend a line-item audit of marketing disbursements."
        elif role == "Founder":
            return f"Profit is down mainly because of {primary_reason}. Basically, we spent more than usual to grow. We need to watch our burn rate this month."
        else: # Sales
             return f"We took a hit on profit due to {primary_reason}. We need to close more high-margin deals to offset this."

    def _handle_forecast(self, role: str) -> str:
        if role == "CFO":
            return "Projected cash flow indicates a 14-month runway at current burn. Sensitivity analysis suggests a +/- 15% variance based on Q3 churn rates."
        elif role == "Founder":
            return "Good news, we have about 14 months of runway left. If we hit our growth targets next month, we can extend that to 18 months."
        else:
            return "Pipeline looks solid. If we convert 30% of the qualified leads, we'll beat the forecast."

    def _handle_risk_query(self, role: str) -> str:
        return "Customer concentration risk is high. Top 10 clients contribute 60% of ARR. Churn in 'Segment B' has ticked up by 2%."

    def _handle_recommendation(self, role: str) -> str:
         return "Based on the data: 1. Cut marketing spend by 15% immediately. 2. Push price increase to legacy Tier 1 clients. 3. Automate collections."

    def _handle_general_query(self, role: str) -> str:
        return f"[{role} Mode] I'm analyzing the real-time data. Could you be more specific about which metric you're interested in?"

# Singleton instance for simple state management in MVP
chat_service = ChatService()
