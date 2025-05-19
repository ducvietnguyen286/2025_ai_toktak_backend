from bson import ObjectId
from app.models.batch import Batch
from mongoengine import Q
from app.lib.query_mongo import select_with_pagination_mongo


class BatchService:

    @staticmethod
    def create_batch(*args, **kwargs):
        batch = Batch(*args, **kwargs)
        batch.save()
        return batch

    @staticmethod
    def find_batch(id):
        return Batch.objects.get(id=ObjectId(id))

    @staticmethod
    def get_batchs():
        batchs = Batch.objects(status=1)
        return batchs

    @staticmethod
    def update_batch(id, *args, **kwargs):
        batch = Batch.objects.get(id=ObjectId(id))
        batch.update(**kwargs)
        return batch

    @staticmethod
    def delete_batch(id):
        return Batch.objects.get(id=ObjectId(id)).delete()

    @staticmethod
    def get_all_batches(page, per_page, user_id=None):
        filters = [Q(user_id__gt=0)]
        if user_id is not None:
            filters.append(Q(user_id=user_id))

        order = ["-_id"]

        return select_with_pagination_mongo(
            model=Batch,
            page=page,
            per_page=per_page,
            filters=filters,
            order_by=order,
        )
