from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from app.models.base import BaseModel

db = SQLAlchemy()



class VideoCreate(db.Model, BaseModel):
    __tablename__ = "video_create"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # ID người dùng
    product_name = db.Column(db.String(255), nullable=False)  # Tên sản phẩm
    images_url = db.Column(db.JSON, nullable=False)  # Danh sách URL ảnh
    render_id = db.Column(db.String(100), default="", nullable=False)  # render id
    status = db.Column(db.String(50), default="queued", nullable=False)  # Trạng thái
    description = db.Column(db.Text, nullable=True)  # Mô tả
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )  # Ngày cập nhật

 