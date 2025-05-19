from app.models.batch import Batch
from app.lib.query import select_with_filter, select_by_id, select_with_pagination


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
    def get_batchs():
        batchs = select_with_filter(
            Batch, order_by=[Batch.id.desc()], filters=[Batch.status == 1]
        )
        return [batch._to_json() for batch in batchs]

    @staticmethod
    def update_batch(id, *args, **kwargs):
        batch = Batch.query.get(id)
        batch.update(**kwargs)
        return batch

    @staticmethod
    def delete_batch(id):
        batch = select_by_id(Batch, id)
        if not batch:
            return None
        batch.delete()
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
