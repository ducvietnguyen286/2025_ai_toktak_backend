from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Payment(db.Model, BaseModel):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_id = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(255), nullable=False)
    package_name = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_status = db.Column(db.String(50), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.Integer, default=1)
    total_link = db.Column(db.Integer, default=0)
    total_create = db.Column(db.Integer, default=10)

    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    requested_at = db.Column(db.DateTime, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=False)
    fail_reason = db.Column(db.String(255), nullable=False)
