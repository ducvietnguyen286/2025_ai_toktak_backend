# coding: utf8
import traceback
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response
from app.services.user import UserService
from datetime import datetime

from app.lib.logger import logger
import json

from app.services.auth import AuthService
from app.services.notification import NotificationServices
from app.lib.string import get_level_images
import const

ns = Namespace(name="auth", description="Auth API")


@ns.route("/login")
class APILogin(Resource):

    @parameters(
        type="object",
        properties={
            "email": {"type": "string"},
            "password": {"type": "string"},
        },
        required=["email", "password"],
    )
    def post(self, args):
        email = args.get("email", "")
        password = args.get("password", "")

        user = AuthService.login(email, password)
        if user.deleted_at and (datetime.now() - user.deleted_at).days <= 30:
            return Response(
                message="시스템에 로그인해주세요.",
                data={
                    "error_message": "🚫 탈퇴하신 계정은 30일간 재가입하실 수 없습니다."
                },
                code=201,
            ).to_dict()

        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
            }
        )

        return Response(
            data=tokens,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/social-login")
class APISocialLogin(Resource):

    @parameters(
        type="object",
        properties={
            "provider": {"type": "string", "enum": ["FACEBOOK", "GOOGLE"]},
            "access_token": {"type": "string"},
            "person_id": {"type": "string"},
        },
        required=["provider", "access_token"],
    )
    def post(self, args):
        provider = args.get("provider", "")
        access_token = args.get("access_token", "")
        person_id = args.get("person_id", "")

        user = AuthService.social_login(
            provider=provider,
            access_token=access_token,
            person_id=person_id,
        )

        if user.deleted_at and (datetime.now() - user.deleted_at).days <= 30:
            return Response(
                message="시스템에 로그인해주세요.",
                data={
                    "error_message": "🚫 탈퇴하신 계정은 30일간 재가입하실 수 없습니다."
                },
                code=201,
            ).to_dict()

        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
            }
        )

        return Response(
            data=tokens,
            message="Đăng nhập bằng mạng xã hội thành công",
        ).to_dict()


@ns.route("/register")
class APIRegister(Resource):

    @parameters(
        type="object",
        properties={
            "username": {"type": "string"},
            "email": {"type": "string"},
            "password": {"type": "string"},
        },
        required=["email", "password"],
    )
    def post(self, args):
        username = args.get("username", "")
        email = args.get("email", "")
        password = args.get("password", "")
        level = 0
        level_info = get_level_images(level)

        user = AuthService.register(email, password, username, json.dumps(level_info))
        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
                "user": user._to_json(),
            }
        )

        return Response(
            data=tokens,
            message="Đăng ký thành công",
        ).to_dict()


@ns.route("/refresh-token")
class APIRefreshToken(Resource):

    @jwt_required(refresh=True)
    def post(self):
        tokens = AuthService.refresh_token()
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
            }
        )

        return Response(
            data=tokens,
            message="Lấy token mới thành công",
        ).to_dict()


@ns.route("/me")
class APIMe(Resource):

    @jwt_required()
    def get(self):
        try:
            user_login = AuthService.get_current_identity()
            if not user_login:
                return Response(
                    status=401,
                    message="Can't User login",
                ).to_dict()

            if (
                user_login.deleted_at
                and (datetime.now() - user_login.deleted_at).days <= 30
            ):
                return Response(
                    message="시스템에 로그인해주세요.",
                    data={
                        "error_message": "🚫 탈퇴하신 계정은 30일간 재가입하실 수 없습니다."
                    },
                    code=201,
                ).to_dict()

            user_login = AuthService.update(
                user_login.id,
                last_activated=datetime.now(),
            )

            current_datetime = datetime.now()
            if (
                user_login.subscription_expired
                and user_login.subscription_expired <= current_datetime
            ):
                user_login = AuthService.update(
                    user_login.id,
                    subscription="FREE",
                    subscription_expired=None,
                    batch_total=const.LIMIT_BATCH["FREE"],
                    batch_remain=const.LIMIT_BATCH["FREE"],
                    batch_sns_total=0,
                    batch_sns_remain=0,
                    batch_no_limit_sns=0,
                )

            subscription_name = user_login.subscription
            if user_login.subscription == "FREE":
                subscription_name = "무료 체험"
            elif user_login.subscription == "STANDARD":
                subscription_name = "기업형 스탠다드 플랜"

            first_coupon, latest_coupon = UserService.get_latest_coupon(user_login.id)

            start_used = None
            if first_coupon:
                start_used = first_coupon.get("used_at")
            elif latest_coupon:
                start_used = latest_coupon.get("used_at")

            last_used = latest_coupon.get("expired_at") if latest_coupon else None

            used_date_range = ""
            if start_used and last_used:
                start_used = datetime.strptime(start_used, "%Y-%m-%dT%H:%M:%SZ")
                last_used = datetime.strptime(last_used, "%Y-%m-%dT%H:%M:%SZ")
                used_date_range = f"{start_used.strftime('%Y.%m.%d')}~{last_used.strftime('%Y.%m.%d')}"

            user_dict = user_login._to_json()
            user_dict["subscription_name"] = subscription_name
            user_dict["latest_coupon"] = latest_coupon
            user_dict["used_date_range"] = used_date_range

            return Response(
                data=user_dict,
                message="사용자 정보를 성공적으로 가져왔습니다.",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.exception(f"APIMe: {e}")
            return Response(
                data={},
                message="Đã xảy ra lỗi trong quá trình xử lý",
                code=500,
            ).to_dict()


@ns.route("/login_by_input")
class APILoginByInput(Resource):

    @parameters(
        type="object",
        properties={
            "email": {"type": "string"},
            "password": {"type": "string"},
        },
        required=["email", "password"],
    )
    def post(self, args):
        email = args.get("email", "")
        password = args.get("password", "")

        user = AuthService.login(email, password)
        if not user:
            return Response(
                code=201,
                message="비밀번호가 정확하지 않습니다.",
            ).to_dict()

        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
                "user": user._to_json(),
            }
        )

        return Response(
            data=tokens,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/update_user")
class APIMeUpdate(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "name": {"type": "string"},
            "phone": {"type": "string"},
            "contact": {"type": "string"},
            "company_name": {"type": "string"},
        },
        required=[],
    )
    def post(self, args):
        name = args.get("name")
        phone = args.get("phone")
        contact = args.get("contact")
        company_name = args.get("company_name")
        user_login = AuthService.get_current_identity()

        update_data = {}

        message = ""
        if name is not None:
            update_data["name"] = name
            message = f"✏️ 이름이 변경되었습니다. ({user_login.name} → {name})"
        if phone is not None:
            update_data["phone"] = phone
            message = f"📞 연락처가 변경되었습니다. ({user_login.phone} → {phone})"
        if contact is not None:
            update_data["contact"] = contact
            message = f"📞 이름이 변경되었습니다. ({user_login.contact} → {contact})"
        if company_name is not None:
            update_data["company_name"] = company_name
            message = f"🏢 회사명이 변경되었습니다. ({user_login.company_name} → {company_name})"

        if update_data:  # Chỉ update nếu có dữ liệu
            NotificationServices.create_notification(
                user_id=user_login.id,
                title=message,
            )
            update_data["updated_at"] = datetime.now()

            user_login = AuthService.update(user_login.id, **update_data)

        return Response(
            data=user_login._to_json(),
            message="Update thông tin thành công",
        ).to_dict()


