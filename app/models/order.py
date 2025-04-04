from app.extensions import db
from app.models.base import BaseModel


class Order(db.Model, BaseModel):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_number = db.Column(db.String(50), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0)
    final_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(50), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    payment_date = db.Column(db.DateTime, nullable=True)
    coupon_code = db.Column(db.String(20), nullable=True)
    coupon_discount = db.Column(db.Float, default=0)
    coupon_type = db.Column(db.String(20), nullable=True)

    status = db.Column(db.Integer, default=1)

    db.relationship("User", lazy="joined")
