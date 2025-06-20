from app.models.batch import Batch
from app.lib.query import (
    delete_by_id,
    select_with_filter,
    select_by_id,
    select_with_pagination,
    update_by_id,
)
from datetime import datetime, timedelta
from app.extensions import db


class BatchService:

    @staticmethod
    def create_batch(*args, **kwargs):
        batch = Batch(*args, **kwargs)
        batch.save()
        return batch

    @staticmethod
    def find_batch(id):
        batch = select_by_id(Batch, id)
        return batch

    @staticmethod
    def find_batch_by_id(id):
        batch = Batch.query.filter(Batch.id == id).first()
        return batch

    @staticmethod
    def get_batchs():
        batchs = select_with_filter(
            Batch, order_by=[Batch.id.desc()], filters=[Batch.status == 1]
        )
        return [batch._to_json() for batch in batchs]

    @staticmethod
    def update_batch(id, *args, **kwargs):
        update_by_id(Batch, id, kwargs)
        batch = Batch.query.get(id)
        return batch

    @staticmethod
    def delete_batch(id):
        delete_by_id(Batch, id)
        return True

    @staticmethod
    def get_all_batches(page, per_page, user_id=None):
        filters = [
            Batch.user_id > 0,
        ]
        if user_id is not None:
            filters.append(Batch.user_id == user_id)
        pagination = select_with_pagination(
            Batch,
            page=page,
            per_page=per_page,
            filters=filters,
            order_by=[Batch.id.desc()],
        )
        return pagination

    @staticmethod
    def report_batch_by_type(data_search):

        histories = Batch.query
        process_status = data_search.get("process_status", "")
        if process_status != "":
            histories = histories.filter(Batch.process_status == process_status)

        time_range = data_search.get("time_range", "")
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            histories = histories.filter(Batch.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            histories = histories.filter(Batch.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            histories = histories.filter(Batch.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            histories = histories.filter(Batch.created_at >= start_date)

        elif time_range == "from_to":
            if "from_date" in data_search:
                from_date = datetime.strptime(data_search["from_date"], "%Y-%m-%d")
                histories = histories.filter(Batch.created_at >= from_date)
            if "to_date" in data_search:
                to_date = datetime.strptime(
                    data_search["to_date"], "%Y-%m-%d"
                ) + timedelta(days=1)
                histories = histories.filter(Batch.created_at < to_date)

        total = histories.count()

        return total

    @staticmethod
    def find_batch_with_task(id, session=None):
        if session is None:
            session = db.session
        return session.get(Batch, id)

    @staticmethod
    def update_batch_with_task(batch_id, session=None, **kwargs):
        if session is None:
            session = db.session
        batch = session.get(Batch, batch_id)
        for k, v in kwargs.items():
            setattr(batch, k, v)
        session.commit()
        return batch
