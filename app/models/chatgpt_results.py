from app.extensions import db
from app.models.base import BaseModel


class ChatGPTResult(db.Model, BaseModel):
    __tablename__ = "chatgpt_results"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False, index=True)
    link_type = db.Column(db.String(50), index=True)
    link = db.Column(db.Text)
    item_id = db.Column(db.String(50), index=True)
    vendor_id = db.Column(db.String(50), index=True)
    name = db.Column(db.Text)
    name_hash = db.Column(db.String(200), index=True)
    response = db.Column(db.Text, nullable=False)
    status = db.Column(db.Integer, default=1)
