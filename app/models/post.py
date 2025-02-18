from app.extensions import db
from app.models.base import BaseModel


class Post(db.Model, BaseModel):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batchs.id"), nullable=False)
    thumbnail = db.Column(db.String(500), nullable=True)
    title = db.Column(db.String(500), nullable=False)
    subtitle = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text, nullable=True)
    video_path = db.Column(db.String(255), nullable=False)
    type = db.Column(db.Integer, default=1)
    status = db.Column(db.Integer, default=1)
