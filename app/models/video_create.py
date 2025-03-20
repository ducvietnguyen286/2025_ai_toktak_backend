from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db



class VideoCreate(db.Model, BaseModel):
    __tablename__ = "video_create"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # ID người dùng
    post_id = db.Column(db.Integer, nullable=False)  # ID Port
    product_name = db.Column(db.String(500), nullable=False)  # Tên sản phẩm
    video_url = db.Column(db.String(500), nullable=False)   
    google_driver_url = db.Column(db.String(500), nullable=False)   
    hash_tags = db.Column(db.String(500), nullable=False)  # Tên sản phẩm
    images_url = db.Column(db.Text, nullable=False)  # Danh sách URL ảnh
    render_id = db.Column(db.String(100), default="", nullable=False)  # render id
    status = db.Column(db.String(50), default="queued", nullable=False)  # Trạng thái
    description = db.Column(db.Text, nullable=True)  # Mô tả
    captions = db.Column(db.Text, nullable=True)  # Mô tả
    origin_caption = db.Column(db.Text, nullable=True)  # Mô tả
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )  # Ngày cập nhật
    
    def to_dict(self):
        return {
            "id": self.id,
            "render_id": self.render_id,
            "user_id": self.user_id,
            "product_name": self.product_name,
            "hash_tags": self.hash_tags,
            "images_url": self.images_url,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }