# coding: utf8
from datetime import datetime
import json
import os

import pytz
from sqlalchemy import inspect

from app.extensions import db


class BaseModel:
    __abstract__ = True

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    print_filter = ()
    to_json_filter = ()
    to_json_parse = ()

    def __repr__(self):
        """Define a base way to print models
        Columns inside `print_filter` are excluded"""
        return "%s(%s)" % (
            self.__class__.__name__,
            {
                column: value
                for column, value in self.to_dict().items()
                if column not in self.print_filter
            },
        )

    def _to_json(self):
        """Define a base way to jsonify models
        Columns inside `to_json_filter` are excluded"""
        # timezone = os.environ.get("TZ", "UTC")
        timezone = "UTC"
        tz = pytz.timezone(timezone)

        response = {}
        for column, value in self._to_dict().items():
            # Bỏ qua các thuộc tính liên kết (relation)
            if isinstance(value, db.Model):
                continue  # Bỏ qua các thuộc tính liên kết

            if isinstance(value, list) and all(
                isinstance(item, db.Model) for item in value
            ):
                continue  # Bỏ qua danh sách chứa các đối tượng liên kết (1-N, N-N)

            if column in self.to_json_filter:
                continue
            if column in self.to_json_parse:
                if value and isinstance(value, str):
                    response[column] = json.loads(value)
            elif isinstance(value, datetime):
                if value.tzinfo is None:
                    value = pytz.utc.localize(value)  # Fix lỗi lệch giờ
                response[column] = value.astimezone(tz).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                response[column] = value

        return response

    def _to_dict(self):
        """This would more or less be the same as a `to_json`
        But putting it in a "private" function
        Allows to_json to be overriden without impacting __repr__
        Or the other way around
        And to add filter lists"""
        return {
            column.key: getattr(self, column.key)
            for column in inspect(self.__class__).attrs
        }

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def expunge(self):
        db.session.expunge(self)
        return self

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def soft_delete(self):
        setattr(self, "deleted_at", datetime.now())
        db.session.commit()
        return self
