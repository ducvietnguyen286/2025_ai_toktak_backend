from app.models.base_mongo import BaseDocument
from mongoengine import StringField


class MonthText(BaseDocument):
    meta = {
        "collection": "month_texts",
        "indexes": ["month"],
    }
    keyword = StringField(default="")
    hashtag = StringField(default="")
    month = StringField(required=True, max_length=50)
    status = StringField(required=True, max_length=50, default="ACTIVE")
