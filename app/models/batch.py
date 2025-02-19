from app.extensions import db
from app.models.base import BaseModel


class Batch(db.Model, BaseModel):
    __tablename__ = "batchs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    url = db.Column(db.String(100), nullable=False)
    thumbnail = db.Column(db.String(500), nullable=True, default="")
    content = db.Column(db.Text, nullable=True)
    type = db.Column(db.Integer, default=1)
    count_post = db.Column(db.Integer, default=0)
    done_post = db.Column(db.Integer, default=0)
    status = db.Column(db.Integer, default=1)

    to_json_filter = "content"
