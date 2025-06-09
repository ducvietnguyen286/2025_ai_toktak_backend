from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db


class Caption(db.Model, BaseModel):
    __tablename__ = "captions"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False) 
    type_content = db.Column(db.Integer, default=1)
    status = db.Column(db.Integer, default=1)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now
    )
