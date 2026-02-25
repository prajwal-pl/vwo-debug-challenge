import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "financial_analyzer",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,  # Results expire after 1 hour
    task_acks_late=True,  # Don't ack until task completes (crash safety)
    worker_prefetch_multiplier=1,  # Only fetch 1 task at a time per worker
)
