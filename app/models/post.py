from app.models.base_mongo import BaseDocument
import pytz
from mongoengine import StringField, IntField, ObjectIdField


class Post(BaseDocument):
    meta = {"collection": "posts"}

    user_id = IntField(required=True, default=0)
    batch_id = ObjectIdField(required=True)
    thumbnail = StringField(required=True, default="")
    captions = StringField()
    images = StringField()
    title = StringField(required=True, default="")
    subtitle = StringField(required=True, default="")
    content = StringField()
    description = StringField()
    hashtag = StringField()
    hooking = StringField()
    video_url = StringField(default="")
    docx_url = StringField(default="")
    file_size = IntField(default=0)
    mime_type = StringField(default="")
    type = StringField(required=True, default="video")
    status = IntField(required=True, default=1)
    status_sns = IntField(default=0)
    process_number = IntField(default=0)
    render_id = StringField(default="")
    video_path = StringField(default="")

    social_sns_description = StringField(default="")
    schedule_date = StringField(default="")

    to_json_parse = "images"
    to_json_filter = "captions"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "batch_id": self.batch_id,
            "thumbnail": self.thumbnail,
            "captions": self.captions,
            "images": self.images,
            "title": self.title,
            "subtitle": self.subtitle,
            "content": self.content,
            "description": self.description,
            "hashtag": self.hashtag,
            "video_url": self.video_url,
            "docx_url": self.docx_url,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "type": self.type,
            "status": self.status,
            "status_sns": self.status_sns,
            "process_number": self.process_number,
            "render_id": self.render_id,
            "video_path": self.video_path,
            "social_sns_description": self.social_sns_description,
            "user_email": None,  # Lấy email từ user
            "schedule_date": (
                pytz.utc.localize(self.schedule_date).strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.schedule_date
                else None
            ),
            "created_at": (
                self.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.updated_at
                else None
            ),
        }
