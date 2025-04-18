# coding: utf8
import os

from dotenv import load_dotenv
from flask import abort, send_from_directory

load_dotenv(override=False)

from app import create_app  # noqa
from app.config import configs as config  # noqa

config_name = os.environ.get("FLASK_CONFIG") or "develop"
config_app = config[config_name]
application = app = create_app(config_app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
VOICE_FOLDER = os.path.join(os.getcwd(), "static/voice")


 


if __name__ == "__main__":
    is_debug = config_name == "develop"
    application.run(debug=True)
