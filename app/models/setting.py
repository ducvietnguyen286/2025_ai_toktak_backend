from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db


class Setting(db.Model, BaseModel):
    __tablename__ = "setting"

    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(500), nullable=False)  # Tên sản phẩm
    setting_value = db.Column(db.String(500), nullable=False)
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
