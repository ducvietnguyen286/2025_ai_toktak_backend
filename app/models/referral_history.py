from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class ReferralHistory(db.Model, BaseModel):
    __tablename__ = "referral_history"

    id = db.Column(db.Integer, primary_key=True)
    referral_code = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(255), nullable=False, default="PENDING")

    referrer_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    referred_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    days = db.Column(db.Integer, nullable=False, default=7)

    expired_at = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now
    )

    referrer = db.relationship(
        "User",
        foreign_keys=[referrer_user_id],
    )
    referred_user = db.relationship(
        "User",
        foreign_keys=[referred_user_id],
    )

    def to_dict(self):
        return {
            "id": self.id,
            "referrer_user_id": self.referrer_user_id,
            "referrer_email": self.referrer.email if self.referrer else None,
            "referred_user_id": self.referred_user_id,
            "referral_code": self.referral_code,
            "status": self.status,
            "referred_user_email": (
                self.referred_user.email if self.referred_user else None
            ),
            "referred_user_name": (
                self.referred_user.name if self.referred_user else None
            ),
            "expired_at": (
                self.expired_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.expired_at
                else None
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
            "updated_at_view": (
                self.updated_at.strftime("%Y-%m-%d") if self.updated_at else None
            ),
        }
