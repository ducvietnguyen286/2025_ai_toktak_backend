from app.extensions import db
from app.models.base import BaseModel
import const


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
    used_at = db.Column(db.DateTime)
    used_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
