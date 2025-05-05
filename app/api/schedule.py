from flask import request
from flask_restx import Resource, Namespace
from flask_jwt_extended import jwt_required, get_jwt_identity

import json
from app.services.auth import AuthService
from app.services.schedule_services import ScheduleService
from app.lib.response import Response
from app.lib.logger import logger

ns = Namespace("schedule", description="Schedule API")


@ns.route("/create_schedule")
class APICreateSchedule(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        is_paid_advertisements = data.get("is_paid_advertisements", 0)
        product_name = data.get("product_name", "")
        is_product_name = data.get("is_product_name", 0)
        purchase_guide = data.get("purchase_guide", "")
        is_purchase_guide = data.get("is_purchase_guide", 0)
        voice_gender = data.get("voice_gender", 0)
        voice_id = data.get("voice_id", 0)
        is_video_hooking = data.get("is_video_hooking", 0)
        is_caption_top = data.get("is_caption_top", 0)
        is_caption_last = data.get("is_caption_last", 0)
        image_template_id = data.get("image_template_id", 0)
        date = data.get("date", None)
        link_sns = data.get("link_sns", None)
        url = data.get("url", None)
        logger.info(data)

        user_id_login = 0
        current_user = AuthService.get_current_identity() or None
        user_id_login = current_user.id

        data_update_template = {
            "is_paid_advertisements": is_paid_advertisements,
            "product_name": product_name,
            "is_product_name": is_product_name,
            "purchase_guide": purchase_guide,
            "is_purchase_guide": is_purchase_guide,
            "voice_gender": voice_gender,
            "voice_id": voice_id,
            "is_video_hooking": is_video_hooking,
            "is_caption_top": is_caption_top,
            "is_caption_last": is_caption_last,
            "image_template_id": image_template_id,
        }

        schedule = ScheduleService.create_schedule(
            user_id=user_id_login,
            url=url,
            date=date,
            link_sns=json.dumps(link_sns),
            template_info=json.dumps(data_update_template),
        )

        return Response(
            message="Schedule created",
            data={"schedule": schedule._to_json()},
            code=200,
        ).to_dict()


@ns.route("/delete_schedule")
class APIDeleteScheduleDetail(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        user_id = get_jwt_identity()
        ids = data.get("ids", [])

        if not ids:
            return {"message": "No IDs provided"}, 400

        ScheduleService.delete_schedules_by_user_id(ids, user_id)
        return Response(
            message="Schedule delete",
            code=200,
        ).to_dict()


@ns.route("/admin_get_schedule")
class APIAdminGetSchedules(Resource):
    @jwt_required()
    def get(self):
        user_id_login = 0
        current_user = AuthService.get_current_identity() or None
        user_id_login = current_user.id

        start = request.args.get("start")
        end = request.args.get("end")
        status = request.args.get("status")
        schedules = ScheduleService.get_schedule_by_user_id(
            start, end, status
        )
        return Response(
            data=schedules,
            message="Schedule List.",
        ).to_dict()
