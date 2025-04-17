from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField, ListField


class YoutubeClient(BaseDocument):
    meta = {"collection": "youtube_clients"}

    user_ids = ListField(default=[])
    member_count = IntField(default=0)
    project_name = StringField(max_length=100)
    client_id = StringField(required=True, max_length=150)
    client_secret = StringField(required=True, max_length=150)
