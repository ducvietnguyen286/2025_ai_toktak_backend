from app.extensions import db
from app.models.base import BaseModel


class Link(db.Model, BaseModel):
    __tablename__ = "links"

    id = db.Column(db.Integer, primary_key=True)
    avatar = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    need_info = db.Column(db.Text, nullable=False)
    type = db.Column(db.Integer, default=1)
    status = db.Column(db.Integer, default=1)

    to_json_parse = ("need_info",)
