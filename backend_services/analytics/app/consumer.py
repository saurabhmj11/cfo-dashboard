import asyncio
import json
import os
import aio_pika
from typing import Dict, Any
from app.services.analytics import AnalyticsEngine
from app.models.schemas import TransactionBase, AnalysisPayload
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Analytics_Consumer")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

engine = AnalyticsEngine()

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            run_id = payload.get('run_id')
            logger.info(f"Received Data.Uploaded event for run_id: {run_id}")
            
            # 1. Extract transactions
            tx_data = payload.get("tx_data", [])
            transactions = [tx for tx in tx_data]
            
            # 2. Compute metrics & anomalies
            # compute_metrics takes list of objects with dot notation (t.revenue) normally, 
            # let's convert dicts to TransactionBase objects so engine works unmodified.
            tx_objects = [TransactionBase(
                date=tx["date"], 
                revenue=tx["revenue"], 
                expenses=tx["expenses"], 
                category=tx["category"]
            ) for tx in transactions]
            
            result = engine.compute_metrics(tx_objects)
            
            # 3. Publish to Orchestrator 'NeedsDeepDive' queue
            out_payload = {
                "run_id": run_id,
                "dataset_id": payload.get("dataset_id"),
                "tenant_id": payload.get("tenant_id"),
                "user_id": payload.get("user_id"),
                "metrics": result["legacy"],
                "analysis_payload": result["payload"]
            }
            
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.declare_queue("Analysis.NeedsDeepDive", durable=True)
                
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(out_payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key="Analysis.NeedsDeepDive",
                )
                logger.info(f"Metrics computed. Published Analysis.NeedsDeepDive for run_id: {run_id}")
                
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")

async def start_consumer():
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                
                # Set prefetch count to 1 for fair dispatch
                await channel.set_qos(prefetch_count=1)
                queue = await channel.declare_queue("Data.Uploaded", durable=True)
                
                logger.info("Waiting for messages on Data.Uploaded")
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        await process_message(message)
        except Exception as e:
            logger.warning(f"Connection lost, retrying in 5s... ({str(e)})")
            await asyncio.sleep(5)
