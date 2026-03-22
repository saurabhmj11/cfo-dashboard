import asyncio
import json
import os
import aio_pika
from typing import Dict, Any
from app.services.agents.orchestrator import FinancialOrchestrator
from app.models.schemas import AnalysisPayload
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Orchestrator_Consumer")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

orchestrator = FinancialOrchestrator()

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            run_id = payload.get('run_id')
            logger.info(f"Received Analysis.NeedsDeepDive for run_id: {run_id}")
            
            analysis_payload = AnalysisPayload(**payload["analysis_payload"])
            
            # The orchestrator handles bypassing internally if there are no anomalies
            # or runs full AI agents if necessary!
            result = orchestrator.run_analysis(analysis_payload)
            
            out_payload = {
                "run_id": run_id,
                "metrics_result": {
                    "financials": payload["metrics"],
                    "detective": result["detective_report"].model_dump(mode='json')  if hasattr(result["detective_report"], 'model_dump') else result["detective_report"]
                },
                "forecast_result": result["forecast_report"].model_dump(mode='json') if hasattr(result["forecast_report"], 'model_dump') else result["forecast_report"],
                "advisor_result": result["advisor_report"].model_dump(mode='json') if hasattr(result["advisor_report"], 'model_dump') else result["advisor_report"],
                "status": "COMPLETED"
            }
            
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.declare_queue("Analysis.Complete", durable=True)
                
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(out_payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key="Analysis.Complete",
                )
                logger.info(f"Published Analysis.Complete for run_id: {run_id}")
                
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            # Publish failed event back to Gateway DB
            try:
                connection = await aio_pika.connect_robust(RABBITMQ_URL)
                async with connection:
                    channel = await connection.channel()
                    await channel.declare_queue("Analysis.Complete", durable=True)
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps({"run_id": payload.get('run_id'), "status": "FAILED", "error_message": str(e)}).encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                        ),
                        routing_key="Analysis.Complete",
                    )
            except Exception:
                pass

async def start_consumer():
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                queue = await channel.declare_queue("Analysis.NeedsDeepDive", durable=True)
                
                logger.info("Waiting for messages on Analysis.NeedsDeepDive")
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        await process_message(message)
        except Exception as e:
            logger.warning(f"Connection lost, retrying in 5s... ({str(e)})")
            await asyncio.sleep(5)
