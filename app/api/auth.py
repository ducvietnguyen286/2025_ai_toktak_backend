# coding: utf8
import traceback
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response
from app.services.user import UserService
from app.services.referral_service import ReferralService
from datetime import datetime

from app.lib.logger import log_reset_user_message, logger
import json

from app.services.auth import AuthService
from app.services.notification import NotificationServices
from app.lib.string import get_level_images 
import const
from app.extensions import redis_client
from app.services.payment_services import PaymentService

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
        if not user:
            return Response(
                code=201,
                message="비밀번호가 정확하지 않습니다.",
            ).to_dict()
        if user and user.deleted_at and (datetime.now() - user.deleted_at).days <= 30:
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
            "referral_code": {"type": ["string", "null"]},
        },
        required=["provider", "access_token"],
    )
    def post(self, args):
        try:
            provider = args.get("provider", "")
            access_token = args.get("access_token", "")
            person_id = args.get("person_id", "")
            referral_code = args.get("referral_code", "")

            if referral_code != "":
                user_referal_detail = UserService.find_user_by_referral_code(
                    referral_code
                )
                if not user_referal_detail:
                    return Response(
                        message="입력하신 URL을 다시 한 번 확인해 주세요. 😊",
                        data={
                            "error_message_title": "⚠️ 초대하기 URL에 문제가 있어요!",
                            "error_message": "입력하신 URL을 다시 한 번 확인해 주세요. 😊",
                            "referral_code": referral_code,
                        },
                        code=202,
                    ).to_dict()

            user, new_user_referral_code, is_new_user = AuthService.social_login(
                provider=provider,
                access_token=access_token,
                person_id=person_id,
                referral_code=referral_code,
            )

            if user.deleted_at and (datetime.now() - user.deleted_at).days <= 30:
                return Response(
                    message="시스템에 로그인해주세요.",
                    data={
                        "error_message_title": "⚠️ 현재는 재가입할 수 없어요!",
                        "error_message": "🚫 탈퇴하신 계정은 30일간 재가입하실 수 없습니다.",
                    },
                    code=201,
                ).to_dict()

            tokens = AuthService.generate_token(user)
            tokens.update(
                {
                    "type": "Bearer",
                    "expires_in": 7200,
                    "new_user_referral_code": new_user_referral_code,
                    "is_new_user": is_new_user,
                }
            )

            return Response(
                data=tokens,
                message="Đăng nhập bằng mạng xã hội thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.exception(f"social-login : {e}")
            return Response(
                data=None, message=f"Lỗi hệ thống: {str(e)}", status=500
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
            user_login_id = AuthService.get_user_id()
            user_login = UserService.find_user_with_out_session(user_login_id)
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

            level = user_login.level
            total_link = UserService.get_user_links(user_login.id)

            if level != len(total_link):
                level = len(total_link)
                level_info = get_level_images(level)
                user_login = AuthService.update(
                    user_login.id,
                    level=level,
                    level_info=json.dumps(level_info),
                )

            current_date = datetime.now().date()
            expired_date = (
                user_login.subscription_expired.date()
                if user_login.subscription_expired
                else None
            )
            if expired_date and expired_date < current_date:
                log_reset_user_message(
                    f"Reset User : {user_login.id} {user_login.email}  from {user_login.subscription} expired_date :  {expired_date}  current_date : {current_date}"
                )
                user_login = AuthService.reset_free_user(user_login)
            created_at = user_login.created_at

            subscription_name_display  = UserService.get_subscription_name(user_login.subscription , user_login.id)

            user_dict = user_login._to_json()
            user_dict["subscription_name_display"] = subscription_name_display
            user_dict["subscription_name"] = subscription_name_display['subscription_name']
            user_dict.pop("auth_nice_result", None)
            user_dict.pop("password_certificate", None)

            can_download = AuthService.check_subscription_allowed(
                user_dict["subscription"], created_at
            )
            user_dict["can_download"] = can_download
            
            # PaymentService.auto_renew_subscriptions()
            
            try:
                key_redis = const.REDIS_KEY_TOKTAK.get("user_info_me", "user:me")
                redis_key = f"{key_redis}:{user_login.id}"
                redis_client.setex(redis_key, 86400, json.dumps(user_dict))
            except Exception as e:
                logger.warning(f"Cannot save user to redis: {e}")

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
            "email": {"type": ["string", "null"]},
            "password": {"type": ["string", "null"]},
            "random_string": {"type": ["string", "null"]},
        },
        required=[],
    )
    def post(self, args):
        try:
            email = args.get("email", "")
            password = args.get("password", "")
            random_string = args.get("random_string", "")
            if random_string != "":
                user = AuthService.admin_login_by_password(random_string)
            else:
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
            redis_client.delete(f"toktak:current_user:{user.id}")

            return Response(
                data=tokens,
                message="로그인에 성공했습니다",
            ).to_dict()

        except Exception as e:
            # Log lỗi ra console hoặc file nếu cần
            print(f"[Login Error] {str(e)}")

            return Response(
                code=201,
                message="로그인 중 오류가 발생했습니다. 나중에 다시 시도해 주세요.",
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
        user_login = AuthService.get_current_identity(no_cache=True)
        if not user_login:
            return Response(
                message="시스템에 로그인해주세요.",
                code=201,
            ).to_dict()

        update_data = {}

        message = ""
        if name is not None:
            update_data["name"] = name
            message = f"✏️ 이름이 변경되었습니다. ({user_login.name} → {name})"
        if phone is not None:
            update_data["phone"] = phone
            update_data["is_auth_nice"] = 0
            message = f"📞 연락처가 변경되었습니다. ({user_login.phone} → {phone})"
        if contact is not None:
            update_data["contact"] = contact
            message = f"📞 이름이 변경되었습니다. ({user_login.contact} → {contact})"
        if company_name is not None:
            update_data["company_name"] = company_name
            message = f"🏢 회사명이 변경되었습니다. ({user_login.company_name} → {company_name})"

        if update_data:  # Chỉ update nếu có dữ liệu
            notification = NotificationServices.create_notification(
                notification_type="update_user",
                user_id=user_login.id,
                title=message,
            )

            update_data["updated_at"] = datetime.now()

            user_login = AuthService.update(user_login.id, **update_data)

            user_dict = user_login.to_dict()

            redis_client.set(
                f"toktak:current_user:{user_login.id}",
                json.dumps(user_dict),
                ex=const.REDIS_EXPIRE_TIME,
            )

        return Response(
            data=user_login._to_json(),
            message="Update thông tin thành công",
        ).to_dict()


@ns.route("/user_profile")
class APIUserProfile(Resource):

    @jwt_required()
    def get(self):
        try:
            user_login = AuthService.get_current_identity(no_cache=True)
            if not user_login:
                return Response(
                    message="시스템에 로그인해주세요.",
                    code=201,
                ).to_dict()

            if (
                user_login
                and user_login.deleted_at
                and (datetime.now() - user_login.deleted_at).days <= 30
            ):
                return Response(
                    message="시스템에 로그인해주세요.",
                    data={
                        "error_message": "🚫 탈퇴하신 계정은 30일간 재가입하실 수 없습니다."
                    },
                    code=201,
                ).to_dict()
            level = user_login.level
            total_link = UserService.get_user_links(user_login.id)

            if level != len(total_link):
                level = len(total_link)
                level_info = get_level_images(level)
                user_login = AuthService.update(
                    user_login.id,
                    level=level,
                    level_info=json.dumps(level_info),
                )
            created_at = user_login.created_at
            subscription_name_display = UserService.get_subscription_name(user_login.subscription , user_login.id)
            
            user_histories = UserService.get_all_user_history_by_user_id(user_login.id)
            user_dict = user_login._to_json()
            user_dict["user_histories"] = user_histories
            user_dict["subscription_name_display"] = subscription_name_display
            user_dict["subscription_name"] = subscription_name_display['subscription_name']
            

            user_dict.pop("auth_nice_result", None)
            user_dict.pop("password_certificate", None)
            can_download = AuthService.check_subscription_allowed(
                user_dict["subscription"], created_at
            )
            user_dict["can_download"] = can_download

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

        user_id = AuthService.get_user_id()
        if not user_id:
            return Response(
                message="시스템에 로그인해주세요.",
                code=201,
            ).to_dict()

        AuthService.deleteAccount(user_id)

        redis_client.delete(f"toktak:current_user:{user_id}")

        return Response(
            data={},
            message="계정을 성공적으로 삭제했습니다.",
        ).to_dict()
