import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, Optional
from datetime import datetime

class MongoDBService:
    def __init__(self):
        self.client = None
        self.db = None
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.db_name = os.getenv("MONGODB_DB_NAME", "financial_analyst")

    def connect(self):
        if not self.client:
            self.client = AsyncIOMotorClient(self.mongodb_url)
            self.db = self.client[self.db_name]
            print(f"[MONGODB] Connected to {self.db_name}")

    async def save_analysis_result(self, analysis_run_id: int, result_data: Dict[str, Any]):
        """
        Saves large AI analysis result to MongoDB.
        """
        if not self.db:
            self.connect()
        
        collection = self.db["analysis_results"]
        document = {
            "analysis_run_id": analysis_run_id,
            "data": result_data,
            "created_at": datetime.utcnow()
        }
        result = await collection.update_one(
            {"analysis_run_id": analysis_run_id},
            {"$set": document},
            upsert=True
        )
        return result.upserted_id or True

    async def get_analysis_result(self, analysis_run_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves analysis result from MongoDB.
        """
        if not self.db:
            self.connect()
        
        collection = self.db["analysis_results"]
        doc = await collection.find_one({"analysis_run_id": analysis_run_id})
        return doc["data"] if doc else None

    async def save_agent_trace(self, analysis_run_id: int, agent_name: str, trace_data: Dict[str, Any]):
        """
        Saves granular agent decision-making traces.
        """
        if not self.db:
            self.connect()
        
        collection = self.db["agent_traces"]
        document = {
            "analysis_run_id": analysis_run_id,
            "agent_name": agent_name,
            "trace": trace_data,
            "timestamp": datetime.utcnow()
        }
        await collection.insert_one(document)

# Singleton
mongodb_service = MongoDBService()
