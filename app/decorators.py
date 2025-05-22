# coding: utf8
from functools import wraps

from flask import request
from flask_jwt_extended import verify_jwt_in_request
from jsonschema import FormatChecker, validate
from jsonschema.exceptions import ValidationError
from app.errors.exceptions import BadRequest, Unauthorized
from app.services.auth import AuthService
from app.lib.response import Response


def jwt_optional(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.headers.get("Authorization"):
            try:
                verify_jwt_in_request()
            except Exception as e:
                raise Unauthorized(message="Unauthorized")
        return fn(*args, **kwargs)

    return wrapper


def required_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            raise Unauthorized(message="Unauthorized")

        current_user = AuthService.get_current_identity()
        if not current_user or getattr(current_user, "user_type", 0) != 1:
            return Response(
                message="Bạn không có quyền",
                code=201,
            ).to_dict()
        return fn(*args, **kwargs)

    return wrapper


def parameters(**schema):
    def decorated(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.endpoint == "api.user_api_new_link":
                req_args = request.get_json()
                new_args = args + (req_args,)
                return func(*new_args, **kwargs)

            req_args = request.args.to_dict()
            if (
                request.method in ("POST", "PUT", "PATCH", "DELETE")
                and request.mimetype == "application/json"
            ):
                req_args.update(request.get_json())

            if (
                request.method in ("POST", "PUT", "PATCH", "DELETE")
                and request.mimetype == "multipart/form-data"
            ):
                req_args.update(request.form.to_dict())

            req_args = {
                k: v for k, v in req_args.items() if k in schema["properties"].keys()
            }

            if "required" in schema:
                for field in schema["required"]:
                    if field not in req_args or not req_args[field]:
                        field_name = field
                        if field in schema["properties"]:
                            if "name" in schema["properties"][field]:
                                field_name = schema["properties"][field]["name"]
                        message = "{} is required".format(field_name)
                        return Response(
                            message=message,
                            message_en="Request parameters are invalid.",
                            status=500,
                        ).to_dict()

            try:
                validate(
                    instance=req_args, schema=schema, format_checker=FormatChecker()
                )
            except ValidationError as exp:
                exp_info = list(exp.schema_path)
                error_type = (
                    "type",
                    "format",
                    "pattern",
                    "maxLength",
                    "minLength",
                    "enum",
                )

                if set(exp_info).intersection(set(error_type)):
                    field = exp_info[1]
                    field_config = schema["properties"].get(field, {})
                    field_name_kr = field_config.get("name", field)  # name tiếng Hàn
                    valid_values = field_config.get("enum", [])

                    message = f"'{field_name_kr}' 필드의 값이 올바르지 않습니다."
                    message_en = f"Field '{field}' is not valid."

                    if valid_values:
                        enum_values = ", ".join(valid_values)
                        message += f" 허용된 값: {enum_values}."
                        message_en += f" Valid values: {enum_values}."
                else:
                    message = "요청 파라미터가 잘못되었습니다."
                    message_en = "Request parameters are invalid."

                return Response(
                    message=message, message_en=message_en, status=500
                ).to_dict()

            if request.endpoint == "api.maker_api_make_post":
                kwargs["req_args"] = req_args
                return func(*args, **kwargs)

            new_args = args + (req_args,)
            return func(*new_args, **kwargs)

        return wrapper

    return decorated


def admin_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            current_user = AuthService.get_current_identity()
            if not current_user or getattr(current_user, "user_type", 0) != 1:
                return Response(
                    message="Bạn không có quyền",
                    code=201,
                ).to_dict()
            return fn(*args, **kwargs)

        return decorator

    return wrapper
