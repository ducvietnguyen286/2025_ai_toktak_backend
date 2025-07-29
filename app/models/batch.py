from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Batch(db.Model, BaseModel):
    __tablename__ = "batchs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    url = db.Column(db.String(2048), nullable=False)
    shorten_link = db.Column(db.String(200), nullable=True)
    thumbnail = db.Column(db.String(500), nullable=True, default="")
    thumbnails = db.Column(db.Text)
    content = db.Column(db.Text, nullable=True)

    type = db.Column(db.Integer, default=1)
    count_post = db.Column(db.Integer, default=0)
    done_post = db.Column(db.Integer, default=0)
    status = db.Column(db.Integer, default=1)
    is_paid_advertisements = db.Column(db.Integer, default=0)
    is_advance = db.Column(db.Integer, default=0)
    voice_google = db.Column(db.Integer, default=1)
    voice_typecast = db.Column(db.String(100), default="")
    voice = db.Column(db.String(100), default="")
    voice_type = db.Column(db.String(100), default="")
    process_status = db.Column(db.String(50), default="PENDING")

    error_code = db.Column(db.String(50), nullable=True)
    message = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    template_info = db.Column(db.Text, nullable=True)

    to_json_filter = ("content", "thumbnails")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "content": self.content,
            "type": self.type,
            "count_post": self.count_post,
            "done_post": self.done_post,
            "status": self.status,
            "process_status": self.process_status,
            "voice_google": self.voice_google,
            "is_paid_advertisements": self.is_paid_advertisements,
            "is_advance": self.is_advance,
            "template_info": self.template_info,
            "voice": self.voice,
            "voice_type": self.voice_type,
            "error_code": self.error_code,
            "message": self.message,
            "error_message": self.error_message,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
