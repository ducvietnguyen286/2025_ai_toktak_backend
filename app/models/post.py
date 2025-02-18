from app.extensions import db
from app.models.base import BaseModel


class Post(db.Model, BaseModel):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batchs.id"), nullable=False)
    thumbnail = db.Column(db.String(500), nullable=False, default="")
    title = db.Column(db.String(500), nullable=False, default="")
    subtitle = db.Column(db.String(500), nullable=False, default="")
    content = db.Column(db.Text, nullable=False, default="")
    hashtag = db.Column(db.String(500), nullable=False, default="")
    video_path = db.Column(db.String(255), nullable=False, default="")
    type = db.Column(db.String(10), default="video", index=True)
    status = db.Column(db.Integer, default=1)
