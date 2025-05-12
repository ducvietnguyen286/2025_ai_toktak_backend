from app.models.user import User
from app.models.post import Post
from app.models.link import Link
from app.models.payment import Payment
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

from const import PACKAGE_CONFIG, PACKAGE_DURATION_DAYS


class PaymentService:

    @staticmethod
    def can_upgrade(current_package: str, new_package: str) -> bool:
        """Kiểm tra xem việc nâng cấp có hợp lệ không (theo thứ tự gói)"""
        return (
            PACKAGE_CONFIG[new_package]["order_index"]
            > PACKAGE_CONFIG[current_package]["order_index"]
        )

    @staticmethod
    def has_active_subscription(user_id):
        now = datetime.utcnow()
        active_payment = (
            Payment.query.filter_by(user_id=user_id)
            .filter(Payment.end_date > now)
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
    def create_new_payment(current_user, package_name):
        now = datetime.utcnow()
        price = PACKAGE_CONFIG[package_name]["price"]
        start_date = now
        end_date = start_date + relativedelta(months=1)
        user_id = current_user.id
        payment = Payment(
            user_id=user_id,
            package_name=package_name,
            amount=price,
            customer_name=current_user.name or current_user.email,
            method="REQUEST",
            price=price,
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
    def upgrade_package(current_user, new_package):
        user_id = current_user.id
        now = datetime.utcnow()
        active_payment = PaymentService.has_active_subscription(user_id)

        if not active_payment:
            return PaymentService.create_new_payment(user_id, new_package)

        # Tính tiền còn lại của gói cũ
        remaining_days = (active_payment.end_date - now).days
        old_price_per_day = active_payment.price / PACKAGE_DURATION_DAYS
        remaining_value = round(old_price_per_day * remaining_days)

        new_price = PACKAGE_CONFIG[new_package]["price"]

        final_price = max(0, new_price - remaining_value)

        new_payment = Payment(
            user_id=user_id,
            package_name=new_package,
            amount=final_price,
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
        now = datetime.utcnow()
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
