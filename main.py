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
application = create_app(config_app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
VOICE_FOLDER = os.path.join(os.getcwd(), "static/voice")

# Danh sách IP được phép truy cập
ALLOWED_IPS = {"118.70.171.129", "218.154.54.97"}

# Endpoint không cần kiểm tra IP
EXCLUDED_ENDPOINTS = {"/api/v1/setting/get_public_config"}


<<<<<<< HEAD
# @app.before_request
# def limit_remote_addr():
#     # Kiểm tra nếu route không cần kiểm tra IP
#     print(request.path)
#     print("XXXXXXXXXXXXX")
#     if request.path in EXCLUDED_ENDPOINTS:
#         return
#     # Lấy IP của người dùng
#     remote_ip = request.remote_addr

#     # Nếu IP không hợp lệ thì trả lỗi JSON
#     if remote_ip not in const.ALLOWED_IPS:
#         return (
#             jsonify(
#                 {"error": "Forbidden", "message": f"Access denied for IP: {remote_ip}"}
#             ),
#             403,
#         )


# @app.route("/files/<path:filename>")
# def get_file(filename):
#     try:
#         return send_from_directory(UPLOAD_FOLDER, filename)
#     except FileNotFoundError:
#         abort(404)


# @app.route("/voice/<path:filename>")
# def serve_static(filename):
#     return send_from_directory(VOICE_FOLDER, filename)


@application.route("/", methods=["GET"])
=======
@app.route("/", methods=["GET"])
>>>>>>> 34f5810eff433ea0a3cfa01f357de6503cbe2b81
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
    application.run()
