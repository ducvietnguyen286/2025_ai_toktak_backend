from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Schedules(db.Model, BaseModel):
    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    type_schedule = db.Column(db.Integer, default=1)
    status = db.Column(db.Integer, default=1)
    template_info = db.Column(db.Text, nullable=True) 
    link_sns = db.Column(db.Text, nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.now)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now
    )

    # to_json_filter = ("template_info",)
