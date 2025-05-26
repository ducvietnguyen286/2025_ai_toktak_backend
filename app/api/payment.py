from flask import request
from flask_restx import Resource, Namespace
from flask_jwt_extended import jwt_required, get_jwt_identity

import json
from app.services.auth import AuthService
from app.services.payment_services import PaymentService
from app.services.notification import NotificationServices
from app.services.user import UserService
from app.decorators import parameters, admin_required
from app.services.post import PostService
from app.lib.response import Response
from app.lib.logger import logger
import const

import datetime
from dateutil.relativedelta import relativedelta

ns = Namespace("payment", description="Payment API")


@ns.route("/create_new_payment")
class APICreateNewPayment(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        package_name = data.get("package_name")
        addon_count = int(data.get("addon_count", 0))

        PACKAGE_CHOICES = list(const.PACKAGE_CONFIG.keys())

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
        addon_payments = []

        # Nếu mua kèm addon (chỉ áp dụng với BASIC)
        if package_name == "BASIC" and addon_count > 0:
            for _ in range(min(addon_count, const.MAX_ADDON_PER_BASIC)):
                addon_payment = PaymentService.create_addon_payment(
                    user_id_login, payment.id
                )
                if addon_payment:
                    addon_payments.append(addon_payment._to_json())

        message = f"{package_name} 요금제가 성공적으로 등록되었습니다."
        if addon_payments:
            message += f" (추가 Addon {len(addon_payments)}개 포함)"

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


@ns.route("/rate-plan")
class APIGetRatePlan(Resource):
    def get(self):

        rate_plan = const.PACKAGE_CONFIG
        rate_plan.pop("INVITE_BASIC", None)
        return Response(
            data=rate_plan,
            code=200,
        ).to_dict()


@ns.route("/buy_addon")
class APICreateAddon(Resource):
    @jwt_required()
    def post(self):
        current_user = AuthService.get_current_identity() or None

        user_id = current_user.id

        data = request.get_json()
        parent_payment_id = data.get("parent_payment_id")
        try:
            payment = PaymentService.create_addon_payment(user_id, parent_payment_id)
            return Response(
                message="Addon payment created",
                data=payment.to_dict(),
                code=200,
            ).to_dict()
        except Exception as e:
            return Response(
                message=str(e),
                data=payment.to_dict(),
                code=201,
            ).to_dict()


@ns.route("/admin/histories")
class APIAdminNotificationHistories(Resource):
    @jwt_required()
    @admin_required()
    def get(self):
        page = request.args.get("page", const.DEFAULT_PAGE, type=int)
        per_page = request.args.get("per_page", const.DEFAULT_PER_PAGE, type=int)
        status = request.args.get("status", const.UPLOADED, type=int)
        type_order = request.args.get("type_order", "", type=str)
        type_post = request.args.get("type_post", "", type=str)
        time_range = request.args.get("time_range", "", type=str)
        type_payment = request.args.get("type_payment", "", type=str)
        search_key = request.args.get("search_key", "", type=str)
        data_search = {
            "page": page,
            "per_page": per_page,
            "status": status,
            "type_order": type_order,
            "type_post": type_post,
            "time_range": time_range,
            "type_payment": type_payment,
            "search_key": search_key,
        }
        billings = PaymentService.get_admin_billings(data_search)
        return {
            "status": True,
            "message": "Success",
            "total": billings.total,
            "page": billings.page,
            "per_page": billings.per_page,
            "total_pages": billings.pages,
            "data": [post.to_dict() for post in billings.items],
        }, 200


@ns.route("/admin/approval")
class APIPaymentApproval(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        payment_id = data.get("payment_id")

        payment = PaymentService.update_payment(payment_id, status="PAID")
        if payment:
            user_id = payment.user_id
            package_name = payment.package_name
            package_data = const.PACKAGE_CONFIG.get(package_name)
            if not package_data:
                return Response(
                    message="유효하지 않은 패키지입니다.", code=201
                ).to_dict()

            subscription_expired = payment.end_date

            data_update = {
                "subscription": package_name,
                "subscription_expired": subscription_expired,
                "batch_total": package_data["batch_total"],
                "batch_remain": package_data["batch_remain"],
                "total_link_active": package_data["total_link_active"],
            }

            UserService.update_user(user_id, **data_update)
            data_user_history = {
                "user_id": user_id,
                "type": "payment",
                "object_id": payment.id,
                "object_start_time": payment.start_date,
                "object_end_time": subscription_expired,
                "title": package_data["pack_name"],
                "description": package_data["pack_description"],
                "value": package_data["batch_total"],
                "num_days": package_data["batch_remain"],
            }
            UserService.create_user_history(**data_user_history)

        message = "승인이 완료되었습니다."
        return Response(
            message=message,
            data={"payment": payment._to_json()},
            code=200,
        ).to_dict()


@ns.route("/addon/price")
class APICalculateAddonPrice(Resource):
    @jwt_required()
    def get(self):
        current_user = AuthService.get_current_identity() or None
        result = PaymentService.calculate_addon_price(current_user.id)
        return Response(
            data=result,
            code=200,
        ).to_dict()


@ns.route("/admin/delete_payment")
class APIDeleteAccount(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "post_ids": {"type": "string"},
        },
        required=["post_ids"],
    )
    def post(self, args):
        try:
            post_ids = args.get("post_ids", "")
            # Chuyển chuỗi post_ids thành list các integer
            if not post_ids:
                return Response(
                    message="No post_ids provided",
                    code=201,
                ).to_dict()

            # Tách chuỗi và convert sang list integer
            id_list = [int(id.strip()) for id in post_ids.split(",")]

            if not id_list:
                return Response(
                    message="Invalid post_ids format",
                    code=201,
                ).to_dict()

            process_delete = PaymentService.deletePayment(id_list)
            if process_delete == 1:
                message = "Delete Payment Success"
            else:
                message = "Delete Payment Fail"

            return Response(
                message=message,
                code=200,
            ).to_dict()

        except Exception as e:
            logger.error(f"Exception: Delete Payment Fail  :  {str(e)}")
            return Response(
                message="Delete Payment Fail",
                code=201,
            ).to_dict()
