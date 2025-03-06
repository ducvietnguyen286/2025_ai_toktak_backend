from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField


class SocialPost(BaseDocument):
    meta = {
        "collection": "social_posts",
        "indexes": ["session_key"],
    }

    user_id = IntField(required=True, default=0)
    link_id = IntField(required=True, default=0)
    post_id = IntField(required=True, default=0)
    batch_id = IntField(required=True, default=0)
    session_key = StringField(required=True, max_length=100)
    social_link = StringField(max_length=700, default="")
    status = StringField(required=True, max_length=50)
    error_message = StringField(default="")
    process_number = IntField(default=0)
