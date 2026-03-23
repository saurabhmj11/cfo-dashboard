import time
import requests
import os
import pika
import json

PAPERCLIP_URL = os.getenv("PAPERCLIP_URL", "http://paperclip:3100")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

def fetch_and_route_tasks(company_id, agent_id):
    """
    V0.3.1 Heartbeat:
    1. Poll for 'todo' issues assigned to this agent.
    2. Post a 'checkout' to start the heartbeat run.
    3. Route to RabbitMQ for processing.
    """
    while True:
        try:
            # Poll for assigned TODO issues
            response = requests.get(
                f"{PAPERCLIP_URL}/api/companies/{company_id}/issues",
                params={"status": "todo", "assigneeAgentId": agent_id},
                timeout=5
            )
            if response.status_code == 200:
                issues = response.json()
                for issue in issues:
                    # 2. Checkout the issue (This creates the 'Heartbeat Run' in v0.3.1)
                    checkout_res = requests.post(f"{PAPERCLIP_URL}/api/issues/{issue['id']}/checkout", timeout=5)
                    if checkout_res.status_code == 200:
                        run_data = checkout_res.json()
                        task_payload = {
                            "paperclip_task_id": issue["id"],
                            "paperclip_run_id": run_data["id"],
                            "title": issue["title"],
                            "description": issue.get("description", ""),
                            # ... other context
                        }
                        route_to_rabbitmq(task_payload)
        except Exception as e:
            print(f"Adapter Error: {e}")
        time.sleep(10)

def route_to_rabbitmq(task):
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue='analysis_queue', durable=True)
    channel.basic_publish(
        exchange='',
        routing_key='analysis_queue',
        body=json.dumps(task),
        properties=pika.BasicProperties(delivery_mode=2) # make message persistent
    )
    connection.close()
    print(f"Routed Autonomous Task {task.get('id')} to Gemini AI Queue.")

import threading

def listen_for_results():
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue='Paperclip.Results', durable=True)
            
            def callback(ch, method, properties, body):
                result_data = json.loads(body)
                task_id = result_data.get("paperclip_task_id")
                print(f"Received results for Task {task_id}. Posting to Paperclip...")
                
                # Resolve the issue in Paperclip (v0.3.1 uses /resolve or status update)
                try:
                    requests.patch(
                        f"{PAPERCLIP_URL}/api/issues/{task_id}", 
                        json={
                            "status": "done",
                            "comment": result_data["result"]
                        },
                        timeout=5
                    )
                    print(f"Successfully resolved Paperclip Task {task_id}")
                except Exception as e:
                    print(f"Failed to post result to Paperclip: {e}")
                
                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(queue='Paperclip.Results', on_message_callback=callback)
            print("Listening for Paperclip Results...")
            channel.start_consuming()
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    print("Starting Paperclip v0.3.1 <-> RabbitMQ autonomous bridge...")
    time.sleep(5) 
    
    # In production, these would be loaded from env
    COMPANY_ID = os.getenv("PAPERCLIP_COMPANY_ID")
    AGENT_ID = os.getenv("PAPERCLIP_AGENT_ID")
    
    if not COMPANY_ID or not AGENT_ID:
        print("❌ Error: PAPERCLIP_COMPANY_ID and PAPERCLIP_AGENT_ID must be set.")
        exit(1)

    # Start the result listener in a background thread
    threading.Thread(target=listen_for_results, daemon=True).start()
    
    fetch_and_route_tasks(COMPANY_ID, AGENT_ID)
