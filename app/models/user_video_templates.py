from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db
import json


class UserVideoTemplates(db.Model, BaseModel):
    __tablename__ = "user_video_templates"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, default=0, nullable=False)
    is_paid_advertisements = db.Column(db.Integer, default=0, nullable=False)

    product_name = db.Column(db.String(500), default="", nullable=False)
    is_product_name = db.Column(db.Integer, default=0, nullable=False)

    purchase_guide = db.Column(db.String(500), default="", nullable=False)
    is_purchase_guide = db.Column(db.Integer, default=0, nullable=False)
    voice_gender = db.Column(db.Integer, default=0, nullable=False)
    voice_id = db.Column(db.Integer, default=0, nullable=False)
    is_video_hooking = db.Column(db.Integer, default=0, nullable=False)
    is_caption_top = db.Column(db.Integer, default=0, nullable=False)
    is_caption_last = db.Column(db.Integer, default=0, nullable=False)
    image_caption_type = db.Column(db.Integer, default=0, nullable=False)

    image_template = db.Column(db.Text, nullable=False, default="")
    video_hooks = db.Column(db.Text, nullable=False, default="")
    viral_messages = db.Column(db.Text, nullable=False, default="")
    subscribe_video = db.Column(db.Text, nullable=False, default="")

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "is_paid_advertisements": self.is_paid_advertisements,
            "product_name": self.product_name,
            "is_product_name": self.is_product_name,
            "purchase_guide": self.purchase_guide,
            "is_purchase_guide": self.is_purchase_guide,
            "voice_gender": self.voice_gender,
            "voice_id": self.voice_id,
            "is_video_hooking": self.is_video_hooking,
            "is_caption_top": self.is_caption_top,
            "is_caption_last": self.is_caption_last,
            "image_caption_type": self.image_caption_type,
            "image_template": json.loads(self.image_template),
            "video_hooks": json.loads(self.video_hooks),
            "viral_messages": json.loads(self.viral_messages),
            "subscribe_video": self.subscribe_video,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
