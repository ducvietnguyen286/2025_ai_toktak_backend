from app.extensions import db
from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField


class Batch(BaseDocument):
    meta = {"collection": "batchs"}

    user_id = IntField(required=True, default=0)
    url = StringField(required=True, max_length=500)
    shorten_link = StringField(required=True, max_length=200, default="")
    thumbnail = StringField(max_length=500)
    thumbnails = StringField()
    content = StringField()

    type = IntField(required=False, default=1)
    count_post = IntField(required=False, default=0)
    done_post = IntField(required=False, default=0)
    status = IntField(required=False, default=1)
    is_paid_advertisements = IntField(required=False, default=0)
    is_advance = IntField(required=False, default=0)
    voice_google = IntField(required=False, default=1)
    process_status = StringField(max_length=50, default="PENDING")
    template_info = StringField()

    to_json_filter = ("content", "thumbnails")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "content": self.content,
            "type": self.type,
            "count_post": self.count_post,
            "done_post": self.done_post,
            "status": self.status,
            "process_status": self.process_status,
            "voice_google": self.voice_google,
            "is_paid_advertisements": self.is_paid_advertisements,
            "is_advance": self.is_advance,
            "template_info": self.template_info,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
