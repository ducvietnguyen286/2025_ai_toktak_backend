# celery_worker.py
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.config import configs  # Thêm dòng này
from celery import Celery


def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # 👉 Quan trọng: Tự động tìm tất cả task trong app/
    celery.autodiscover_tasks(['app'])

    return celery


config_name = os.getenv("FLASK_CONFIG", "develop")
flask_app = create_app(configs[config_name])
celery = make_celery(flask_app)
