from app.extensions import db
from app.models.base import BaseModel


class SocialPost(db.Model, BaseModel):
    __tablename__ = "social_posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    link_id = db.Column(db.Integer, db.ForeignKey("links.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    social_link = db.Column(db.String(700), nullable=True, default="")
    status = db.Column(db.String(50), nullable=False, default="")
    error_message = db.Column(db.Text, nullable=True)
    process_number = db.Column(db.Integer, nullable=True)
    
    # Nếu cần thiết, bạn có thể thêm relationship
    link = db.relationship('Link', backref=db.backref('social_posts', lazy=True))
