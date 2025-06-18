from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class PaymentLog(db.Model, BaseModel):
    __tablename__ = "payment_logs"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=True)
    status_code = db.Column(db.Integer)
    response_json = db.Column(db.Text)  # Toàn bộ phản hồi từ Toss
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Quan hệ 1-n với Payment
    payment = db.relationship("Payment", backref="logs")

    def to_dict(self):
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "status_code": self.status_code,
            "response_json": self.response_json,
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
