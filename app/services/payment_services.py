from app.models.user import User
from app.models.link import Link
from app.models.payment import Payment
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

from app.lib.string import generate_order_id


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
        now = datetime.now()
        active_payment = (
            Payment.query.filter_by(user_id=user_id)
            .filter(Payment.end_date > now)
            .filter(Payment.package_name != "ADDON")
            .order_by(Payment.end_date.desc())
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
    def create_new_payment(current_user, package_name, status="PENDING"):
        now = datetime.now()
        origin_price = PACKAGE_CONFIG[package_name]["price"]
        start_date = now
        end_date = start_date + relativedelta(months=1)
        user_id = current_user.id
        order_id = generate_order_id()
        payment = Payment(
            user_id=user_id,
            package_name=package_name,
            order_id=order_id,
            amount=origin_price,
            customer_name=current_user.name or current_user.email,
            method="REQUEST",
            status=status,
            price=origin_price,
            requested_at=start_date,
            start_date=start_date,
            end_date=end_date,
            total_link=PACKAGE_CONFIG[package_name]["total_link"],
            total_create=PACKAGE_CONFIG[package_name]["total_create"],
        )
        db.session.add(payment)
        db.session.commit()
        return payment

    @staticmethod
    def create_addon_payment(user_id, parent_payment_id, order_id):
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
        result = PaymentService.calculate_addon_price(user_id, 1)
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
            "total_link": 1,
            "description": "BuyAddon",
        }
        payment = PaymentService.create_payment(**payment_data)
        return payment

    @staticmethod
    def upgrade_package(current_user, new_package):
        user_id = current_user.id
        now = datetime.now()
        active_payment = PaymentService.has_active_subscription(user_id)

        if not active_payment:
            return PaymentService.create_new_payment(user_id, new_package)

        # Tính tiền còn lại của gói cũ
        remaining_days = (active_payment.end_date - now).days
        old_price_per_day = active_payment.price / PACKAGE_DURATION_DAYS
        remaining_value = round(old_price_per_day * remaining_days)

        origin_price = PACKAGE_CONFIG[new_package]["price"]

        final_price = max(0, origin_price - remaining_value)

        new_payment = Payment(
            user_id=user_id,
            package_name=new_package,
            amount=origin_price,
            customer_name=current_user.name or current_user.email,
            method="REQUEST_UPGRADE",
            price=final_price,
            requested_at=now,
            start_date=now,
            end_date=active_payment.end_date,
            total_link=PACKAGE_CONFIG[new_package]["total_link"],
            total_create=PACKAGE_CONFIG[new_package]["total_create"],
        )
        db.session.add(new_payment)
        db.session.commit()
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
        # Query cơ bản với các điều kiện
        query = Payment.query

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
            if len(payment_addons) > 1:
                return {
                    "user_id": user_id,
                    "can_buy": 0,
                    "message": "애드온 2개가 이미 존재합니다",
                    "message_en": "2 addon packages already exist",
                    "price": 0,
                    "remaining_days": 0,
                }

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
                    "next_payment": (end_date_default + timedelta(days=1)).strftime(
                        "%Y-%m-%d"
                    ),
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
                    "next_payment": (end_date_default + timedelta(days=1)).strftime(
                        "%Y-%m-%d"
                    ),
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
                    "next_payment": (
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
                    "next_payment": (
                        (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
                        if end_date
                        else None
                    ),
                }

            current_package_detail = const.PACKAGE_CONFIG[current_package]

            current_price = current_payment.price
            current_days = current_package_detail.get("duration_days", 30)
            discount = int(current_price / current_days * remaining_days)
            new_package_price = new_package_info["price"]
            upgrade_price = max(0, new_package_price - discount)
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
                "remaining_days": remaining_days,
                "used_days": used_days,
                "discount": discount,
                "amount": new_package_price,
                "price": upgrade_price,
                "new_package_price": new_package_price,
                "new_package_price_origin": new_package_info["price_origin"],
                "discount_welcome": discount_welcome,
                "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
                "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
                "next_payment": (
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
