# coding: utf8
from datetime import datetime

from sqlalchemy import inspect

from app.extensions import db


class BaseModel:
    __abstract__ = True

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    print_filter = ()
    to_json_filter = ()

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
        return {
            column: (
                value if not isinstance(value, datetime) else value.strftime("%Y-%m-%d")
            )
            for column, value in self._to_dict().items()
            if column not in self.to_json_filter
        }

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

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()
