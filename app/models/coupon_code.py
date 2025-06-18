from app.extensions import db
from app.models.base import BaseModel
import const
from datetime import datetime
from app.models.coupon import Coupon
from app.models.user import User


class CouponCode(db.Model, BaseModel):
    __tablename__ = "coupon_codes"

    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey("coupons.id"), nullable=False)
    code = db.Column(db.String(20), nullable=False, unique=True)
    is_used = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    expired_at = db.Column(db.DateTime)
    value = db.Column(db.Integer, nullable=False, default=0)
    num_days = db.Column(db.Integer, default=const.DATE_EXPIRED)
    total_link_active = db.Column(db.Integer, default=7)
    used_at = db.Column(db.DateTime)
    used_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now
    )  #

    coupon = db.relationship(Coupon, foreign_keys=[coupon_id], lazy="joined")
    user = db.relationship(User, lazy="joined", foreign_keys=[used_by])

    def to_dict(self):
        return {
            "expired_from": (
                self.coupon.expired_from.strftime("%Y-%m-%d %H:%M:%S")
                if self.coupon.expired_from
                else None
            ),
            "expired": (
                self.coupon.expired.strftime("%Y-%m-%d %H:%M:%S")
                if self.coupon.expired
                else None
            ),
            "type": self.coupon.type if self.coupon else None,
            "coupon_name": self.coupon.name if self.coupon else None,
            "username": self.user.username if self.user else None,
            "email": self.user.email if self.user else None,
            "id": self.id,
            "coupon_id": self.coupon_id,
            "code": self.code,
            "is_used": self.is_used,
            "is_active": self.is_active,
            "value": self.value,
            "num_days": self.num_days,
            "total_link_active": self.total_link_active,
            "used_by": self.used_by,
            "used_at": (
                self.used_at.strftime("%Y-%m-%d %H:%M:%S") if self.used_at else None
            ),
            "expired_at": (
                self.expired_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.expired_at
                else None
            ),
            "created_at": (
                self.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.updated_at
                else None
            ),
        }
