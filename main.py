# coding: utf8
from gevent import monkey

monkey.patch_all()

import os

from dotenv import load_dotenv
from flask import request

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path, override=True)

from app import create_app  # noqa
from app.config import configs as config  # noqa

config_name = os.environ.get("FLASK_CONFIG") or "develop"
config_app = config[config_name]
application = app = create_app(config_app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
VOICE_FOLDER = os.path.join(os.getcwd(), "static/voice")

# Danh sách IP được phép truy cập
ALLOWED_IPS = {"118.70.171.129", "218.154.54.97"}

# Endpoint không cần kiểm tra IP
EXCLUDED_ENDPOINTS = {"/api/v1/setting/get_public_config"}


@app.route("/", methods=["GET"])
def index():
    headers = dict(request.headers)
    params = dict(request.args)
    is_show_headers = params.get("show_header", "false").lower() == "true"
    if is_show_headers:
        return {
            "message": "Welcome to the Flask API",
            "headers": headers,
        }
    else:
        return {
            "message": "Welcome to the Flask API",
        }


if __name__ == "__main__":
    is_debug = config_name == "develop"
    application.run(debug=True)
