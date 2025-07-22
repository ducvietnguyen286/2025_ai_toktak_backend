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
    icon = db.Column(db.String(255))
    redirect_type = db.Column(db.String(255))
    button_cancel = db.Column(db.String(255))
    button_oke = db.Column(db.String(255))
    description = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)
    ask_again = db.Column(db.Integer, default=0)
    repeat_duration = db.Column(db.Integer, default=0)
    
    
    popup_type = db.Column(db.String(255))
    toasts_color = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "country": self.country,
            "title": self.title,
            "url": self.url,
            "icon": self.icon,
            "redirect_type": self.redirect_type,
            "description": self.description,
            "status": self.status,
            "ask_again": self.ask_again,
            "repeat_duration": self.repeat_duration,
            "button_cancel": self.button_cancel,
            "button_oke": self.button_oke,
            "popup_type": self.popup_type,
            "toasts_color": self.toasts_color,
            
            
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
