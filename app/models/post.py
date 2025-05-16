from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime
import pytz
import json


class Post(db.Model, BaseModel):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batchs.id"), nullable=False)
    thumbnail = db.Column(db.String(500), nullable=False, default="")
    captions = db.Column(db.Text, nullable=True)
    images = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(500), nullable=False, default="")
    subtitle = db.Column(db.String(500), nullable=False, default="")
    content = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, default="")
    hashtag = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(255), nullable=False, default="")
    docx_url = db.Column(db.String(255), default="")
    file_size = db.Column(db.String(50), default="")
    mime_type = db.Column(db.String(250), default="")
    type = db.Column(db.String(10), default="video", index=True)
    status = db.Column(db.Integer, default=1)
    status_sns = db.Column(db.Integer, default=0)
    process_number = db.Column(db.Integer, default=0)
    render_id = db.Column(db.String(500), nullable=False, default="")
    video_path = db.Column(db.String(255), nullable=False, default="")

    social_sns_description = db.Column(db.Text, nullable=True)
    schedule_date = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )  #

    user = db.relationship("User", lazy="joined")

    to_json_parse = "images"
    to_json_filter = "captions"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "batch_id": self.batch_id,
            "thumbnail": self.thumbnail,
            "captions": self.captions,
            "images": json.loads(self.images),
            "title": self.title,
            "subtitle": self.subtitle,
            "content": self.content,
            "description": self.description,
            "hashtag": self.hashtag,
            "video_url": self.video_url,
            "docx_url": self.docx_url,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "type": self.type,
            "status": self.status,
            "status_sns": self.status_sns,
            "process_number": self.process_number,
            "render_id": self.render_id,
            "video_path": self.video_path,
            "social_sns_description": self.social_sns_description,
            "user_email": self.user.email if self.user else None,  # Lấy email từ user
            "schedule_date": (
                pytz.utc.localize(self.schedule_date).strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.schedule_date
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
        }
