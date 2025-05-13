# coding: utf8
from datetime import datetime
import os
import time
import traceback
import uuid
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response

from app.makers.images import ImageMaker
from app.services.auth import AuthService
from app.services.image_template import ImageTemplateService
from flask import request

ns = Namespace(name="image-template", description="User API")


@ns.route("/list")
class APIListImageTemplate(Resource):

    def get(self):
        image_templates = ImageTemplateService.get_image_templates()
        return Response(
            data=image_templates,
            message="Lấy danh sách thành công",
        ).to_dict()


@ns.route("/<int:id>")
class APIFindImageTemplate(Resource):

    @jwt_required()
    def get(self, id):
        image_template = ImageTemplateService.find_image_template(id)
        if not image_template:
            return Response(
                message="Không tìm thấy image_template",
                status=400,
            ).to_dict()

        return Response(
            data=image_template,
            message="Lấy template thành công",
        ).to_dict()


@ns.route("/create")
class APICreateImageTemplate(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "template_name": {"type": "string"},
            "template_code": {"type": "string"},
            "font_size": {"type": "string"},
            "main_text_color": {"type": "string"},
            "text_color": {"type": "string"},
            "stroke_color": {"type": "string"},
            "stroke_width": {"type": "string"},
            "text_shadow": {"type": "string"},
            "text_align": {"type": "string"},
            "text_position": {"type": "string"},
            "text_position_x": {"type": "string"},
            "text_position_y": {"type": "string"},
            "background": {"type": "string"},
            "background_color": {"type": "string"},
            "background_image": {"type": "string"},
            "padding": {"type": "string"},
            "margin": {"type": "string"},
            "type": {"type": "string"},
        },
        required=["template_name", "template_code", "font_size", "type"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            date_create = datetime.now().strftime("%Y_%m_%d")
            UPLOAD_FOLDER = os.path.join(os.getcwd(), f"uploads/{date_create}/fonts")
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)

            if "template_image" not in request.files:
                return Response(
                    message="Không tìm thấy template_image",
                    status=400,
                ).to_dict()

            if "font" not in request.files:
                return Response(
                    message="Không tìm thấy font",
                    status=400,
                ).to_dict()
            font = request.files["font"]
            font_name = font.filename
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex

            font_ext = font_name.split(".")[-1]
            font_save_name = f"{timestamp}_{unique_id}.{font_ext}"
            font_path = f"{UPLOAD_FOLDER}/{font_save_name}"
            with open(font_path, "wb") as font_file:
                font_file.write(font.read())

            template_image = ImageMaker().save_image_from_request(
                request.files["template_image"]
            )

            template_name = args.get("template_name", "")
            template_code = args.get("template_code", "")
            font_size = args.get("font_size", "0")
            main_text_color = args.get("main_text_color")
            text_color = args.get("text_color")
            stroke_color = args.get("stroke_color")
            stroke_width = args.get("stroke_width")
            text_shadow = args.get("text_shadow")
            text_align = args.get("text_align")
            text_position = args.get("text_position")
            text_position_x = args.get("text_position_x")
            text_position_y = args.get("text_position_y")
            background = args.get("background")
            background_color = args.get("background_color")
            background_image = args.get("background_image")
            padding = args.get("padding")
            margin = args.get("margin")
            sort = args.get("sort")
            type = args.get("type", "")
            image_template = ImageTemplateService.create_image_template(
                template_name=template_name,
                template_code=template_code,
                template_image=template_image,
                font=font_name,
                font_path=font_path,
                font_size=int(font_size),
                main_text_color=main_text_color,
                text_color=text_color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                text_shadow=text_shadow,
                text_align=text_align,
                text_position=text_position,
                text_position_x=text_position_x,
                text_position_y=text_position_y,
                background=background,
                background_color=background_color,
                background_image=background_image,
                padding=padding,
                margin=margin,
                type=type,
                sort=sort,
                created_by=current_user.id,
            )
            return Response(
                data=image_template.to_json(),
                message="Tạo image_template thành công",
            ).to_dict()
        except Exception as e:
            print(e)
            traceback.print_exc()
            return Response(
                message="Tạo image_template thất bại",
                status=400,
            ).to_dict()


@ns.route("/update")
class APIUpdateImageTemplate(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "id": {"type": "string"},
            "template_name": {"type": "string"},
            "template_code": {"type": "string"},
            "font_size": {"type": "string"},
            "main_text_color": {"type": "string"},
            "text_color": {"type": "string"},
            "stroke_color": {"type": "string"},
            "stroke_width": {"type": "string"},
            "text_shadow": {"type": "string"},
            "text_align": {"type": "string"},
            "text_position": {"type": "string"},
            "text_position_x": {"type": "string"},
            "text_position_y": {"type": "string"},
            "background": {"type": "string"},
            "background_color": {"type": "string"},
            "background_image": {"type": "string"},
            "padding": {"type": "string"},
            "margin": {"type": "string"},
            "type": {"type": "string"},
        },
        required=["id"],
    )
    def put(self, args):
        id = args.get("id", "")
        current_template = ImageTemplateService.find_image_template(id)
        if not current_template:
            return Response(
                message="Không tìm thấy image_template",
                status=400,
            ).to_dict()

        date_create = datetime.now().strftime("%Y_%m_%d")
        UPLOAD_FOLDER = os.path.join(os.getcwd(), f"uploads/{date_create}/fonts")
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        if "template_image" in request.files:
            template_image = ImageMaker().save_image_from_request(
                request.files["template_image"]
            )
            args["template_image"] = template_image
        if "font" in request.files:
            font = request.files["font"]
            font_name = font.filename
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex

            font_ext = font_name.split(".")[-1]
            font_save_name = f"{timestamp}_{unique_id}.{font_ext}"
            font_path = f"{UPLOAD_FOLDER}/{font_save_name}"
            with open(font_path, "wb") as font_file:
                font_file.write(font.read())
            args["font"] = font_name
            args["font_path"] = font_path

        image_template = ImageTemplateService.update_image_template(id, **args)
        if not image_template:
            return Response(
                message="Cập nhật image_template thất bại",
                status=400,
            ).to_dict()
        if "template_image" in args:
            if os.path.exists(current_template.template_image):
                os.remove(current_template.template_image)
        if "font_path" in args:
            if os.path.exists(current_template.font_path):
                os.remove(current_template.font_path)
        return Response(
            data=image_template,
            message="Tạo image_template thành công",
        ).to_dict()
