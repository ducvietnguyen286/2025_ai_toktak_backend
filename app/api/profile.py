# coding: utf8
import os
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters, admin_required
from app.lib.response import Response
from app.services.user import UserService
from datetime import datetime

from app.lib.logger import logger
import json
from flask import request
from app.services.auth import AuthService
from app.services.notification import NotificationServices
from app.lib.string import generate_random_nick_name
import const

from app.models.notification import Notification
from app.ais.chatgpt import (
    translate_notifications_batch,
)
from sqlalchemy import or_


from app.services.profileservices import ProfileServices

ns = Namespace(name="profile", description="Member profile operations")

UPLOAD_FOLDER = "static/voice/avatars"


@ns.route("/profile_detail")
class MemberProfileAPI(Resource):
    @jwt_required()
    def get(self):
        try:

            current_user = AuthService.get_current_identity()
            profile = ProfileServices.profile_by_user_id(current_user.id)
            if not profile:
                nick_name = generate_random_nick_name(current_user.email)
                design_settings = {
                    "background_color": "#E8F0FE",
                    "main_text_color": "#0A1929",
                    "sub_text_color": "#6B7F99",
                    "notice_color": "#6B7F99",
                    "notice_background_color": "#FFFFFF",
                    "product_background_color": "#FFFFFF",
                    "product_name_color": "#6B7F99",
                    "product_price_color": "#1E4C94",
                    "show_price": 1,
                }
                guide_info = [{"id": i + 1, "is_completed": False} for i in range(10)]
                profile = ProfileServices.create_profile(
                    user_id=current_user.id,
                    nick_name=nick_name,
                    status=0,
                    design_settings=json.dumps(design_settings),
                    guide_info=json.dumps(guide_info),
                )
            return profile.to_dict()
        except Exception as e:
            logger.error(f"Exception: 프로필이 존재하지 않습니다.  :  {str(e)}")
            return Response(
                message="프로필이 존재하지 않습니다.",
                code=201,
            ).to_dict()


