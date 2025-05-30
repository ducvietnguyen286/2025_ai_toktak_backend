from app.extensions import db
from app.models.base import BaseModel


class RequestSocialCount(db.Model, BaseModel):
    __tablename__ = "request_social_counts"

    id = db.Column(db.Integer, primary_key=True)
    social = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, default=0, index=True)
    count = db.Column(db.Integer, default=0)
    day = db.Column(db.String(50), nullable=False)
    hour = db.Column(db.String(50), nullable=False)
