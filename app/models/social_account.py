from app.extensions import db, bcrypt
from app.models.base import BaseModel


class SocialAccount(db.Model, BaseModel):
    __tablename__ = "social_accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    provider = db.Column(db.String(50), index=True, nullable=False)
    provider_user_id = db.Column(db.String(100), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    access_token_expired = db.Column(db.String(100), nullable=True)
    refresh_token_expired = db.Column(db.String(100), nullable=True)
