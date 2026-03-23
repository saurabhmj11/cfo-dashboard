import time
import random

def fetch_live_market_data():
    """Simulates automatically fetching daily financial data from Plaid / ERP APIs."""
    print("🔄 Connecting to secure ERP/Market APIs (Bypassing Human CSV Upload)...")
    time.sleep(2)
    # Generate mock live ingested data
    revenue = random.randint(50000, 150000)
    expenses = random.randint(20000, 80000)
    return {"daily_revenue": revenue, "daily_expenses": expenses, "timestamp": time.time()}

def ingest_data_autonomously():
    print("--- ⏱️ Daily Autonomous Ingestion Triggered (06:00 AM) ---")
    data = fetch_live_market_data()
    
    print(f"✅ Autonomously ingested £{data['daily_revenue']} revenue data.")
    print("📥 Syncing clean data directly to the RabbitMQ Analysis Queue...")
    print("🤖 Waking up Gemini Detective for Risk Analysis...")
    # Emits directly to backend queue, totally unsupervised.

if __name__ == "__main__":
    ingest_data_autonomously()
