from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class ReferralHistory(db.Model, BaseModel):
    __tablename__ = "referral_history"

    id = db.Column(db.Integer, primary_key=True)
    referral_code = db.Column(db.String(255), nullable=False)
    referrer_user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )  # người giới thiệu
    referred_user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )  # người được mời

    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    referrer = db.relationship("User", foreign_keys=[referrer_user_id])
    referred_user = db.relationship("User", foreign_keys=[referred_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "referrer_user_id ": self.referrer_user_id,
            "referrer_email": self.referrer.email if self.referrer else None,
            "referred_user_id": self.referred_user_id,
            "referred_user_email": (
                self.referred_user.email if self.referred_user else None
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
