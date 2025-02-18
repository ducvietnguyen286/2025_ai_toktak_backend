from app.extensions import db
from app.models.base import BaseModel


class Video(db.Model, BaseModel):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Integer, default=1)
    status = db.Column(db.Integer, default=1)
