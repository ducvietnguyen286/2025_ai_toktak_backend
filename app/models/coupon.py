from app.extensions import db
from app.models.base import BaseModel


class Coupon(db.Model, BaseModel):
    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(500))
    name = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text)
    expired_from = db.Column(db.DateTime)
    expired = db.Column(db.DateTime)
    type = db.Column(db.String(20), nullable=False, default="DISCOUNT")
    value = db.Column(db.Float, nullable=False, default=0)
    used = db.Column(db.Integer, default=0)
    max_used = db.Column(db.Integer, default=0)
    is_has_whitelist = db.Column(db.Boolean, default=False)
    white_lists = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    to_json_parse = ("white_lists",)
