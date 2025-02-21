from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db


class TiktokCallback(db.Model, BaseModel):
    __tablename__ = "tiktok_callback"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False)
    state = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, default=1)
    error = db.Column(db.Text, nullable=False)
    error_description = db.Column(db.Text, nullable=False)
