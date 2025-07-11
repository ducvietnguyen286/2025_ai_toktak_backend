# coding: utf8
from gevent import monkey

monkey.patch_all()

import os

from dotenv import load_dotenv
from flask import abort, send_from_directory, request, jsonify

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path, override=True)

from app import create_app  # noqa
from app.config import configs as config  # noqa

config_name = os.environ.get("FLASK_CONFIG") or "develop"
config_app = config[config_name]
application = create_app(config_app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
VOICE_FOLDER = os.path.join(os.getcwd(), "static/voice")

# Danh sách IP được phép truy cập
ALLOWED_IPS = {"118.70.171.129", "218.154.54.97"}

# Endpoint không cần kiểm tra IP
EXCLUDED_ENDPOINTS = {"/api/v1/setting/get_public_config"}


@application.route("/", methods=["GET"])
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


@application.route("/files/<path:filename>")
def get_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        abort(404)


@application.route("/voice/<path:filename>")
def serve_static(filename):
    return send_from_directory(VOICE_FOLDER, filename)




if __name__ == "__main__":
    application.run()
