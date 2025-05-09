

from celery_worker import celery
import os
import requests
from dotenv import load_dotenv

from app.lib.logger import log_celery_worker_message

load_dotenv()  # Load .env file nếu chưa được load ở nơi khác

@celery.task
def call_maker_batch_api():
    url = os.getenv("MAKER_BATCH_API_URL")
    if not url:
        return {"error": "MAKER_BATCH_API_URL not set in .env"}

    try:
        
        log_celery_worker_message("Call:  call_maker_batch_api XXXXXXXXXXXXXXXXXXXXXXXXXXX")
        
        response = requests.post(f"{url}/api/v1/maker/batchs")
        return {"status_code": response.status_code, "response": response.text}
    except Exception as e:
        return {"error": str(e)}
