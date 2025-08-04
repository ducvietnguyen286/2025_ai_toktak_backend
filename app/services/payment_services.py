from app.models.user import User
from app.models.link import Link
from app.models.payment import Payment
from app.models.payment_logs import PaymentLog
from app.models.payment_detail import PaymentDetail
from app.models.user_history import UserHistory
from app.extensions import db
from sqlalchemy import and_, func, or_
from flask import jsonify
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased
import os
import json
import const
import hashlib
from app.models.batch import Batch
from app.lib.logger import logger
from dateutil.relativedelta import relativedelta
import traceback
from const import PACKAGE_CONFIG, PACKAGE_DURATION_DAYS
import requests
import base64
from app.services.user import UserService
from app.lib.response import Response

from app.lib.string import generate_order_id
from app.lib.logger import log_make_repayment_message
from app.third_parties.email import send_email
from unittest.mock import Mock


class PaymentService:

    @staticmethod
    def find_payment(id):
        return Payment.query.get(id)

    @staticmethod
    def create_payment(*args, **kwargs):
        try:
            payment = Payment(*args, **kwargs)
            payment.save()
            return payment
        except Exception as ex:
            logger.error(f"Error creating payment: {ex}")
            return None

    @staticmethod
    def create_payment_log(*args, **kwargs):
        try:
            payment_log = PaymentLog(*args, **kwargs)
            payment_log.save()
            return payment_log
        except Exception as ex:
            logger.error(f"Error creating payment_log: {ex}")
            return None

    @staticmethod
    def create_payment_detail(*args, **kwargs):
        try:
            payment_detail = PaymentDetail(*args, **kwargs)
            payment_detail.save()
            return payment_detail
        except Exception as ex:
            logger.error(f"Error creating payment_detail: {ex}")
            return None

    @staticmethod
    def find_payment_by_order(order_id):
        try:
            payment_detail = Payment.query.filter(
                Payment.order_id == order_id,
            ).first()
            return payment_detail
        except Exception as ex:
            logger.error(f"Error creating payment: {ex}")
            return None

    @staticmethod
    def get_last_payment_basic(user_id, date_today):
        try:
            payment_detail = (
                Payment.query.filter(
                    Payment.user_id == user_id,
                    Payment.package_name == "BASIC",
                    Payment.status == "PAID",
                    Payment.end_date >= date_today,
                )
                .order_by(Payment.end_date.desc())
                .first()
            )
            return payment_detail
        except Exception as ex:
            logger.error(f"Error creating payment: {ex}")
            return None

    @staticmethod
    def get_total_payment_basic_addon(user_id, date_today, basic_payment_id):
        try:
            payment_addon_count = Payment.query.filter(
                Payment.user_id == user_id,
                # Payment.status == "PAID",
                Payment.end_date >= date_today,
                Payment.parent_id == basic_payment_id,
            ).count()
            return payment_addon_count
        except Exception as ex:
            logger.error(f"Error creating payment: {ex}")
            return 0

    @staticmethod
    def get_payment_basic_addon(basic_payment_id):
        try:
            payment_addons = Payment.query.filter(
                Payment.parent_id == basic_payment_id,
            ).all()
            return payment_addons
        except Exception as ex:
            logger.error(f"Error get_payment_basic_addon payment: {ex}")
            return 0

    @staticmethod
    def update_payment(id, *args, **kwargs):
        payment = Payment.query.get(id)
        if not payment:
            return None
        payment.update(**kwargs)
        return payment

    @staticmethod
    def can_upgrade(current_package: str, new_package: str) -> bool:
        """Kiểm tra xem việc nâng cấp có hợp lệ không (theo thứ tự gói)"""
        return (
            PACKAGE_CONFIG[new_package]["order_index"]
            > PACKAGE_CONFIG[current_package]["order_index"]
        )

    @staticmethod
    def has_active_subscription(user_id):
        today = datetime.now().date()
        active_payment = (
            Payment.query.filter_by(user_id=user_id)
            .filter(func.date(Payment.end_date) >= today)
            .filter(Payment.package_name != "ADDON")
            .order_by(Payment.id.desc())
            .first()
        )
        return active_payment

    @staticmethod
    def get_last_subscription(user_id):
        active_payment = (
            Payment.query.filter_by(user_id=user_id).order_by(Payment.id.desc()).first()
        )
        return active_payment

    @staticmethod
    def create_new_payment(
        current_user, package_name, status="PENDING", addon_count=0, method="REQUEST"
    ):
        now = datetime.now()
        origin_price = PACKAGE_CONFIG[package_name]["price"]
        start_date = now
        end_date = (start_date + relativedelta(months=1)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        user_id = current_user.id
        order_id = generate_order_id()
        payment_data = {
            "user_id": user_id,
            "package_name": package_name,
            "order_id": order_id,
            "amount": origin_price,
            "price": origin_price,
            "next_payment": origin_price,
            "start_date": start_date,
            "end_date": end_date,
            "customer_name": current_user.name or current_user.email,
            "total_create": PACKAGE_CONFIG[package_name]["total_create"],
            "method": method,
            "requested_at": start_date,
            "total_link": PACKAGE_CONFIG[package_name]["total_link"],
            "next_total_link": PACKAGE_CONFIG[package_name]["total_link"],
            "description": f"{package_name} 패키지를 구매하기",
            "status": status,
        }
        payment = PaymentService.create_payment(**payment_data)
        if package_name == "BASIC" and addon_count > 0:
            result_addon = PaymentService.calculate_addon_price(user_id, addon_count)
            amount_addon = result_addon["amount"]
            amount_price = result_addon["price"]

            data_update_payment = {
                "total_link": payment.total_link + addon_count,
                "amount": payment.amount + amount_addon,
                "price": payment.price + amount_price,
                "description": f"{payment.description}을(를) {amount_addon}개의 애드온으로 구매",
            }
            payment = PaymentService.update_payment(payment.id, **data_update_payment)
            logger.info(
                f"package_name {package_name} addon_count : {addon_count}  data_update_payment : {data_update_payment}"
            )
            PaymentService.create_addon_payment_detail(user_id, payment.id, addon_count)

        return payment

    @staticmethod
    def create_addon_payment(user_id, parent_payment_id, order_id, addon_count=1):
        basic_payment = Payment.query.filter_by(
            id=parent_payment_id, user_id=user_id, package_name="BASIC"
        ).first()
        if not basic_payment:
            return None

        # Kiểm tra số lần đã mua addon với parent_id này
        count = Payment.query.filter_by(
            user_id=user_id, parent_id=parent_payment_id, package_name="ADDON"
        ).count()
        if count >= const.MAX_ADDON_PER_BASIC:
            raise Exception(
                "이 애드온은 BASIC 패키지당 최대 2회까지만 구매할 수 있습니다."
            )
        # Tính số ngày còn lại
        today = datetime.now()
        now = datetime.now()
        result = PaymentService.calculate_addon_price(user_id, addon_count)
        payment_data = {
            "user_id": user_id,
            "package_name": "ADDON",
            "order_id": order_id,
            "amount": result["amount"],
            "price": result["price"],
            "start_date": today,
            "end_date": basic_payment.end_date,
            "customer_name": basic_payment.customer_name,
            "parent_id": parent_payment_id,
            "total_create": 0,
            "method": "REQUEST",
            "requested_at": now,
            "total_link": addon_count,
            "description": "애드온 구매 결제",
        }
        payment = PaymentService.create_payment(**payment_data)
        return payment

    @staticmethod
    def create_addon_payment_detail(user_id, payment_id, addon_count=1):
        result = PaymentService.calculate_addon_price(user_id, 1)
        payment_data = {
            "user_id": user_id,
            "payment_id": payment_id,
            "amount": result["amount"] * addon_count,
            "price": result["price"],
            "description": f"User by addon with {addon_count}",
        }
        payment_detail = PaymentService.create_payment_detail(**payment_data)
        return payment_detail

    @staticmethod
    def upgrade_package(current_user, new_package, parent_id=0):
        user_id = current_user.id
        now = datetime.now()
        active_payment = PaymentService.has_active_subscription(user_id)
        log_make_repayment_message(active_payment)
        log_make_repayment_message(active_payment.next_payment)

        if not active_payment:
            return PaymentService.create_new_payment(user_id, new_package)

        # Tính tiền còn lại của gói cũ
        payment_user_ugrade_pay = PaymentService.get_payment_must_pay(
            user_id, active_payment.id, active_payment.package_name, new_package
        )
        origin_price = PACKAGE_CONFIG[new_package]["price"]
        order_id = generate_order_id()

        payment_data = {
            "parent_id": parent_id,
            "user_id": user_id,
            "order_id": order_id,
            "package_name": new_package,
            "amount": origin_price,
            "next_payment": origin_price,
            "customer_name": current_user.name or current_user.email,
            "method": "REQUEST_UPGRADE",
            "price": payment_user_ugrade_pay["price"],
            "requested_at": now,
            "start_date": now,
            "end_date": active_payment.end_date,
            "total_link": PACKAGE_CONFIG[new_package]["total_link"],
            "next_total_link": PACKAGE_CONFIG[new_package]["total_link"],
            "total_create": PACKAGE_CONFIG[new_package]["total_create"],
            "description": f"{new_package} 추가 기능을 구매하세요",
        }
        new_payment = PaymentService.create_payment(**payment_data)
        logger.info(payment_data)
        payment_data_log = {
            "payment_id": new_payment.id if new_payment else None,
            "status_code": 200,
            "response_json": json.dumps(payment_data, ensure_ascii=False, default=str),
            "description": json.dumps(payment_user_ugrade_pay, ensure_ascii=False, default=str),
        }
        logger.info(payment_data_log)
        PaymentService.create_payment_log(**payment_data_log)
        return new_payment

    @staticmethod
    def process_subscription_request(user, package_name: str) -> bool:
        now = datetime.now()
        user_id = user.id
        active = PaymentService.get_last_subscription(user_id)
        logger.info(package_name)
        logger.info(active)
        if active:
            logger.info(active.package_name)
            # Trùng gói → không cho mua lại
            if active.package_name == package_name and now <= active.end_date:
                return False

        # Hợp lệ (gói hết hạn hoặc chưa có)
        return True

    @staticmethod
    def get_admin_billings(data_search):
        query = Payment.query.filter(Payment.method != "NEW_USER")
        search_key = data_search.get("search_key", "")

        if search_key != "":
            search_pattern = f"%{search_key}%"
            query = query.filter(
                or_(
                    Payment.package_name.ilike(search_pattern),
                    Payment.customer_name.ilike(search_pattern),
                    Payment.user.has(User.email.ilike(search_pattern)),
                )
            )

        # Xử lý type_order
        if data_search["type_order"] == "id_asc":
            query = query.order_by(Payment.id.asc())
        elif data_search["type_order"] == "id_desc":
            query = query.order_by(Payment.id.desc())
        else:
            query = query.order_by(Payment.id.desc())

        # Xử lý type_payment
        if data_search["type_payment"] == "BASIC":
            query = query.filter(Payment.package_name == "BASIC")
        elif data_search["type_payment"] == "STANDARD":
            query = query.filter(Payment.package_name == "STANDARD")
        elif data_search["type_payment"] == "BUSINESS":
            query = query.filter(Payment.package_name == "BUSINESS")
        elif data_search["type_payment"] == "FREE":
            query = query.filter(Payment.package_name == "FREE")

        time_range = data_search.get("time_range")  # Thêm biến time_range
        # Lọc theo khoảng thời gian
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.filter(Payment.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            query = query.filter(Payment.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            query = query.filter(Payment.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            query = query.filter(Payment.created_at >= start_date)
        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                query = query.filter(Payment.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                query = query.filter(Payment.created_at < to_date)

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination

    @staticmethod
    def calculate_addon_price(user_id, addon_count=1):
        try:
            today = datetime.now().date()
            payment_basic = (
                Payment.query.filter(
                    Payment.user_id == user_id,
                    Payment.package_name == "BASIC",
                    # Payment.status == "PAID",
                    Payment.end_date >= today,
                )
                .order_by(Payment.end_date.desc())
                .first()
            )

            if not payment_basic:
                return {
                    "user_id": user_id,
                    "can_buy": 0,
                    "message": "유효한 BASIC 요금제가 없거나 만료되었습니다.",
                    "message_en": "There is no active or valid BASIC plan, or it has expired.",
                    "price": 0,
                    "remaining_days": 0,
                }

            payment_addons = PaymentService.get_payment_basic_addon(payment_basic.id)
            end_date = payment_basic.end_date.date()
            remaining_days = min((end_date - today).days, 30)
            if remaining_days < 1:
                return {
                    "can_buy": 0,
                    "message": "Gói BASIC đã hết hạn.",
                    "price": 0,
                    "remaining_days": 0,
                }

            # Tính tiền addon
            addon_price = const.PACKAGE_CONFIG["BASIC"]["addon"]["EXTRA_CHANNEL"][
                "price"
            ]

            basic_price = const.PACKAGE_CONFIG["BASIC"]["price"]

            total_amount = addon_price * addon_count
            duration = const.BASIC_DURATION_DAYS
            price_to_pay = int(total_amount / duration * remaining_days)
            price_discount = total_amount - price_to_pay

            return {
                "addon_count": addon_count,
                "payment_addons": [
                    payment_addon_detail._to_json()
                    for payment_addon_detail in payment_addons
                ],
                "can_buy": 1,
                "message": f"Bạn có thể mua addon. Còn {remaining_days} ngày. calculate_addon_price",
                "duration": duration,
                "amount": total_amount,
                "discount": price_discount,
                "price": price_to_pay,
                "addon_price": total_amount,
                "total_discount": price_discount * addon_count,
                "price_discount": price_discount,
                "price_payment": price_to_pay,
                "remaining_days": remaining_days,
                "basic_payment_id": payment_basic.id,
                "basic_price": basic_price,
                "basic_end_date": end_date.strftime("%Y-%m-%d"),
            }
        except Exception as ex:

            traceback.print_exc()
            logger.error(f"Error calculating addon price: {ex}")
            return {
                "can_buy": 0,
                "message": "Có lỗi xảy ra khi tính giá addon.",
                "price": 0,
                "remaining_days": 0,
            }

    @staticmethod
    def calculate_price_with_addon(user_id, addon_count=1):
        try:
            today = datetime.now().date()

            end_date_default = today + timedelta(days=30)
            # Tính tiền addon
            addon_price = const.PACKAGE_CONFIG["BASIC"]["addon"]["EXTRA_CHANNEL"][
                "price"
            ]

            basic_price = const.PACKAGE_CONFIG["BASIC"]["price"]
            remaining_days = 30
            total_amount = addon_price * addon_count
            duration = const.BASIC_DURATION_DAYS
            price_to_pay = total_amount + basic_price
            price_discount = 0

            return {
                "addon_count": addon_count,
                "payment_addons": [],
                "can_buy": 1,
                "message": f"Bạn có thể mua addon. Còn {remaining_days} ngày. calculate_price_with_addon",
                "duration": duration,
                "amount": price_to_pay,
                "discount": 0,
                "price": price_to_pay,
                "addon_price": addon_price,
                "total_discount": price_discount * addon_count,
                "price_discount": 0,
                "price_payment": price_to_pay,
                "remaining_days": remaining_days,
                "basic_payment_id": 0,
                "basic_price": basic_price,
                "basic_end_date": end_date_default.strftime("%Y-%m-%d"),
            }
        except Exception as ex:

            traceback.print_exc()
            logger.error(f"Error calculating addon price: {ex}")
            return {
                "can_buy": 0,
                "message": "Có lỗi xảy ra khi tính giá addon.",
                "price": 0,
                "remaining_days": 0,
            }

    @staticmethod
    def deletePayment(post_ids):
        try:
            UserHistory.query.filter(
                UserHistory.type == "payment", UserHistory.object_id.in_(post_ids)
            ).delete(synchronize_session=False)

            PaymentDetail.query.filter(PaymentDetail.payment_id.in_(post_ids)).delete(
                synchronize_session=False
            )

            Payment.query.filter(Payment.id.in_(post_ids)).delete(
                synchronize_session=False
            )
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1

    @staticmethod
    def deletePaymentPending(post_ids):
        try:
            UserHistory.query.filter(
                UserHistory.type == "payment", UserHistory.object_id.in_(post_ids)
            ).delete(synchronize_session=False)

            PaymentDetail.query.filter(PaymentDetail.payment_id.in_(post_ids)).delete(
                synchronize_session=False
            )

            Payment.query.filter(Payment.id.in_(post_ids)).delete(
                synchronize_session=False
            )
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1

    @staticmethod
    def calculate_upgrade_price(user_id, new_package, addon_count=0):
        try:
            today = datetime.now().date()
            start_date_default = today
            end_date_default = today + timedelta(days=30)
            logger.info(addon_count)

            # Kiểm tra gói mới có hợp lệ không
            new_package_info = const.PACKAGE_CONFIG.get(new_package)
            if not new_package_info:
                return {
                    "can_upgrade": 0,
                    "code": 201,
                    "message": "업그레이드 플랜이 유효하지 않습니다.",
                    "message_en": "Invalid upgrade package.",
                    "current_package": None,
                    "remaining_days": 0,
                    "used_days": 0,
                    "discount": 0,
                    "upgrade_price": 0,
                    "amount": 0,
                    "price": 0,
                    "new_package_price": 0,
                    "new_package_price_origin": 0,
                    "start_date": start_date_default.strftime("%Y-%m-%d"),
                    "end_date": end_date_default.strftime("%Y-%m-%d"),
                    "next_date_payment": (
                        end_date_default + timedelta(days=1)
                    ).strftime("%Y-%m-%d"),
                }

            # Lấy payment hiện tại còn hạn
            current_payment = (
                Payment.query.filter(
                    Payment.user_id == user_id,
                    Payment.package_name != "ADDON",
                    Payment.end_date >= today,
                )
                .order_by(Payment.end_date.desc())
                .first()
            )
            amount = new_package_info["price"]
            price_addon = 0
            if addon_count > 0 and new_package == "BASIC":
                price_addon = (
                    new_package_info["addon"]["EXTRA_CHANNEL"]["price"] * addon_count
                )
                logger.info(
                    f"addon_count  : {addon_count}  price_addon: {price_addon} "
                )

            new_package_price_origin = new_package_info["price_origin"]
            new_package_price = new_package_info["price"]
            discount_welcome = new_package_price_origin - new_package_price

            if not current_payment:
                return {
                    "can_upgrade": 1,
                    "code": 200,
                    "message": "플랜을 업그레이드할 수 있습니다.",
                    "message_en": "You can upgrade your plan.Not have current_payment",
                    "current_package": None,
                    "remaining_days": 0,
                    "used_days": 0,
                    "discount": 0,
                    "upgrade_price": 0,
                    "amount": amount,
                    "price": amount + price_addon,
                    "new_package_price_origin": new_package_price_origin,
                    "new_package_price": new_package_price,
                    "discount_welcome": discount_welcome,
                    "start_date": start_date_default.strftime("%Y-%m-%d"),
                    "end_date": end_date_default.strftime("%Y-%m-%d"),
                    "next_date_payment": (
                        end_date_default + timedelta(days=1)
                    ).strftime("%Y-%m-%d"),
                }

            current_package = current_payment.package_name
            start_date = (
                current_payment.start_date.date()
                if current_payment.start_date
                else None
            )
            end_date = (
                current_payment.end_date.date() if current_payment.end_date else None
            )

            used_days = (today - start_date).days if start_date else 0

            new_package_price_origin = new_package_info["price_origin"]
            new_package_price = new_package_info["price"]
            discount_welcome = new_package_price_origin - new_package_price

            if current_package == new_package:
                return {
                    "can_upgrade": 0,
                    "code": 200,
                    "message": "현재 이 플랜을 사용 중입니다. 업그레이드할 수 없습니다.",
                    "message_en": "You are already using this plan. Upgrade is not possible.",
                    "current_package": current_package,
                    "remaining_days": 0,
                    "used_days": used_days,
                    "discount": 0,
                    "upgrade_price": 0,
                    "amount": new_package_info["price"],
                    "price": new_package_info["price"],
                    "new_package_price": new_package_info["price"],
                    "new_package_price_origin": new_package_info["price_origin"],
                    "discount_welcome": discount_welcome,
                    "start_date": (
                        start_date.strftime("%Y-%m-%d") if start_date else None
                    ),
                    "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
                    "next_date_payment": (
                        (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
                        if end_date
                        else None
                    ),
                }

            remaining_days = min(
                (end_date - today).days if end_date and today else 0, 30
            )

            if remaining_days <= 0:
                return {
                    "can_upgrade": 0,
                    "code": 201,
                    "message": "현재 이용 중인 요금제가 만료되었습니다.",
                    "message_en": "Your current package has expired.",
                    "current_package": current_package,
                    "remaining_days": 0,
                    "used_days": used_days,
                    "discount": 0,
                    "upgrade_price": new_package_info["price"],
                    "amount": new_package_info["price"],
                    "price": new_package_info["price"],
                    "new_package_price": new_package_info["price"],
                    "new_package_price_origin": new_package_info["price_origin"],
                    "discount_welcome": discount_welcome,
                    "start_date": (
                        start_date.strftime("%Y-%m-%d") if start_date else None
                    ),
                    "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
                    "next_date_payment": (
                        (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
                        if end_date
                        else None
                    ),
                }

            current_package_detail = const.PACKAGE_CONFIG[current_package]

            # tính tiền basic và addon

            current_price = PaymentService.get_total_price(current_payment.id)
            # tiền 1 ngày của gói hiện tại
            base_day_price = current_price / current_package_detail.get(
                "duration_days", 30
            )

            # tien đã sử dụng
            used_money = base_day_price * used_days if used_days else 0
            money_rollback = current_price - used_money

            current_days = current_package_detail.get("duration_days", 30)
            discount = used_money
            new_package_price = new_package_info["price"]

            upgrade_price = max(0, new_package_price - money_rollback)
            amount = upgrade_price
            discount_welcome = (
                new_package_info["price_origin"] - new_package_info["price"]
            )

            return {
                "can_upgrade": 1,
                "code": 200,
                "message": "업그레이드하실 수 있습니다.",
                "message_en": f"You can upgrade. {new_package}",
                "upgrade_package": new_package,
                "upgrade_origin_price": new_package_price,
                "current_package": current_package,
                "current_price": current_price,
                "base_day_price": base_day_price,
                "remaining_days": remaining_days,
                "used_days": used_days,
                "used_money": used_money,
                "money_rollback": money_rollback,
                "discount": used_money,
                "amount": new_package_price,
                "price": upgrade_price,
                "new_package_price": new_package_price,
                "new_package_price_origin": new_package_info["price_origin"],
                "discount_welcome": discount_welcome,
                "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
                "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
                "next_date_payment": (
                    (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
                    if end_date
                    else None
                ),
                "current_package_detail": current_package_detail,
                "current_days": current_days,
            }
        except Exception as ex:
            tb_str = traceback.format_exc()
            logger.error(f"[calculate_upgrade_price] {ex}\n{tb_str}")
            return {
                "can_upgrade": 0,
                "code": 201,
                "message": "Có lỗi xảy ra khi tính toán nâng cấp.",
                "message_en": "Error occurred while calculating upgrade.",
            }

    @staticmethod
    def get_payment_must_pay(user_id, payment_id, current_package, upgrade_package):
        # Tính toán giá nâng cấp gói
        current_package_detail = const.PACKAGE_CONFIG[current_package]
        new_package_info = const.PACKAGE_CONFIG[upgrade_package]
        today = datetime.now().date()
        current_payment = (
            Payment.query.filter(
                Payment.user_id == user_id,
                Payment.package_name != "ADDON",
                Payment.end_date >= today,
            )
            .order_by(Payment.end_date.desc())
            .first()
        )

        start_date = (
            current_payment.start_date.date() if current_payment.start_date else None
        )

        used_days = (today - start_date).days if start_date else 0

        current_price = PaymentService.get_total_price(payment_id)
        # tiền 1 ngày của gói hiện tại
        base_day_price = current_price / current_package_detail.get("duration_days", 30)

        # tien đã sử dụng
        used_money = base_day_price * used_days if used_days else 0
        money_rollback = current_price - used_money

        current_days = current_package_detail.get("duration_days", 30)
        discount = used_money
        new_package_price = new_package_info["price"]

        upgrade_price = max(0, new_package_price - money_rollback)
        discount_welcome = new_package_info["price_origin"] - new_package_info["price"]
        return {
            "upgrade_origin_price": new_package_price,
            "current_package": current_package,
            "current_price": current_price,
            "base_day_price": base_day_price,
            "used_days": used_days,
            "used_money": used_money,
            "money_rollback": money_rollback,
            "discount": discount,
            "amount": new_package_price,
            "price": upgrade_price,
            "new_package_price": new_package_price,
            "new_package_price_origin": new_package_info["price_origin"],
            "discount_welcome": discount_welcome,
            "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
            "current_package_detail": current_package_detail,
            "current_days": current_days,
        }

    @staticmethod
    def confirm_payment_toss(payment_key, order_id, amount):
        TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY")
        url = "https://api.tosspayments.com/v1/payments/confirm"
        auth = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()

        headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

        payload = {"paymentKey": payment_key, "orderId": order_id, "amount": amount}

        try:
            res = requests.post(url, json=payload, headers=headers)
            return res.json(), res.status_code
        except requests.RequestException as e:
            return {"message": f"TossPayments 연결 오류: {str(e)}"}, 500

    @staticmethod
    def billing_authorizations_toss(auth_key, customer_key):
        TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY")
        url = "https://api.tosspayments.com//v1/billing/authorizations/issue"
        auth = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()

        headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

        payload = {"authKey": auth_key, "customerKey": customer_key}

        try:
            res = requests.post(url, json=payload, headers=headers)
            return res.json(), res.status_code
        except requests.RequestException as e:
            return {"message": f"TossPayments 연결 오류: {str(e)}"}, 500

    @staticmethod
    def approvalPayment(payment_id):
        try:
            today = datetime.now().date()
            payment_detail = PaymentService.find_payment(payment_id)
            if not payment_detail:
                return Response(
                    message="결제 정보가 존재하지 않습니다.",
                    message_en="Payment does not exist",
                    code=201,
                ).to_dict()

            package_name = payment_detail.package_name
            if package_name == "ADDON":
                payment_parent_detail = PaymentService.find_payment(
                    payment_detail.parent_id
                )
                if payment_parent_detail:
                    payment_parent_end_date = payment_parent_detail.end_date.date()
                    payment_parent_status = payment_parent_detail.status
                    if payment_parent_status != "PAID":
                        return Response(
                            message="구매하신 Basic 요금제가 아직 결제되지 않았습니다.",
                            message_en="Your Basic plan has not been paid for yet.",
                            code=201,
                        ).to_dict()
                    if payment_parent_end_date <= today:
                        return Response(
                            message="Basic 요금제가 만료되었습니다.",
                            message_en="Your Basic plan has expired.",
                            code=201,
                        ).to_dict()

            data_payment = {
                "status": "PAID",
                "approved_at": datetime.now(),
            }

            payment = PaymentService.update_payment(payment_id, **data_payment)
            if payment:
                user_id = payment.user_id
                package_name = payment.package_name
                parent_id = payment.parent_id
                total_link = payment.total_link
                object_id = payment.id
                start_date = payment.start_date
                end_date = payment.end_date
                child_amount = payment.amount
                child_total_link = payment.total_link
                total_create = payment.total_create

                if parent_id > 0:

                    payment_parent = PaymentService.find_payment(parent_id)
                    parent_amount = payment_parent.amount
                    parent_total_link = payment_parent.total_link

                    # update old payment để không thể tự động trừ tiền
                    # vì ngày kết thúc của gói nâng cấp sẽ bằng gói mới
                    data_update_old_payment = {
                        "is_renew": 1,
                        "next_payment": child_amount + parent_amount,
                        "next_total_link": min(child_total_link + parent_total_link, 7),
                    }
                    PaymentService.update_payment(parent_id, **data_update_old_payment)

                user_detail = UserService.find_user(user_id)
                if package_name == "ADDON":

                    if user_detail:
                        total_link_active = user_detail.total_link_active
                        data_update = {
                            "total_link_active": total_link_active + total_link,
                        }

                        UserService.update_user(user_id, **data_update)
                        data_user_history = {
                            "user_id": user_id,
                            "type": "payment",
                            "type_2": package_name,
                            "object_id": object_id,
                            "object_start_time": start_date,
                            "object_end_time": end_date,
                            "title": "Basic 추가 기능을 구매하세요.",
                            "description": "Basic 추가 기능을 구매하세요.",
                            "value": 0,
                            "num_days": 0,
                            "total_link_active": 0,
                        }
                        UserService.create_user_history(**data_user_history)
                else:
                    package_data = const.PACKAGE_CONFIG.get(package_name)
                    if not package_data:
                        return Response(
                            message="유효하지 않은 패키지입니다.", code=201
                        ).to_dict()

                    subscription_expired = end_date

                    batch_total = UserService.get_total_batch_total(user_id)
                    login_user_subscription = user_detail.subscription
                    batch_remain = 0
                    if login_user_subscription != "FREE":
                        batch_remain = user_detail.batch_remain

                    batch_remain = batch_remain + package_data["batch_remain"]
                    total_link_active = user_detail.total_link_active
                    data_update = {
                        "subscription": package_name,
                        "subscription_expired": subscription_expired,
                        "batch_total": batch_total + total_create,
                        "batch_remain": batch_remain,
                        "total_link_active": min(
                            total_link_active + total_link, 7
                        ),
                    }

                    UserService.update_user(user_id, **data_update)
                    data_user_history = {
                        "user_id": user_id,
                        "type": "payment",
                        "object_id": object_id,
                        "object_start_time": start_date,
                        "object_end_time": subscription_expired,
                        "title": package_data["pack_name"],
                        "description": package_data["pack_description"],
                        "value": package_data["batch_total"],
                        "num_days": package_data["batch_remain"],
                        "total_link_active": package_data["total_link_active"],
                        "admin_description": package_name,
                    }
                    UserService.create_user_history(**data_user_history)
            else:
                return Response(
                    message="결제 정보가 존재하지 않습니다",
                    message_en="Payment does not exist",
                    code=201,
                ).to_dict()

            return Response(
                message="승인이 완료되었습니다.",
                message_en="Approval has been completed",
                # data={"payment": payment},
                code=200,
            ).to_dict()
        except requests.RequestException as e:
            return Response(
                message=f"유효하지 않은 패키지입니다. {str(e)}", code=201
            ).to_dict()

    @staticmethod
    def get_total_price(payment_id):
        total = (
            Payment.query.with_entities(func.sum(Payment.price))
            .filter((Payment.id == payment_id) | (Payment.parent_id == payment_id))
            .scalar()
        )
        return total or 0

    @staticmethod
    def report_payment_by_type(data_search):

        histories = Payment.query.filter(Payment.method != "NEW_USER")
        package_name = data_search.get("package_name", "")
        status = data_search.get("status", "")

        if package_name != "":
            histories = histories.filter(Payment.package_name == package_name)
        if status != "":
            histories = histories.filter(Payment.status == status)
        time_range = data_search.get("time_range", "")
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            histories = histories.filter(Payment.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            histories = histories.filter(Payment.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            histories = histories.filter(Payment.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            histories = histories.filter(Payment.created_at >= start_date)

        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                histories = histories.filter(Payment.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                histories = histories.filter(Payment.created_at < to_date)

        total = histories.count()
        total_price = histories.with_entities(
            func.coalesce(func.sum(Payment.price), 0)
        ).scalar()

        return {"total": total, "total_price": total_price}

    @staticmethod
    def auto_renew_subscriptions():
        try:
            # chạy lúc 23 giờ đêm mỗi ngày
            now = datetime.now()
            today = now.date()
            log_make_repayment_message("Begin[auto_renew_subscriptions] ")
            expiring_payments = Payment.query.filter(
                func.date(Payment.end_date) == today,
                Payment.status == "PAID",
                Payment.is_renew == 0,
                Payment.method != "NEW_USER",
                Payment.package_name != "ADDON",
            ).all()

            for old_payment in expiring_payments:
                old_payment_id = old_payment.id
                old_payment_amount = old_payment.amount

                user = old_payment.user
                log_make_repayment_message(f"User {user.id} {user.email} hết hạn .")
                order_id = generate_order_id("renew")
                new_package_info = const.PACKAGE_CONFIG.get(old_payment.package_name)
                if not new_package_info:
                    log_make_repayment_message(
                        f"User {user.id} {user.email} {old_payment.package_name} không tồn tại."
                    )
                    continue

                if not user or not user.card_info:
                    log_make_repayment_message(
                        f"User {user.id} {user.email} không đăng kí thẻ để tự động gia hạn ."
                    )
                    continue
                log_make_repayment_message(user.card_info)
                card_info_json = json.loads(user.card_info)
                billing_key = card_info_json.get("billingKey")
                customer_key = card_info_json.get("customerKey")

                if not billing_key or not customer_key:
                    log_make_repayment_message(
                        f"❌ User {user.id} {user.email}  thiếu billingKey hoặc customerKey, bỏ qua."
                    )
                    continue
                order_id = generate_order_id("renew")
                encoded_auth = base64.b64encode(
                    f"{os.getenv('TOSS_SECRET_KEY')}:".encode()
                ).decode()
                headers = {
                    "Authorization": f"Basic {encoded_auth}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "amount": new_package_info["price"],
                    "orderId": order_id,
                    "customerKey": customer_key,
                    "orderName": f"{old_payment.package_name} 요금제를 자동 갱신합니다.",
                    "customerEmail": user.email,
                    "customerName": old_payment.customer_name,
                }
                log_make_repayment_message(
                    "[auto_renew_subscriptions] Gửi yêu cầu gia hạn tự động đến TossPayments API : payload "
                )

                log_make_repayment_message(payload)

                payment_data_log = {
                    "payment_id": old_payment.id,
                    "description": f"결제 ID {old_payment.id}의 자동 갱신",
                }
                PaymentService.create_payment_log(**payment_data_log)

                res = requests.post(
                    f"https://api.tosspayments.com/v1/billing/{billing_key}",
                    headers=headers,
                    json=payload,
                )

                result = res.json()
                log_make_repayment_message(
                    "[auto_renew_subscriptions] Kết quả từ TossPayments API:"
                )
                log_make_repayment_message(result)

                now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                api_result_str = json.dumps(result, ensure_ascii=False)

                if res.status_code == 200 and result.get("status") == "DONE":
                    new_payment = PaymentService.create_new_payment(
                        user, old_payment.package_name
                    )
                    payment_id = new_payment.id

                    now = datetime.now()
                    start_date = (now + timedelta(days=1)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    end_date = (start_date + relativedelta(months=1)).replace(
                        hour=23, minute=59, second=59, microsecond=0
                    )

                    data_update_payment = {
                        "order_id": order_id,
                        "method": "AUTO_RENEW",
                        "start_date": start_date,
                        "end_date": end_date,
                        "payment_key": result.get("paymentKey", ""),
                        "payment_data": api_result_str,
                        "description": (
                            f"[Auto Renew]\n"
                            f"- Time: {now_str}\n"
                            f"- From Payment ID: {old_payment_id}\n"
                            f"- Order ID: {order_id}\n"
                            f"- Amount: {old_payment_amount}\n"
                            f"- API Result: {api_result_str}"
                        ),
                    }
                    new_payment = PaymentService.update_payment(
                        new_payment.id, **data_update_payment
                    )

                    PaymentService.approvalPayment(payment_id)
                    data_email = {
                        "customer_name": user.name or user.email,
                        "package_name": new_payment.package_name,
                        "amount": new_payment.amount,
                        "order_id": new_payment.order_id,
                        "end_date": new_payment.end_date.strftime("%Y-%m-%d"),
                    }

                    payment_data_log = {
                        "payment_id": payment_id,
                        "raw_response": json.dumps(result, ensure_ascii=False),
                        "response_json": result,
                        "description": (
                            f"[Auto Renew]\n"
                            f"- Time: {now_str}\n"
                            f"- From Payment ID: {old_payment_id}\n"
                            f"- Order ID: {order_id}\n"
                            f"- Amount: {old_payment_amount}\n"
                            f"- API Result: {api_result_str}"
                        ),
                    }
                    PaymentService.create_payment_log(**payment_data_log)

                    data_update_old_payment = {"is_renew": 1}
                    PaymentService.update_payment(
                        old_payment_id, **data_update_old_payment
                    )

                    send_email(
                        user.email,
                        "요금제 자동 결제가 완료되었습니다",
                        "renewal_success.html",
                        data_email,
                    )
                    log_make_repayment_message(
                        f"✅ Gia hạn thành công cho user {user.email}"
                    )
                else:
                    fail_msg = result.get("message", "Không rõ lỗi")
                    error_message = (
                        f"{old_payment.description}\n"
                        f"[Auto Renew Failed]\n"
                        f"- Time: {now_str}\n"
                        f"- From Payment ID: {old_payment_id}\n"
                        f"- Order ID: {order_id}\n"
                        f"- Lỗi: {fail_msg}\n"
                        f"- API Result: {api_result_str}"
                    )
                    data_update_old_payment = {
                        "description": error_message,
                        "is_renew": 1,
                    }
                    PaymentService.update_payment(
                        old_payment_id, **data_update_old_payment
                    )

                    log_make_repayment_message(
                        f"❌ Gia hạn thất bại cho user {user.email}: {fail_msg}"
                    )

                    payment_data_log = {
                        "payment_id": payment_id,
                        "raw_response": json.dumps(result, ensure_ascii=False),
                        "response_json": result,
                        "description": error_message,
                    }
                    PaymentService.create_payment_log(**payment_data_log)

            return len(expiring_payments)

        except Exception as ex:
            tb = traceback.format_exc()
            log_make_repayment_message(
                f"[auto_renew_subscriptions] Exception: {ex}\n{tb}"
            )

    @staticmethod
    def auto_payment_basic_free(user_id_login):
        try:
            user = UserService.find_user_with_out_session(user_id_login)
            subscription = user.subscription

            if subscription == "FREE":
                now = datetime.now()
            else:
                now = user.subscription_expired
            logger.info(f"auto_payment_basic_free {now} datetime")
            today = now.date()
            new_payment = PaymentService.create_new_payment(user, "BASIC")
            payment_id = new_payment.id

            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (start_date + relativedelta(months=1)).replace(
                hour=23, minute=59, second=59, microsecond=0
            )
            order_id = generate_order_id("free_basic")
            data_update_payment = {
                "order_id": order_id,
                "method": "AUTO_FREE_BASIC",
                "start_date": start_date,
                "end_date": end_date,
                "payment_key": "",
                "payment_data": "",
                "description": (
                    f"[Free User when save Card]\n" f"Card Info: {user.card_info}\n"
                ),
            }
            new_payment = PaymentService.update_payment(
                new_payment.id, **data_update_payment
            )

            PaymentService.approvalPayment(payment_id)
            data_email = {
                "customer_name": user.name or user.email,
                "start_date": new_payment.start_date.strftime("%Y-%m-%d"),
                "end_date": new_payment.end_date.strftime("%Y-%m-%d"),
            }

            send_email(
                user.email,
                "무료 BASIC 요금제 제공 안내",
                "free_basic_success.html",
                data_email,
            )
            log_make_repayment_message(f"✅ Free Basic for user save Card {user.email}")

        except Exception as ex:
            tb = traceback.format_exc()
            log_make_repayment_message(
                f"[auto_renew_subscriptions] Exception: {ex}\n{tb}"
            )

    @staticmethod
    def deletePaymentNewUser(user_id):
        try:
            Payment.query.filter(
                Payment.user_id == user_id,
                Payment.method == "NEW_USER",
            ).delete(synchronize_session=False)
        except Exception as ex:
            return 0
        return 1

    @staticmethod
    def get_user_billings(data_search):
        query = Payment.query.filter(Payment.method != "NEW_USER")
        search_key = data_search.get("search_key", "")
        user_id_login = data_search.get("user_id_login", "")
        query = query.filter(Payment.user_id == user_id_login)

        if search_key != "":
            search_pattern = f"%{search_key}%"
            query = query.filter(
                or_(
                    Payment.package_name.ilike(search_pattern),
                    Payment.customer_name.ilike(search_pattern),
                    Payment.user.has(User.email.ilike(search_pattern)),
                )
            )

        query = query.order_by(Payment.id.desc())

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination
