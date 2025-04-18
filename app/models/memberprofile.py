from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class MemberProfile(db.Model, BaseModel):
    __tablename__ = "member_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    nick_name = db.Column(db.String(500), nullable=False, default="")
    member_name = db.Column(db.String(500), nullable=False, default="")
    member_avatar = db.Column(db.String(500), nullable=False, default="")
    member_address = db.Column(db.Text, nullable=True)
    design_settings = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, default="")
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )  #

    user = db.relationship("User", lazy="joined")

    to_json_parse = "design_settings"
    # to_json_filter = "captions"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "nick_name": self.nick_name,
            "member_name": self.member_name,
            "member_avatar": self.member_avatar,
            "content": self.content,
            "design_settings": self.design_settings,
            "description": self.description,
            "status": self.status,
            "user_email": self.user.email if self.user else None,  # Lấy email từ user
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
