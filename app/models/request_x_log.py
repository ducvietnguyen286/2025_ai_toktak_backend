from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db


class RequestXLog(db.Model, BaseModel):
    __tablename__ = "request_x_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    request = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, default=1)
