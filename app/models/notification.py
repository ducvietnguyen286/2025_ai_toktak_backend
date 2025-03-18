from app.extensions import db
from app.models.base import BaseModel


class Notification(db.Model, BaseModel):
    __tablename__ = "notifications"

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

    social_sns_description = db.Column(db.Text, nullable=True)

    to_json_parse = "images"
    to_json_filter = "captions"

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "ai_type": self.ai_type,
            "request": self.request,
            "response": self.response,
            "status": self.status,
            "status_sns": self.status_sns,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
