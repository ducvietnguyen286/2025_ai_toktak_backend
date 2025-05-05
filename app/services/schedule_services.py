from app.models.user import User
from app.models.post import Post
from app.models.link import Link
from app.models.schedule import Schedules
from app.extensions import db
from sqlalchemy import and_, func, or_
from flask import jsonify
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased
import os
import json
import const
import hashlib
from app.models.batch import Batch
from app.lib.logger import logger


class ScheduleService:

    @staticmethod
    def create_schedule(*args, **kwargs):
        schedule_detail = Schedules(*args, **kwargs)
        schedule_detail.save()
        return schedule_detail

    @staticmethod
    def find_schedule(id):
        return Schedules.query.get(id)

    @staticmethod
    def update_schedule(id, *args, **kwargs):
        schedule_detail = Schedules.query.get(id)
        if not schedule_detail:
            return None
        schedule_detail.update(**kwargs)
        return schedule_detail

    @staticmethod
    def delete_schedules(id):
        return Schedules.query.get(id).delete()

    @staticmethod
    def delete_schedules_by_ids(ids):
        try:
            Schedules.query.filter(Schedules.id.in_(ids)).delete(
                synchronize_session=False
            )
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1

    @staticmethod
    def delete_schedules_by_user_id(ids, user_id):

        products_to_delete = Schedules.query.filter(
            and_(Schedules.id.in_(ids), Schedules.user_id == user_id)
        )

        # Đếm số lượng để biết có xóa gì không
        if products_to_delete.count() == 0:
            return False  # Không có sản phẩm để xóa

        # Thực hiện xóa
        products_to_delete.delete(synchronize_session=False)
        db.session.commit()
        return True

    @staticmethod
    def find_schedule_by_user_id(id, user_id):
        return Schedules.query.filter_by(id=id, user_id=user_id).first()

    @staticmethod
    def get_schedule_by_user_id(start, end, status):
        query = Schedules.query

        if start and end:
            query = query.filter(Schedules.date.between(start, end))

        if status:
            query = query.filter(Schedules.status == status)

        schedules = query.all()
        
        return [schedule_detail._to_json() for schedule_detail in schedules]