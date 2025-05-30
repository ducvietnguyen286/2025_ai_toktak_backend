from app.extensions import db
from app.models.base import BaseModel


class OCRResult(db.Model, BaseModel):
    __tablename__ = "ocr_results"

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.Text)
    image_hash = db.Column(db.String(200), index=True)
    response = db.Column(db.Text)
    status = db.Column(db.Integer, default=1)
