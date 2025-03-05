# coding: utf8
import json
from flask_restx import Namespace, Resource
from flask import request
from app.services.video_service import VideoService
from app.services.post import PostService
from datetime import datetime
from app.lib.logger import logger
from app.extensions import db
from app.models.setting import Setting
from app.lib.logger import logger
from app.lib.response import Response
from app.models.request_log import RequestLog

ns = Namespace(name="setting", description="Setting API")


@ns.route("/all")
class AllSetting(Resource):
    def get(self):
        settings = Setting.query.all()
        settings_dict = {
            setting.setting_name: setting.setting_value for setting in settings
        }

        return Response(
            data=settings_dict,
            message="Get All setting",
        ).to_dict()


@ns.route("/update_setting")
class APIUpdateSetting(Resource):
    def post(self):
        try:
            data = request.get_json()

            # Kiểm tra dữ liệu gửi lên
            if not isinstance(data, dict):
                return {"message": "Dữ liệu phải là dictionary"}, 400
            for key, value in data.items():
                print(key)
                print(value)
                setting = Setting.query.filter_by(setting_name=key).first()
                if setting:
                    setting.setting_value = value  # Cập nhật giá trị mới
                else:
                    # Nếu chưa có thì tạo mới
                    new_setting = Setting(setting_name=key, setting_value=value)
                    db.session.add(new_setting)
            db.session.commit()  # Lưu thay đổi vào DB

            settings = Setting.query.all()
            settings_dict = {
                setting.setting_name: setting.setting_value for setting in settings
            }

            return Response(
                data=settings_dict,
                message="Update setting thanh cong",
            ).to_dict()
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Update setting that bai",
                status=400,
            ).to_dict()


@ns.route("/get_logs")
class ApiGetLog(Resource):
    def get(self):
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        print("page", page)
        print("per_page", per_page)

        batches = RequestLog.query.order_by(RequestLog.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "status": True,
            "message": "Success",
            "total": batches.total,
            "page": batches.page,
            "per_page": batches.per_page,
            "total_pages": batches.pages,
            "data": [batch_detail.to_dict() for batch_detail in batches.items],
        }, 200

