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
            print(data)
            # Danh sách các setting cần cập nhật
            setting_keys = [
                "SHOTSTACK_API_KEY",
                "SHOTSTACK_URL",
                "SHOTSTACK_EMAIL",
                "SHOTSTACK_OWNER_ID",
                "SHOTSTACK_AI_IMAGE",
            ]

            # Kiểm tra dữ liệu gửi lên
            if not isinstance(data, dict):
                return {"message": "Dữ liệu phải là dictionary"}, 400

            # Lặp qua từng key để cập nhật
            for key in setting_keys:
                if key in data:  # Nếu có giá trị trong request
                    setting = Setting.query.filter_by(setting_name=key).first()
                    if setting:
                        setting.setting_value = data[key]  # Cập nhật giá trị mới
                    else:
                        # Nếu chưa có thì tạo mới
                        new_setting = Setting(setting_name=key, setting_value=data[key])
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
