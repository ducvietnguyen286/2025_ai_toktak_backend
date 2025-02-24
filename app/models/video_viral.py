from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db


class VideoViral(db.Model, BaseModel):
    __tablename__ = "video_viral"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    video_url = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="queued")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "video_url": self.video_url,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
