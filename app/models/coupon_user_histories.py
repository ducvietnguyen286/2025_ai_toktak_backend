from app.extensions import db
from app.models.base import BaseModel


class CouponUserHistories(db.Model, BaseModel):
    __tablename__ = "coupon_user_histories"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    batch_id = db.Column(db.Integer, default=0)
    old_batch_remain = db.Column(db.Integer, default=0)
    new_batch_remain = db.Column(db.Integer, default=0)

    type = db.Column(db.String(500))
    type_2 = db.Column(db.String(500))
    object_id = db.Column(db.Integer, default=0)
    total_link_active = db.Column(db.Integer, default=0)
    title = db.Column(db.String(255), nullable=False)
    subscription = db.Column(db.String(255), nullable=False)
    subscription_expired = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text)
    admin_description = db.Column(db.Text)
    value = db.Column(db.Text)
