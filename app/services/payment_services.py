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

from const import PACKAGE_PRICES, PACKAGE_DURATION_DAYS, PACKAGE_ORDER


class PaymentService:

    @staticmethod
    def can_upgrade(current_package: str, new_package: str) -> bool:
        """Kiểm tra xem việc nâng cấp có hợp lệ không (theo thứ tự gói)"""
        return PACKAGE_ORDER[new_package] > PACKAGE_ORDER[current_package]

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
    def create_new_payment(user_id, package_name):
        now = datetime.utcnow()
        price = PACKAGE_PRICES[package_name]
        start_date = now
        end_date = start_date + relativedelta(months=1)

        payment = Payment(
            user_id=user_id,
            package_name=package_name,
            price=price,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(payment)
        db.session.commit()
        return payment

    @staticmethod
    def upgrade_package(user_id, new_package):
        now = datetime.utcnow()
        active_payment = PaymentService.has_active_subscription(user_id)

        if not active_payment:
            return PaymentService.create_new_payment(user_id, new_package)

        # Tính tiền còn lại của gói cũ
        remaining_days = (active_payment.end_date - now).days
        old_price_per_day = active_payment.price / PACKAGE_DURATION_DAYS
        remaining_value = round(old_price_per_day * remaining_days)

        new_price = PACKAGE_PRICES[new_package]
        final_price = max(0, new_price - remaining_value)

        new_payment = Payment(
            user_id=user_id,
            package_name=new_package,
            price=final_price,
            start_date=now,
            end_date=active_payment.end_date,
        )
        db.session.add(new_payment)
        db.session.commit()
        return new_payment
