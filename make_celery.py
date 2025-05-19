import os
from dotenv import load_dotenv

from app import create_app  # noqa
from app.config import configs as config  # noqa

load_dotenv(override=False)

config_name = os.environ.get("FLASK_CONFIG") or "develop"
config_app = config[config_name]
flask_app = create_app(config_app)
celery_app = flask_app.extensions["celery"]
