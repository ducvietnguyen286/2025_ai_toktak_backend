from flask import request
from flask_restx import Resource, Namespace
from flask_jwt_extended import jwt_required, get_jwt_identity

import json
from app.services.auth import AuthService
from app.services.payment_services import PaymentService
from app.services.notification import NotificationServices
from app.services.user import UserService
from app.decorators import parameters, admin_required
from app.lib.response import Response
from app.lib.logger import logger
from dateutil.parser import isoparse
import const
import traceback
import datetime
from dateutil.relativedelta import relativedelta

from app.lib.string import generate_order_id

ns = Namespace("payment", description="Payment API")


@ns.route("/create_new_payment")
class APICreateNewPayment(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        package_name = data.get("package_name")
        addon_count = int(data.get("addon_count", 0))
        message = ""

        PACKAGE_CHOICES = list(const.PACKAGE_CONFIG.keys())

        if package_name not in PACKAGE_CHOICES:
            return Response(
                message="유효하지 않은 상품입니다.",
                code=201,
            ).to_dict()

        current_user = AuthService.get_current_identity()
        user_id_login = current_user.id
        user_subscription = current_user.subscription
        if user_subscription == "FREE":
            message = f"{package_name} 요금제가 성공적으로 등록되었습니다."
        else:
            message = f"{package_name} 요금제가 성공적으로 등록되었습니다."
        # Kiểm tra xem đã đăng kí gói nào chưa
        active = PaymentService.has_active_subscription(user_id_login)
        if active:
            active_status = active.status
            if active_status == "PENDING":
                message = f"{package_name} 패키지를 구매하셨습니다.<br> 서비스 이용을 위해 시스템의 확인을 기다려 주세요."
                message_en = f" You have purchased the {package_name} package. Please wait for system confirmation to start using the service."
                return Response(
                    message=message, message_en=message_en, code=201
                ).to_dict()

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
        payment = PaymentService.create_new_payment(
            current_user, package_name, "PENDING", addon_count
        )

        message = f"{package_name} 요금제가 성공적으로 등록되었습니다."
        if package_name == "BASIC" and addon_count > 0:
            message += f" (추가 Addon {addon_count}개 포함)"

        NotificationServices.create_notification(
            user_id=user_id_login,
            title=message,
            notification_type="payment",
        )

        # PaymentService.confirm_payment()

        return Response(
            message=message,
            data={
                "payment": payment._to_json(),
                "package_name": package_name,
                "addon_count": addon_count,
            },
            code=200,
        ).to_dict()


@ns.route("/calculate_upgrade_price")
class APICalculateUpgradePrice(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        package_name = data.get("package_name")
        addon_count = data.get("addon_count", 0)
        current_user = AuthService.get_current_identity()
        user_id = current_user.id

        result = PaymentService.calculate_upgrade_price(
            user_id, package_name, addon_count
        )
        return Response(
            data=result,
            code=result["code"],
            message=result["message"],
            message_en=result["message_en"],
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
        user_id_login = current_user.id
        data = request.get_json()
        addon_count = int(data.get("addon_count", 0))
        today = datetime.datetime.now().date()
        basic_payment = PaymentService.get_last_payment_basic(user_id_login, today)

        if not basic_payment:
            return Response(
                message="유효한 BASIC 요금제가 없어 애드온을 구매할 수 없습니다.",
                message_en="You don't have any active BASIC plan, so you cannot purchase an addon.",
                code=201,
            ).to_dict()

        total_addon_count = PaymentService.get_total_payment_basic_addon(
            user_id_login, today, basic_payment.id
        )
        max_addon = const.MAX_ADDON_PER_BASIC
        # Mua thêm và đã mua không quá 2
        total_addon_count = total_addon_count + addon_count
        if total_addon_count > max_addon:
            return Response(
                message=f"BASIC 요금제에 대해 최대 {max_addon}개의 애드온을 구매하셨습니다.",
                message_en=f"You have purchased the maximum of {max_addon} addons for the BASIC plan.",
                data={
                    "total_addon_count": total_addon_count,
                    "max_addon": max_addon,
                },
                code=201,
            ).to_dict()

        logger.info(f"addon_count {addon_count}")
        parent_payment_id = basic_payment.id
        try:
            if addon_count > 0:
                order_id = generate_order_id()
                payment = PaymentService.create_addon_payment(
                    user_id_login, parent_payment_id, order_id, addon_count
                )

                for _ in range(min(addon_count, const.MAX_ADDON_PER_BASIC)):
                    payment_detail = PaymentService.create_addon_payment_detail(
                        user_id_login, payment.id
                    )

            return Response(
                message="애드온을 성공적으로 구매하였습니다",
                message_en="Addon payment addon created",
                data={"addon_count": addon_count, "payment": payment._to_json()},
                code=200,
            ).to_dict()
        except Exception as e:
            return Response(
                message=str(e),
                # data=payment.to_dict(),
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

        result = PaymentService.approvalPayment(payment_id)

        return result


@ns.route("/addon/price_check")
class APICalculateAddonPrice(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "addon_count": {"type": ["string", "null"]},
        },
        required=[],
    )
    def get(self, args):
        addon_count = int(args.get("addon_count", 1))

        current_user = AuthService.get_current_identity() or None
        subscription = current_user.subscription
        if subscription == "FREE":
            result = PaymentService.calculate_price_with_addon(
                current_user.id, addon_count
            )
        else:
            result = PaymentService.calculate_addon_price(current_user.id, addon_count)
        return Response(
            data=result,
            code=200,
        ).to_dict()


@ns.route("/delete_pending")
class APIDeletePending(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "payment_id": {"type": "string"},
        },
        required=["payment_id"],
    )
    def post(self, args):
        try:
            return Response(
                message="",
                code=200,
            ).to_dict()

            payment_id = args.get("payment_id", "")

            payment_detail = PaymentService.find_payment(payment_id)
            if not payment_detail:
                return Response(
                    message="결제가 존재하지 않습니다",
                    message_en="Payment does not exist",
                    data={},
                    code=201,
                ).to_dict()

            if payment_detail.status != "PENDING":
                return Response(
                    message="결제를 삭제할 수 없습니다",
                    message_en="Cannot delete payment",
                    data={},
                    code=201,
                ).to_dict()

            id_list = [int(id.strip()) for id in payment_id.split(",")]

            process_delete = PaymentService.deletePaymentPending(id_list)
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


@ns.route("/get_detail")
class APIGetPaymentDetail(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        payment_id = int(data.get("payment_id", 0))
        message = ""
        active = PaymentService.find_payment(payment_id)
        if active:

            return Response(
                message="",
                data={"payment": active._to_json()},
                code=200,
            ).to_dict()

        return Response(
            message=message,
            data={},
            code=201,
        ).to_dict()
 
@ns.route("/confirm")
class APIPaymentConfirm(Resource):
    @jwt_required()
    def post(self):
        try:
            data = request.get_json()
            payment_key = data.get("paymentKey")
            order_id = data.get("orderId")
            amount = data.get("amount")
            message = ""
            payment = PaymentService.find_payment_by_order(order_id)
            payment_id = payment.id
            if not payment:
                return Response(
                    message="결제 정보가 존재하지 않습니다",
                    message_en="Payment does not exist",
                    code=201,
                ).to_dict()

            payment_data, status_code = PaymentService.confirm_payment_toss(
                payment_key, order_id, amount
            )

            payment_data_log = {
                "payment_id": payment.id if payment else None,
                "status_code": status_code,
                "response_json": json.dumps(payment_data, ensure_ascii=False),
            }

            PaymentService.create_payment_log(**payment_data_log)
            logger.info("_------------------------------------payment_data_log")
            logger.info(payment_data_log)
            logger.info(payment_data)

            if status_code == 200:
                # Thanh toán thành công, cập nhật DB
                if payment.status == "PAID":
                    return Response(
                        message="결제가 완료되었습니다",
                        message_en="Payment has been completed",
                        code=201,
                    ).to_dict()

                data_update_payment = {
                    "payment_key": payment_data.get("paymentKey", ""),
                    "method": payment_data.get("method", ""),
                    "approved_at": datetime.datetime.now(),
                    "payment_data": json.dumps(payment_data),
                    "description": f"{payment.description} Tosspayment : 결제가 완료되었습니다",
                }
                logger.info(
                    f"_------------------------------------data_update_payment payment_id {payment_id}"
                )
                logger.info(data_update_payment)

                payment = PaymentService.update_payment(
                    payment_id, **data_update_payment
                )
                logger.info(payment)
                PaymentService.approvalPayment(payment_id)

                return Response(
                    message="Tosspayment 결제가 완료되었습니다",
                    message_en="Payment completed successfully via Tosspayment",
                    data={
                        "payment": payment._to_json(),
                        "paymentKey": payment_data["paymentKey"],
                        "method": payment_data["method"],
                    },
                ).to_dict()

            return Response(
                message=message,
                data={
                    "payment": payment._to_json(),
                    "status": "FAILED",
                    "fail_reason": payment_data.get("message", "Thanh toán thất bại"),
                    "code": payment_data.get("code"),
                },
                code=201,
            ).to_dict()
        except Exception as ex:
            tb_str = traceback.format_exc()
            logger.error(f"[APIPaymentConfirm] Lỗi: {ex}\n{tb_str}")
            return Response(
                message="결제 확인 중 오류가 발생했습니다.",
                message_en="An error occurred during payment confirmation.",
                code=201,
            ).to_dict()


@ns.route("/log/fail")
class APIPaymentLogFail(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        order_id = data.get("orderId")
        payment_key = data.get("paymentKey")
        status_code = data.get("status_code")
        fail_reason = data.get("fail_reason")
        fail_code = data.get("fail_code")

        payment = PaymentService.find_payment_by_order(order_id)
        if not payment:
            return Response(
                message="결제 정보가 존재하지 않습니다",
                message_en="Payment does not exist",
                code=201,
            ).to_dict()

        payment_data_log = {
            "payment_id": payment.id if payment else None,
            "status_code": status_code,
            "response_json": json.dumps(
                {
                    "paymentKey": payment_key,
                    "fail_reason": fail_reason,
                    "code": fail_code,
                },
                ensure_ascii=False,
            ),
        }

        PaymentService.create_payment_log(**payment_data_log)
        return Response(
            message="결제가 실패했습니다",
            message_en="Payment failed",
            data={},
            code=201,
        ).to_dict()
