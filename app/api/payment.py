from flask import request
from flask_restx import Resource, Namespace
from flask_jwt_extended import jwt_required, get_jwt_identity

import json
from app.services.auth import AuthService
from app.services.payment_services import PaymentService
from app.services.notification import NotificationServices
from app.services.post import PostService
from app.lib.response import Response
from app.lib.logger import logger
from const import PACKAGE_CONFIG
ns = Namespace("payment", description="Payment API")


@ns.route("/create_new_payment")
class APICreateNewPayment(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        package_name = data.get("package_name")
        
        PACKAGE_CHOICES = list(PACKAGE_CONFIG.keys())

        if package_name not in PACKAGE_CHOICES:
            return Response(
                message="유효하지 않은 상품입니다.",
                code=201,
            ).to_dict()

        current_user = AuthService.get_current_identity()
        user_id_login = current_user.id
        # Kiểm tra xem đã đăng kí gói nào chưa
        active = PaymentService.has_active_subscription(user_id_login)
        if active:
            # Đã đăng kí gói nào chưa
            # Không cho downgrade
            if not PaymentService.can_upgrade(active.package_name, package_name):
                message = f"{active.package_name}에서 {package_name}(으)로 하향 변경할 수 없습니다."
                NotificationServices.create_notification(
                    user_id=user_id_login,
                    title=message,
                    notification_type="payment",
                )
                return Response(message=message, code=201).to_dict()

            # Kiểm tra có được phép upgrade không
            if not PaymentService.process_subscription_request(
                current_user, package_name
            ):
                message = f"이전 요금제가 아직 유효하기 때문에 {package_name} 요금제로 업그레이드하실 수 없습니다."
                NotificationServices.create_notification(
                    user_id=user_id_login,
                    title=message,
                    notification_type="payment",
                )
                return Response(message=message, code=201).to_dict()

            # ✅ Được phép upgrade
            message = f"{active.package_name} 요금제를 {package_name} 요금제로 성공적으로 업그레이드했습니다."
            payment_upgrade = PaymentService.upgrade_package(current_user, package_name)
            NotificationServices.create_notification(
                user_id=user_id_login,
                title=message,
                notification_type="payment",
            )
            return Response(
                message=message,
                data={"payment": payment_upgrade._to_json()},
                code=200,
            ).to_dict()

        # Đăng kí gói mới
        payment = PaymentService.create_new_payment(current_user, package_name)
        message = f"{package_name} 요금제가 성공적으로 등록되었습니다."
        NotificationServices.create_notification(
            user_id=user_id_login,
            title=message,
            notification_type="payment",
        )
        return Response(
            message=message,
            data={"payment": payment._to_json()},
            code=200,
        ).to_dict()
