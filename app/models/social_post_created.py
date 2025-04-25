from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField


class SocialPostCreated(BaseDocument):
    meta = {
        "collection": "social_post_created",
        "indexes": [
            {
                "fields": ["user_id", "social", "day"],
                "unique": True,
                "sparse": True,
            }
        ],
    }

    social = StringField(required=True, max_length=50)
    user_id = IntField(required=True, default=0)
    count = IntField(required=True, default=0)
    day = StringField(required=True, max_length=50)
