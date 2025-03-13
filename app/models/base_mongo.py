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

    to_json_filter = ()

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(BaseDocument, self).save(*args, **kwargs)

    def update(self, **kwargs):
        return super().update(**kwargs)

    def to_dict(self):
        return self.to_mongo().to_dict()

    def to_json(self):
        response = {}
        for column, value in self.to_dict().items():
            if column in self.to_json_filter:
                continue
            if column == "_id":
                response["id"] = str(value)
            elif column == "created_at" or column == "updated_at":
                response[column] = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                response[column] = value

        return response
