import datetime
from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField


class ShortenURL(BaseDocument):
    meta = {
        "collection": "shorten_urls",
        "indexes": [
            "original_url_hash",
            "short_code",
        ],
    }

    original_url = StringField(required=True)
    original_url_hash = StringField(required=True, max_length=100)
    short_code = StringField(required=True, max_length=20, unique=True)
    status = IntField(default=1)

    def to_dict(self):
        return {
            "id": self._id,
            "original_url": self.original_url,
            "short_code": self.short_code,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
