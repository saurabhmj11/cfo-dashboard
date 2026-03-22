import asyncio
import json
import os
import aio_pika
from app.database import SessionLocal
from app.models.db_models import AnalysisRun
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Gateway_Consumer")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            run_id = payload.get('run_id')
            logger.info(f"Received Analysis.Complete event for run_id: {run_id}")
            
            with SessionLocal() as db:
                run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
                if run:
                    run.status = payload.get("status", "COMPLETED")
                    run.error_message = payload.get("error_message")
                    
                    if run.status == "COMPLETED":
                        run.metrics_result = payload.get("metrics_result")
                        run.forecast_result = payload.get("forecast_result")
                        run.advisor_result = payload.get("advisor_result")
                        
                    db.commit()
                    logger.info(f"Successfully updated AnalysisRun {run_id} to status: {run.status}")
                else:
                    logger.warning(f"AnalysisRun {run_id} not found in database!")
                    
        except Exception as e:
            logger.error(f"Failed to process Analysis.Complete message: {str(e)}")

async def start_consumer():
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                queue = await channel.declare_queue("Analysis.Complete", durable=True)
                
                logger.info("Waiting for messages on Analysis.Complete")
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        await process_message(message)
        except Exception as e:
            logger.warning(f"Connection lost, retrying in 5s... ({str(e)})")
            await asyncio.sleep(5)
