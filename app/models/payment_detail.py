from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class PaymentDetail(db.Model, BaseModel):
    __tablename__ = "payment_details"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=True)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.now)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now
    )

    user = db.relationship("User", lazy="joined")
    payment = db.relationship("Payment", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "price": self.price,
            "amount": self.amount,
            "user_id": self.user_id,
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
