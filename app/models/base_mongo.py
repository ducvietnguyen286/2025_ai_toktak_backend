from datetime import datetime
from app.extensions import db_mongo
from mongoengine import DateTimeField


class BaseDocument(db_mongo.Document):
    meta = {
        "abstract": True,  # Model này không tạo collection riêng
        "collection": "my_collection",  # Nếu model con không đặt lại, sẽ dùng tên này
    }
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(BaseDocument, self).save(*args, **kwargs)

    def update(self, **kwargs):
        return super().update(**kwargs)

    def to_dict(self):
        return self.to_mongo().to_dict()

    def to_json(self):
        return self.to_dict()
