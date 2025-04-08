from app.extensions import db, bcrypt
from app.models.base import BaseModel
from datetime import datetime

import const


class User(db.Model, BaseModel):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=True)
    name = db.Column(db.String(255), nullable=True, default="")
    avatar = db.Column(db.String(500), nullable=True, default="")
    username = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(200), nullable=True)
    status = db.Column(db.Integer, default=1)
    user_type = db.Column(db.Integer, default=0)

    phone = db.Column(db.String(255), nullable=True)
    contact = db.Column(db.String(255), nullable=True)
    company_name = db.Column(db.String(255), nullable=True)

    subscription = db.Column(db.String(255), nullable=False, default="FREE")
    subscription_expired = db.Column(db.DateTime, nullable=True)

    batch_total = db.Column(db.Integer, default=const.LIMIT_BATCH["FREE"])
    batch_remain = db.Column(db.Integer, default=const.LIMIT_BATCH["FREE"])

    batch_no_limit_sns = db.Column(db.Integer, default=0)
    batch_sns_total = db.Column(db.Integer, default=const.LIMIT_BATCH["FREE"] * 2)
    batch_sns_remain = db.Column(db.Integer, default=const.LIMIT_BATCH["FREE"] * 2)
    batch_of_month = db.Column(db.String(50), default="")

    level = db.Column(db.Integer, default=0)
    level_info = db.Column(db.Text, nullable=False)

    ali_express_active = db.Column(db.Boolean, default=False)
    ali_express_info = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    last_activated = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    print_filter = ("password",)
    to_json_filter = ("password", "ali_express_info")

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar": self.avatar,
            "username": self.username,
            "status": self.status,
            "phone": self.phone,
            "contact": self.contact,
            "level": self.level,
            "level_info": self.level_info,
            "company_name": self.company_name,
            "created_at": (
                self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.created_at
                else None
            ),
            "last_activated": (
                self.last_activated.strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.last_activated
                else None
            ),
            "updated_at": (
                self.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.updated_at
                else None
            ),
        }