@ns.route("/profile_update")
class MemberProfileUpdateAPI(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = AuthService.get_user_id()
            form = request.form
            file = request.files.get("member_avatar")
            file_background = request.files.get("member_background")

            # Lấy dữ liệu text fields
            data_update = {
                "member_name": form.get("member_name"),
                "nick_name": form.get("nick_name"),
                "description": form.get("description"),
                "content": form.get("content"),
                "member_address": form.get("member_address"),
                "social_is_spotify": form.get("social_is_spotify"),
                "social_spotify_url": form.get("social_spotify_url"),
                "social_is_thread": form.get("social_is_thread"),
                "social_thread_url": form.get("social_thread_url"),
                "social_is_youtube": form.get("social_is_youtube"),
                "social_youtube_url": form.get("social_youtube_url"),
                "social_is_x": form.get("social_is_x"),
                "social_x_url": form.get("social_x_url"),
                "social_is_instagram": form.get("social_is_instagram"),
                "social_instagram_url": form.get("social_instagram_url"),
                "social_is_tiktok": form.get("social_is_tiktok"),
                "social_tiktok_url": form.get("social_tiktok_url"),
                "social_is_facebook": form.get("social_is_facebook"),
                "social_facebook_url": form.get("social_facebook_url"),
                "status": 2,
            }

            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
            # Nếu có file ảnh => lưu ảnh
            if file:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = (
                    f"{user_id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
                )
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                output_caption_file = path.replace("static/", "").replace("\\", "/")
                product_image_path = f"{current_domain}/{output_caption_file}"

                data_update["member_avatar"] = product_image_path

            if file_background:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = f"{user_id}_{int(datetime.utcnow().timestamp())}_{file_background.filename}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                file_background.save(path)
                output_caption_file = path.replace("static/", "").replace("\\", "/")
                member_background_path = f"{current_domain}/{output_caption_file}"

                data_update["member_background"] = member_background_path
            profile = ProfileServices.update_profile_by_user_id(user_id, **data_update)
            if not profile:
                return Response(
                    message="프로필이 존재하지 않습니다", code=201
                ).to_dict()

            return Response(
                data=profile.to_dict(), message="업데이트에 성공했습니다."
            ).to_dict()

        except Exception as e:
            logger.error(f"Update profile error: {str(e)}")
            return Response(
                message="프로필 업데이트 중 오류가 발생했습니다.", code=201
            ).to_dict()


@ns.route("/status_update")
class MemberProfileStatusUpdateAPI(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = AuthService.get_user_id()

            profile_member = ProfileServices.profile_by_user_id(user_id)
            if not profile_member:
                return Response(
                    message="상태를 업데이트하는 중에 문제가 발생했습니다.", code=201
                ).to_dict()

            status = profile_member.status
            if status != 0:
                return Response(
                    message="상태를 업데이트하는 중에 문제가 발생했습니다.", code=201
                ).to_dict()
            else:
                data_update = {
                    "status": 1,
                }
                profile = ProfileServices.update_profile_by_user_id(
                    user_id, **data_update
                )
            return Response(
                data=profile.to_dict(), message="상태가 성공적으로 업데이트되었습니다."
            ).to_dict()

        except Exception as e:
            logger.error(f"Update profile error: {str(e)}")
            return Response(
                message="상태를 업데이트하는 중에 문제가 발생했습니다.", code=201
            ).to_dict()


@ns.route("/check_nick_name")
class CheckNickNameAPI(Resource):
    @jwt_required()
    def get(self):
        try:
            user_id = AuthService.get_user_id()
            nick_name = request.args.get("nick_name", "").strip()

            if not nick_name:
                return Response(message="Thiếu nick_name", code=201).to_dict()

            # Tìm người khác có nick_name giống vậy (không phải chính user)
            existed = ProfileServices.find_by_nick_name_exclude_user(
                nick_name, exclude_user_id=user_id
            )

            if existed:
                return Response(
                    message="닉네임이 이미 사용되었습니다.", code=201
                ).to_dict()

            return Response(message="유효한 닉네임입니다.").to_dict()
        except Exception as e:
            logger.error(f"[check_nick_name] Error: {str(e)}")
            return Response(
                message="닉네임 확인 중 오류가 발생했습니다.", code=201
            ).to_dict()


@ns.route("/by_nick_name")
class GetProfileByNickNameAPI(Resource):
    def get(self):
        try:
            nick_name = request.args.get("nick_name", "").strip()
            if not nick_name:
                return Response(message="Thiếu nick_name", code=201).to_dict()

            profile = ProfileServices.find_by_nick_name(nick_name)
            if not profile:
                return Response(
                    message="프로필을 찾을 수 없습니다.", code=201
                ).to_dict()

            return Response(data=profile.to_dict()).to_dict()
        except Exception as e:
            logger.error(f"[by_nick_name] Error: {str(e)}")
            return Response(message="Lỗi khi lấy thông tin profile", code=201).to_dict()


@ns.route("/profile_design_settings")
class MemberProfileDesignSettingsUpdateAPI(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = AuthService.get_user_id()
            data_form = request.get_json()
            data_update = {}

            print(data_form)

            data_update["design_settings"] = json.dumps(data_form, ensure_ascii=False)

            profile = ProfileServices.update_profile_by_user_id(user_id, **data_update)
            if not profile:
                return Response(
                    message="디자인 설정 정보 업데이트에 실패했습니다.", code=201
                ).to_dict()

            return Response(
                data=profile.to_dict(), message="프로필이 존재하지 않습니다."
            ).to_dict()

        except Exception as e:
            logger.error(f"Update profile error: {str(e)}")
            return Response(
                message="디자인 설정 정보 업데이트에 실패했습니다.", code=201
            ).to_dict()


@ns.route("/view/<string:user_name>")
class ViewMemberProfileAPI(Resource):
    def get(self, user_name):
        try:
            profile = ProfileServices.find_by_nick_name(user_name)
            if not profile:
                return Response(
                    message="디자인 설정 정보 업데이트에 실패했습니다.", code=201
                ).to_dict()

            return Response(data=profile.to_dict()).to_dict()

            return profile.to_dict()
        except Exception as e:
            logger.error(f"Exception: 프로필이 존재하지 않습니다.  :  {str(e)}")
            return Response(
                message="프로필이 존재하지 않습니다.",
                code=201,
            ).to_dict()
