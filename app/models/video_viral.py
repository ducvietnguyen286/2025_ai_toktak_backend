from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db


class VideoViral(db.Model, BaseModel):
    __tablename__ = "video_viral"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    video_name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(500), nullable=False)
    video_url = db.Column(db.String(500), nullable=False)
    status = db.Column(db.Integer)
    duration = db.Column(db.Float )
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now
    )

    def to_dict(self):
        return {
            "id": self.id,
            "video_name": self.video_name,
            "video_url": self.video_url,
            "status": self.status,
            "type": self.type,
            "duration": self.duration,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
