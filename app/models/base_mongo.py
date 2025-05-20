from datetime import datetime
from datetime import timezone

from bson import ObjectId
from app.extensions import db_mongo
from mongoengine import DateTimeField, get_db

from app.lib.logger import logger


class BaseDocument(db_mongo.Document):
    meta = {
        "abstract": True,  # Model này không tạo collection riêng
        "collection": "my_collection",  # Nếu model con không đặt lại, sẽ dùng tên này
    }
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    to_json_filter = ()

    def save(self, *args, **kwargs):
        try:
            with get_db().client.start_session() as session:
                with session.start_transaction():
                    self.updated_at = datetime.utcnow()
                    return super(BaseDocument, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            raise

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
            elif type(value) == ObjectId:
                response[column] = str(value)
            elif isinstance(value, datetime):
                new_value = self.format_utc_datetime(value)
                response[column] = new_value
            else:
                response[column] = value

        return response

    @staticmethod
    def format_utc_datetime(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
