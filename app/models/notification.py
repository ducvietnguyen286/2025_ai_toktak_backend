from app.extensions import db
from app.models.base import BaseModel


class Notification(db.Model, BaseModel):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(500), nullable=False, default="video")
    user_id = db.Column(db.Integer, nullable=False)
    batch_id = db.Column(db.Integer, nullable=False)
    post_id = db.Column(db.Integer, nullable=False)
    thumbnail = db.Column(db.String(500), nullable=False, default="")
    images = db.Column(db.Text, nullable=True)
    captions = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(500), nullable=False, default="")
    content = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, default="")
    hashtag = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(255), nullable=False, default="")
    type = db.Column(db.String(10), default="video", index=True)
    status = db.Column(db.Integer, default=1)
    status_sns = db.Column(db.Integer, default=0)
    render_id = db.Column(db.String(500), nullable=False, default="")

    social_sns_description = db.Column(db.Text, nullable=True)

    to_json_parse = "images"
    to_json_filter = "captions"

    def to_dict(self):
        return {
            "id": self.id,
            "notification_type": self.notification_type,
            "user_id": self.user_id,
            "batch_id": self.batch_id,
            "post_id": self.post_id,
            "thumbnail": self.thumbnail,
            "captions": self.captions,
            "images": self.images,
            "title": self.title,
            "content": self.content,
            "description": self.description,
            "hashtag": self.hashtag,
            "video_url": self.video_url,
            "type": self.type,
            "status": self.status,
            "status_sns": self.status_sns,
            "render_id": self.render_id,
            "social_sns_description": self.social_sns_description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
