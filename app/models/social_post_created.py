from app.extensions import db
from app.models.base import BaseModel


class SocialPostCreated(db.Model, BaseModel):
    __tablename__ = "social_post_created"

    id = db.Column(db.Integer, primary_key=True)
    social = db.Column(db.String(50), nullable=False, max_length=50, index=True)
    user_id = db.Column(db.Integer, default=0, index=True)
    count = db.Column(db.Integer, default=0)
    day = db.Column(db.String(50), nullable=False, max_length=50)