@ns.route("/user_profile")
class APIUserProfile(Resource):

    @jwt_required()
    def get(self):
        try:
            user = AuthService.get_current_identity()
            if user.deleted_at and (datetime.now() - user.deleted_at).days <= 30:
                return Response(
                    message="시스템에 로그인해주세요.",
                    data={
                        "error_message": "🚫 탈퇴하신 계정은 30일간 재가입하실 수 없습니다."
                    },
                    code=201,
                ).to_dict()
            level = user.level
            total_link = UserService.get_user_links(user.id)

            if level != len(total_link):
                level = len(total_link)
                level_info = get_level_images(level)
                user = AuthService.update(
                    user.id,
                    level=level,
                    level_info=json.dumps(level_info),
                )
            current_datetime = datetime.now()
            if (
                user.subscription_expired
                and user.subscription_expired <= current_datetime
            ):
                user = AuthService.update(
                    user.id,
                    subscription="FREE",
                    subscription_expired=None,
                    batch_total=const.LIMIT_BATCH["FREE"],
                    batch_remain=const.LIMIT_BATCH["FREE"],
                    batch_sns_total=0,
                    batch_sns_remain=0,
                    batch_no_limit_sns=0,
                )

            batch_remain = user.batch_remain

            latest_coupon, first_coupon, coupons = UserService.get_user_coupons(user.id)
            subscription_name = user.subscription
            if user.subscription == "FREE":
                subscription_name = "무료 체험"
            elif user.subscription == "STANDARD":
                subscription_name = "기업형 스탠다드 플랜"

            result_coupons = []

            for coupon in coupons:
                coupon_value = coupon.get("value", 0)
                coupon_remain = (
                    coupon_value
                    if batch_remain > coupon_value
                    else batch_remain - coupon_value
                )
                if coupon_remain < 0:
                    coupon_remain = 0
                coupon["remain"] = coupon_remain
                result_coupons.append(coupon)

            start_used = None
            if first_coupon:
                start_used = first_coupon.get("used_at")
            elif latest_coupon:
                start_used = latest_coupon.get("used_at")

            last_used = latest_coupon.get("expired_at") if latest_coupon else None

            used_date_range = ""
            if start_used and last_used:
                start_used = datetime.strptime(start_used, "%Y-%m-%dT%H:%M:%SZ")
                last_used = datetime.strptime(last_used, "%Y-%m-%dT%H:%M:%SZ")
                used_date_range = f"{start_used.strftime('%Y.%m.%d')}~{last_used.strftime('%Y.%m.%d')}"

            user_dict = user._to_json()
            user_dict["subscription_name"] = subscription_name
            user_dict["coupons"] = result_coupons
            user_dict["latest_coupon"] = latest_coupon
            user_dict["used_date_range"] = used_date_range

            return Response(
                data=user_dict,
                message="Lấy thông tin người dùng thành công",
            ).to_dict()

        except Exception as e:
            traceback.print_exc()
            logger.exception(f"APIUserProfile: {e}")

            return Response(
                data={},
                message="Đã xảy ra lỗi trong quá trình xử lý",
                code=500,
            ).to_dict()


@ns.route("/delete_account")
class APIDeleteAccount(Resource):
    @jwt_required()
    def post(self):

        user_login = AuthService.get_current_identity()
        if not user_login:
            return Response(
                message="시스템에 로그인해주세요.",
                code=201,
            ).to_dict()

        AuthService.deleteAccount(user_login.id)

        return Response(
            data={},
            message="계정을 성공적으로 삭제했습니다.",
        ).to_dict()
