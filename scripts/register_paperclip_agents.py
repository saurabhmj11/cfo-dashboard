import os
import requests
import time

PAPERCLIP_URL = os.getenv("PAPERCLIP_URL", "http://localhost:3100")
COMPANY_ID = os.getenv("PAPERCLIP_COMPANY_ID")

# Defined as "Employees" in Paperclip v0.3.1
AGENTS = [
    {
        "name": "Gemini Detective",
        "role": "financial_detective",
        "title": "Forensic Accountant",
        "budgetMonthlyCents": 5000, # $50.00
        "adapterType": "python-rabbitmq-bridge",
        "adapterConfig": {"queue": "analysis_queue"}
    },
    {
        "name": "Gemini Forecaster",
        "role": "financial_forecaster",
        "title": "Risk Modeler",
        "budgetMonthlyCents": 10000, # $100.00
        "adapterType": "python-rabbitmq-bridge",
        "adapterConfig": {"queue": "analysis_queue"}
    },
    {
        "name": "Gemini Advisor",
        "role": "financial_advisor",
        "title": "Chief Financial Officer (AI)",
        "budgetMonthlyCents": 2500, # $25.00
        "adapterType": "python-rabbitmq-bridge",
        "adapterConfig": {"queue": "analysis_queue"}
    }
]

def hire_agents_into_paperclip():
    if not COMPANY_ID:
        print("❌ Error: PAPERCLIP_COMPANY_ID not set.")
        return

    print(f"🏢 Connecting to Paperclip v0.3.1 at {PAPERCLIP_URL}...")
    print("--- Hiring AI Workforce ---")
    
    for agent_cfg in AGENTS:
        try:
            print(f"Hiring {agent_cfg['name']}...")
            response = requests.post(
                f"{PAPERCLIP_URL}/api/companies/{COMPANY_ID}/agent-hires",
                json=agent_cfg,
                timeout=10
            )
            if response.status_code in [200, 201]:
                data = response.json()
                agent_id = data.get("agent", {}).get("id")
                print(f"✅ Successfully hired {agent_cfg['name']} (ID: {agent_id})")
            else:
                print(f"❌ Failed to hire {agent_cfg['name']}: {response.text}")
        except Exception as e:
            print(f"❌ Connection Error for {agent_cfg['name']}: {e}")
            
    print("🎉 AI Workforce registration attempted.")

if __name__ == "__main__":
    hire_agents_into_paperclip()
