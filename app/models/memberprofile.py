from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime
import json

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
    created_at = db.Column(db.DateTime, default=datetime.now)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now
    )  #
    
    
    social_is_thread = db.Column(db.Integer, default=0)
    social_thread_url = db.Column(db.String(500), nullable=False, default="")
    social_is_youtube = db.Column(db.Integer, default=0)
    social_youtube_url = db.Column(db.String(500), nullable=False, default="")
    social_is_x = db.Column(db.Integer, default=0)
    social_x_url = db.Column(db.String(500), nullable=False, default="")
    social_is_instagram = db.Column(db.Integer, default=0)
    social_instalgram_url = db.Column(db.String(500), nullable=False, default="")
    social_is_tiktok = db.Column(db.Integer, default=0)
    social_tiktok_url = db.Column(db.String(500), nullable=False, default="")
    social_is_facebook = db.Column(db.Integer, default=0)
    social_facebook_url = db.Column(db.String(500), nullable=False, default="")

    user = db.relationship("User", lazy="joined")

    to_json_parse = "design_settings"
    # to_json_filter = "captions"
    

    def to_dict(self):
        design_settings = json.loads(self.design_settings)
        
        return {
            "id": self.id,
            "user_id": self.user_id,
            "nick_name": self.nick_name,
            "member_name": self.member_name,
            "member_avatar": self.member_avatar,
            "content": self.content,
            "design_settings": design_settings,
            "description": self.description,
            "status": self.status,
            "social_is_thread": self.social_is_thread,
            "social_thread_url": self.social_thread_url,
            "social_is_youtube": self.social_is_youtube,
            "social_youtube_url": self.social_youtube_url,
            "social_is_x": self.social_is_x,
            "social_x_url": self.social_x_url,
            "social_is_instagram": self.social_is_instagram,
            "social_instalgram_url": self.social_instalgram_url,
            "social_is_tiktok": self.social_is_tiktok,
            "social_tiktok_url": self.social_tiktok_url,
            "social_is_facebook": self.social_is_facebook,
            "social_facebook_url": self.social_facebook_url,
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
