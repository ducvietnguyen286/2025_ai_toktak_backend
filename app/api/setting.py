# coding: utf8
import json
from flask_restx import Namespace, Resource
from flask import request
from app.services.video_service import VideoService
from app.services.post import PostService
from datetime import datetime
from app.lib.logger import logger
from app.extensions import db, redis_client
from app.models.setting import Setting
from app.lib.logger import logger
from app.lib.response import Response
from app.models.request_log import RequestLog
from app.services.setting import SettingService
import const

from app.services.admin_notification import AdminNotificationService

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
            SettingService.clear_settings_cache()
            SettingService.get_settings() 
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


@ns.route("/get_config_x")
class GetConfig(Resource):
    def get(self):
        setting = Setting.query.filter_by(setting_name="TWITTER_CLIENT_ID").first()

        return Response(
            data={"TWITTER_CLIENT_ID": setting.setting_value},
            message="Get  setting",
        ).to_dict()


@ns.route("/get_public_config")
class GetPublicConfig(Resource):
    def get(self):
        remote_ip = get_real_ip()
        redis_key = f"{const.REDIS_KEY_SETTING_HOME}:{remote_ip}"

        cache_data = redis_client.get(redis_key)
        if cache_data:
            # ✅ Lấy toàn bộ dict đã cache (bao gồm cả notification_detail)
            full_dict = json.loads(cache_data)
        else:
            # ✅ Truy vấn DB lấy setting
            settings = Setting.query.filter_by(status=0).all()
            settings_dict = {
                setting.setting_name: setting.setting_value for setting in settings
            }

            # ✅ Xử lý bảo trì
            ALLOWED_IPS = json.loads(settings_dict.get("ALLOWED_IPS", "[]"))
            if settings_dict.get("IS_MAINTANCE") == "1" and remote_ip in ALLOWED_IPS:
                settings_dict["IS_MAINTANCE"] = "0"
            settings_dict.pop("ALLOWED_IPS", None)

            # ✅ Lấy notification
            notification_obj = AdminNotificationService.get_first_active_notification()
            notification_detail = (
                notification_obj.to_dict() if notification_obj else {}
            )

            # ✅ Gộp lại toàn bộ dict
            full_dict = settings_dict.copy()
            full_dict["notification_detail"] = notification_detail

            redis_client.setex(redis_key, 3600, json.dumps(full_dict))

        return Response(
            data=full_dict,
            message="Get Public setting",
        ).to_dict()


@ns.route("/ping")
class APIPingStatus(Resource):
    def get(self):

        return Response(
            data={},
            message="Ping Oke",
        ).to_dict()


def get_real_ip():
    # Ưu tiên Cloudflare header
    ip = request.headers.get("CF-Connecting-IP")
    if not ip:
        # Nếu không có, lấy từ chuỗi X-Forwarded-For
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        # Trường hợp X-Forwarded-For có dạng "client, proxy1, proxy2"
        if "," in ip:
            ip = ip.split(",")[0].strip()
    return ip
