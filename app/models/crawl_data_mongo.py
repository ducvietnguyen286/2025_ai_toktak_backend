from mongoengine import StringField, DateTimeField
from app.models.base_mongo import BaseDocument
from datetime import datetime

class CrawlDataMongo(BaseDocument):
    meta = {"collection": "crawl_datas"}

    site = StringField(required=True, max_length=100)
    input_url = StringField()
    crawl_url = StringField(required=True, max_length=500)
    crawl_url_hash = StringField(required=True, max_length=100)
    request = StringField()
    response = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
