from app.extensions import db
from app.models.base import BaseModel


class RequestLog(db.Model, BaseModel):
    __tablename__ = "request_logs"

    id = db.Column(db.Integer, primary_key=True)
    ai_type = db.Column(db.String(10), nullable=False, index=True)
    request = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    status = db.Column(db.Integer, default=1)
