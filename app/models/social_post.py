from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField, BooleanField


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
    sync_id = StringField(required=False, max_length=100)
    social_link = StringField(max_length=700, default="")
    status = StringField(required=True, max_length=50)
    error_message = StringField(default="")
    show_message = StringField(default="")
    disable_comment = BooleanField(default=False)
    privacy_level = StringField(default="SELF_ONLY")
    auto_add_music = BooleanField(default=False)
    disable_duet = BooleanField(default=False)
    disable_stitch = BooleanField(default=False)
    process_number = IntField(default=0)
