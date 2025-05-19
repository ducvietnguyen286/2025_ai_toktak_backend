from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField, ObjectIdField


class Notification(BaseDocument):
    meta = {"collection": "notifications"}

    notification_type = StringField(default="video")
    user_id = IntField(required=True, default=0)
    batch_id = ObjectIdField()
    post_id = ObjectIdField()
    thumbnail = StringField(max_length=500)
    images = StringField()
    captions = StringField()
    title = StringField(max_length=500)
    content = StringField()
    description = StringField()
    description_korea = StringField()
    hashtag = StringField()
    video_url = StringField(max_length=500)
    status = IntField(default=1)
    status_sns = IntField(default=0)
    is_read = IntField(default=0)
    send_telegram = IntField(default=0)
    render_id = StringField(max_length=500)

    social_sns_description = StringField(default="")

    to_json_parse = "images"
    to_json_filter = "captions"

    def to_dict(self):
        return {
            # "email": self.user.email if self.user else None,
            "id": self.id,
            "notification_type": self.notification_type,
            "user_id": self.user_id,
            "batch_id": self.batch_id,
            "post_id": self.post_id,
            "thumbnail": self.thumbnail,
            "captions": self.captions,
            "images": self.images,
            "title": self.title,
            "content": self.content,
            "description": self.description,
            "description_korea": self.description_korea,
            "hashtag": self.hashtag,
            "video_url": self.video_url,
            "status": self.status,
            "status_sns": self.status_sns,
            "render_id": self.render_id,
            "is_read": self.is_read,
            "social_sns_description": self.social_sns_description,
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
