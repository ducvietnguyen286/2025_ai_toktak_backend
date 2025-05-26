from app.extensions import db
from app.models.base import BaseModel


class SocialSync(db.Model, BaseModel):
    __tablename__ = "social_syncs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, default=0, index=True)
    in_post_ids = db.Column(db.Text)
    post_ids = db.Column(db.Text)
    social_post_ids = db.Column(db.Text)
    status = db.Column(db.String(50), default="")
    process_number = db.Column(db.Integer, default=0)

    to_json_filter = (social_post_ids, in_post_ids, post_ids)
