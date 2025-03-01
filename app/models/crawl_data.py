from app.extensions import db
from app.models.base import BaseModel


class CrawlData(db.Model, BaseModel):
    __tablename__ = "crawl_datas"

    id = db.Column(db.Integer, primary_key=True)
    site = db.Column(db.String(100), nullable=False)
    input_url = db.Column(db.Text)
    crawl_url = db.Column(db.String(500), nullable=False)
    crawl_url_hash = db.Column(db.String(100), index=True, nullable=False)
    request = db.Column(db.Text)
    response = db.Column(db.Text)
