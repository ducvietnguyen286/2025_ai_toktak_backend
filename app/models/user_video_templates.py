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

    product_description = db.Column(db.String(500), default="", nullable=False)
    is_product_description = db.Column(db.Integer, default=0, nullable=False)

    product_pin = db.Column(db.String(500), default="", nullable=False)
    is_product_pin = db.Column(db.Integer, default=0, nullable=False)

    purchase_guide = db.Column(db.String(500), default="", nullable=False)
    narration = db.Column(db.String(10), default="male", nullable=False)
    is_purchase_guide = db.Column(db.Integer, default=0, nullable=False)
    voice_gender = db.Column(db.Integer, default=0, nullable=False)
    voice_id = db.Column(db.Integer, default=0, nullable=False)
    is_video_hooking = db.Column(db.Integer, default=0, nullable=False)
    is_caption_top = db.Column(db.Integer, default=0, nullable=False)
    is_caption_last = db.Column(db.Integer, default=0, nullable=False)
    image_template_id = db.Column(db.String(500), default="", nullable=False)

    image_template = db.Column(db.Text, nullable=False, default="")
    video_hooks = db.Column(db.Text, nullable=False, default="")
    viral_messages = db.Column(db.Text, nullable=False, default="")
    subscribe_video = db.Column(db.Text, nullable=False, default="")
    link_sns = db.Column(db.Text, nullable=False, default='{"video": [], "image": []}')

    is_comment = db.Column(db.Integer, default=0, nullable=False)
    comment = db.Column(db.String(255), default="", nullable=False)

    is_hashtag = db.Column(db.Integer, default=0, nullable=False)
    hashtag = db.Column(db.Text, nullable=False, default="[]")
    typecast_voice = db.Column(db.String(100), default="")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "is_paid_advertisements": self.is_paid_advertisements,
            "narration": self.narration,
            "product_name": self.product_name,
            "is_product_name": self.is_product_name,
            "product_description": self.product_description,
            "is_product_description": self.is_product_description,
            "is_product_pin": self.is_product_pin,
            "product_pin": self.product_pin,
            "purchase_guide": self.purchase_guide,
            "is_purchase_guide": self.is_purchase_guide,
            "voice_gender": self.voice_gender,
            "voice_id": self.voice_id,
            "is_video_hooking": self.is_video_hooking,
            "is_caption_top": self.is_caption_top,
            "is_caption_last": self.is_caption_last,
            "image_template_id": self.image_template_id,
            "image_template": json.loads(self.image_template),
            "video_hooks": json.loads(self.video_hooks),
            "viral_messages": json.loads(self.viral_messages),
            "link_sns": json.loads(self.link_sns),
            "comment": self.comment,
            "is_comment": self.is_comment,
            "is_hashtag": self.is_hashtag,
            "hashtag": json.loads(self.hashtag),
            "subscribe_video": self.subscribe_video,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
