from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField


class RequestSocialLog(BaseDocument):
    meta = {
        "collection": "request_social_logs",
        "indexes": ["social", "type"],
    }

    social = StringField(required=True, max_length=50)
    social_post_id = IntField(required=True, default=0)
    user_id = IntField(required=True, default=0)
    type = StringField(required=True, max_length=50)
    request = StringField()
    response = StringField()
