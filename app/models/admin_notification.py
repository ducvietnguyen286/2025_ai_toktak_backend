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
