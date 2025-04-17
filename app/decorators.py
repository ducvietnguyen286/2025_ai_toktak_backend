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
                        raise BadRequest(message="{} is required".format(field_name))
            try:
                validate(
                    instance=req_args, schema=schema, format_checker=FormatChecker()
                )
            except ValidationError as exp:
                exp_info = list(exp.schema_path)
                error_type = ("type", "format", "pattern", "maxLength", "minLength")
                if set(exp_info).intersection(set(error_type)):
                    field = exp_info[1]
                    field_name = field
                    if field_name in schema["properties"]:
                        if "name" in schema["properties"][field]:
                            field_name = schema["properties"][field]["name"]
                    message = "{} is not valid".format(field_name)
                else:
                    message = exp.message  # pragma: no cover
                raise BadRequest(message=message)

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
