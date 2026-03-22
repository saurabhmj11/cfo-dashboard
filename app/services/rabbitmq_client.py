import aio_pika
import json
import os

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

async def publish_message(queue_name: str, message: dict):
    """
    Connects to RabbitMQ and publishes a JSON payload to a specific durable queue.
    """
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            # Ensure the queue exists
            await channel.declare_queue(queue_name, durable=True)
            
            # Send message
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue_name,
            )
            print(f"[RabbitMQ] Successfully published to {queue_name}. run_id: {message.get('run_id')}")
    except Exception as e:
        print(f"[RabbitMQ Error] Failed to publish message to {queue_name}: {str(e)}")
        # We raise the exception so the HTTP endpoint fails cleanly and notifies the user
        raise
