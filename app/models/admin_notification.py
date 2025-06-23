from app.extensions import db
from app.models.base import BaseModel
import const
from datetime import datetime
from app.models.coupon import Coupon
from app.models.user import User


class AdminNotification(db.Model, BaseModel):
    __tablename__ = "admin_notification"
    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(255))
    title = db.Column(db.String(255))
    url = db.Column(db.String(255))
    description = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    
    def to_dict(self):
        return {
            "id": self.id,
            "country": self.country,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }