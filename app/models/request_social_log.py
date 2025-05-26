from app.extensions import db
from app.models.base import BaseModel


class RequestSocialLog(db.Model, BaseModel):
    __tablename__ = "request_social_logs"

    id = db.Column(db.Integer, primary_key=True)
    social = db.Column(db.String(50), nullable=False, max_length=50, index=True)
    social_post_id = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, default=0)
    type = db.Column(db.String(50), nullable=False, max_length=50, index=True)
    request = db.Column(db.Text)
    response = db.Column(db.Text)
