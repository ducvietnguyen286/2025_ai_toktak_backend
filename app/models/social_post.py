from app.extensions import db
from app.models.base import BaseModel


class SocialPost(db.Model, BaseModel):
    __tablename__ = "social_posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, default=0, index=True)
    link_id = db.Column(db.Integer, default=0)
    post_id = db.Column(db.Integer, default=0)
    batch_id = db.Column(db.Integer, default=0)
    session_key = db.Column(db.String(100), max_length=100, index=True)
    sync_id = db.Column(db.Integer, default=0)
    social_link = db.Column(db.String(700), max_length=700, default="")
    status = db.Column(db.String(50), max_length=50, default="")
    error_message = db.Column(db.Text, default="")
    show_message = db.Column(db.Text, default="")
    disable_comment = db.Column(db.Integer, default=0)
    privacy_level = db.Column(db.String(50), max_length=50, default="SELF_ONLY")
    auto_add_music = db.Column(db.Integer, default=0)
    disable_duet = db.Column(db.Integer, default=0)
    disable_stitch = db.Column(db.Integer, default=0)
    process_number = db.Column(db.Integer, default=0)
    instagram_quote = db.Column(db.Text, default="")
