import os
import json
from typing import Dict, Any, List
from app.models.schemas import FinancialAnalysisResult
from app.services.agents.orchestrator import FinancialOrchestrator
from openai import OpenAI

# Global Orchestrator instance to reuse agents if they have state (optional)
orchestrator = FinancialOrchestrator()

def generate_insights(analysis: FinancialAnalysisResult, mock: bool = True) -> Dict[str, Any]:
    """
    Generates structured insights using the Multi-Agent Financial Orchestrator.
    """
    try:
        # Delegate to the Triad
        return orchestrator.run_analysis(analysis)
        
    except Exception as e:
        print(f"Orchestrator Error: {e}")
        # Fallback (Guardrail)
        return {
            "executive_summary": ["Error generating insights from Agent Swarm."],
            "key_observations": [],
            "root_cause_analysis": f"System Error: {str(e)}",
            "recommendations": [],
            "risks": []
        }

def generate_text(messages: List[Dict[str, str]]) -> str:
    """
    Simple wrapper for Chat Completion (Virtual CFO Chat).
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-mock-key")) # Fallback for demo
        
        # If mock key, return mock response to avoid crash
        if client.api_key == "sk-mock-key":
             return "I am a Virtual CFO (Demo Mode). Integrate OpenAI Key to get real AI responses. Based on current data, your revenue looks strong!"
             
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"I'm having trouble thinking right now. Error: {str(e)}"
