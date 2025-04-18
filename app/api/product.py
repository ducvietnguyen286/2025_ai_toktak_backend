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
from app.lib.string import get_level_images
import const

from app.services.profileservices import ProfileServices

ns = Namespace(name="profile", description="Member profile operations")

UPLOAD_FOLDER = "static/uploads/avatars"


@ns.route("/profile_detail")
class MemberProfileAPI(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user = AuthService.get_current_identity()
            profile = ProfileServices.profile_by_user_id(current_user.id)
            if not profile:
                profile = ProfileServices.create_profile(user_id=current_user.id)
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
    def put(self):
        try:
            current_user = AuthService.get_current_identity()
            form = request.form
            file = request.files.get("avatar")

            # Lấy dữ liệu text fields
            data = {
                "member_name": form.get("member_name"),
                "nick_name": form.get("nick_name"),
                "description": form.get("description"),
                "content": form.get("content"),
                "member_address": form.get("member_address"),
                "design_settings": form.get("design_settings"),
            }

            # Nếu có file ảnh => lưu ảnh
            if file:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                data["member_avatar"] = f"/{path}"

            profile = ProfileServices.update_profile(
                current_user.id, **{k: v for k, v in data.items() if v is not None}
            )
            if not profile:
                return Response(
                    message="프로필이 존재하지 않습니다", code=404
                ).to_dict()

            return Response(
                data=profile.to_dict(), message="업데이트에 성공했습니다."
            ).to_dict()

        except Exception as e:
            logger.error(f"Update profile error: {str(e)}")
            return Response(
                message="프로필 업데이트 중 오류가 발생했습니다.", code=500
            ).to_dict()


@ns.route("/check_nick_name")
class CheckNickNameAPI(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user = AuthService.get_current_identity()
            nick_name = request.args.get("nick_name", "").strip()

            if not nick_name:
                return Response(message="Thiếu nick_name", code=400).to_dict()

            # Tìm người khác có nick_name giống vậy (không phải chính user)
            existed = ProfileServices.find_by_nick_name_exclude_user(
                nick_name, exclude_user_id=current_user.id
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
                return Response(message="Không tìm thấy profile", code=201).to_dict()

            return Response(data=profile.to_dict()).to_dict()
        except Exception as e:
            logger.error(f"[by_nick_name] Error: {str(e)}")
            return Response(message="Lỗi khi lấy thông tin profile", code=201).to_dict()
