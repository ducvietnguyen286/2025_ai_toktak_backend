from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField


class RequestSocialCount(BaseDocument):
    meta = {
        "collection": "request_social_counts",
        "indexes": [{"fields": ["user_id", "social", "day", "hour"]}],
    }

    social = StringField(required=True, max_length=50)
    user_id = IntField(required=True, default=0)
    count = IntField(required=True, default=0)
    day = StringField(required=True, max_length=50)
    hour = StringField(required=True, max_length=50)
