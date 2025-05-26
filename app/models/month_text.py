from app.extensions import db
from app.models.base import BaseModel


class MonthText(db.Model, BaseModel):
    __tablename__ = "month_texts"

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(255), default="")
    hashtag = db.Column(db.String(255), default="")
    month = db.Column(db.String(50), nullable=False, index=True)
    status = db.Column(db.String(50), nullable=False, default="ACTIVE")
