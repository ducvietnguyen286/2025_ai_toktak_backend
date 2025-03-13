from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField, ListField


class SocialSync(BaseDocument):
    meta = {
        "collection": "social_syncs",
    }

    user_id = IntField(required=True, default=0)
    in_post_ids = ListField(required=True, default=[])
    post_ids = ListField(required=True, default=[])
    social_post_ids = ListField(required=False, default=[])
    status = StringField(required=True, max_length=50)
    process_number = IntField(default=0)

    to_json_filter = "social_post_ids"
