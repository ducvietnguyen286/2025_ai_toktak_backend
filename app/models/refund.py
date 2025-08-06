from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Refund(db.Model, BaseModel):
    __tablename__ = "refunds"

    id = db.Column(db.BigInteger, primary_key=True)
    payment_id = db.Column(db.BigInteger, db.ForeignKey("payments.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False, default=0)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.SmallInteger, default=0)
    requested_at = db.Column(db.DateTime, default=datetime.now)
    processed_at = db.Column(db.DateTime, nullable=True)
    admin_note = db.Column(db.Text, nullable=True)

    package_name = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    type_payment = db.Column(db.String(255), nullable=False)

    user = db.relationship("User")
    payment = db.relationship("Payment")

    def to_dict(self):
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "package_name": self.package_name,
            "customer_name": self.customer_name,
            "user_name": self.user.name if self.user else None,
            "user_email": self.user.email if self.user else None,
            "current_user_subscription": self.user.subscription if self.user else None,
            "type_payment": self.type_payment,
            "user_id": self.user_id,
            "amount": self.amount,
            "reason": self.reason,
            "status": self.status,
            "requested_at": (
                self.requested_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.requested_at
                else None
            ),
            "processed_at": (
                self.processed_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.processed_at
                else None
            ),
            "created_at": (
                self.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.created_at
                else None
            ),
            "admin_note": self.admin_note,
        }
