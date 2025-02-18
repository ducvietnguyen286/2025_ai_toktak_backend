from app.extensions import db
from app.models.base import BaseModel


class UserLink(db.Model, BaseModel):
    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Integer, default=1)
