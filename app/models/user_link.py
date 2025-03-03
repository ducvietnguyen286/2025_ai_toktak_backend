from app.extensions import db
from app.models.base import BaseModel


class UserLink(db.Model, BaseModel):
    __tablename__ = "user_links"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    link_id = db.Column(db.Integer, db.ForeignKey("links.id"), nullable=False)
    meta = db.Column(db.Text, nullable=False)
    expired_at = db.Column(db.DateTime, nullable=True)
    expired_date = db.Column(db.Date, nullable=True, index=True)
    status = db.Column(db.Integer, default=1)

    to_json_filter = ("meta", "expired_at", "expired_date")
