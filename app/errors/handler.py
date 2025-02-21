# coding: utf8
import traceback
from flask import current_app, jsonify
from werkzeug.exceptions import HTTPException

from .exceptions import ApiException


def api_error_handler(error):
    try:
        if isinstance(error, ApiException):
            current_app.logger.warning(
                f"HTTP_STATUS_CODE: {error.status_code} - {error.to_dict}"
            )
            return jsonify(error.to_dict), error.status_code
        if isinstance(error, HTTPException):
            return (
                jsonify({"error": {"code": error.code, "message": error.description}}),
                error.code,
            )
        current_app.logger.error(error)
        return (
            jsonify({"error": {"code": 500, "message": "Internal Server Error"}}),
            500,
        )
    except Exception as e:
        traceback.print_exc()
        return (
            jsonify({"error": {"code": 500, "message": "Internal Server Error"}}),
            500,
        )
