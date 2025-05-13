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
    
    status = db.Column(db.String(255), default='PENDING')
    total_link = db.Column(db.Integer, default=0)
    total_create = db.Column(db.Integer, default=10)

    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    requested_at = db.Column(db.DateTime, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=False)
    fail_reason = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship("User", lazy="joined")

    def to_dict(self):
        return {
            "email": self.user.email if self.user else None,
            "id": self.id,
            "order_id": self.order_id,
            "method": self.method,
            "user_id": self.user_id,
            "customer_name": self.customer_name,
            "package_name": self.package_name,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "price": self.price,
            "amount": self.amount,
            "status": self.status,
            "total_link": self.total_link,
            "total_create": self.total_create,
            "status": self.status,
            "fail_reason": self.fail_reason,
            "requested_at": (
                self.requested_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.requested_at
                else None
            ),
            "approved_at": (
                self.approved_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.approved_at
                else None
            ),
            "payment_date": (
                self.payment_date.strftime("%Y-%m-%d %H:%M:%S")
                if self.payment_date
                else None
            ),
            "start_date": (
                self.start_date.strftime("%Y-%m-%d %H:%M:%S")
                if self.start_date
                else None
            ),
            "end_date": (
                self.end_date.strftime("%Y-%m-%d %H:%M:%S") if self.end_date else None
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
