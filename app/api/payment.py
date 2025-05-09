from flask import request
from flask_restx import Resource, Namespace
from flask_jwt_extended import jwt_required, get_jwt_identity

import json
from app.services.auth import AuthService
from app.services.payment_services import PaymentService
from app.services.post import PostService
from app.lib.response import Response
from app.lib.logger import logger

ns = Namespace("payment", description="Payment API")


@ns.route("/create_new_payment")
class APICreateNewPayment(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        package_name = data.get("package_name")

        user_id_login = 0
        current_user = AuthService.get_current_identity() or None
        user_id_login = current_user.id

        active = PaymentService.has_active_subscription(user_id_login)
        if active:
            # Nếu vẫn còn hạn, kiểm tra nâng cấp
            if not PaymentService.can_upgrade(active.package_name, package_name):

                return Response(
                    message=f"Cannot downgrade from {active.package_name} to {package_name}.",
                    code=201,
                ).to_dict()

            # Xử lý nâng cấp
            payment = PaymentService.upgrade_package(user_id_login, package_name)

            return Response(
                message=f"User already has an active subscription {active.package_name}",
                code=201,
            ).to_dict()

        if package_name not in ["BASIC", "STANDARD", "BUSINESS"]:
            return Response(
                message="Invalid package",
                code=201,
            ).to_dict()

        payment = PaymentService.create_new_payment(user_id_login, package_name)
        return Response(
            message="Payment created",
            data={"payment": payment._to_json()},
            code=200,
        ).to_dict()


@ns.route("/upgrade_package")
class APIUpgradePackage(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        package_name = data.get("package_name")
        user_id_login = 0
        current_user = AuthService.get_current_identity() or None
        user_id_login = current_user.id

        if package_name not in ["BASIC", "STANDARD", "BUSINESS"]:
            return Response(
                message="Invalid package",
                code=201,
            ).to_dict()

        payment = PaymentService.upgrade_package(user_id_login, package_name)
        return Response(
            message="Package upgraded",
            data={"payment": payment._to_json()},
            code=200,
        ).to_dict()
