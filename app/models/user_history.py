from app.extensions import db
from app.models.base import BaseModel


class UserHistory(db.Model, BaseModel):
    __tablename__ = "user_histories"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(500))
    type_2 = db.Column(db.String(500))
    object_id = db.Column(db.Integer, default=0)
    object_start_time = db.Column(db.DateTime)
    object_end_time = db.Column(db.DateTime)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    admin_description = db.Column(db.Text)
    value = db.Column(db.Text)
    num_days = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    total_link_active = db.Column(db.Integer, default=0)
