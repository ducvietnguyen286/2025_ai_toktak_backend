from app.models.batch import Batch


class BatchService:

    @staticmethod
    def create_batch(*args, **kwargs):
        batch = Batch(*args, **kwargs)
        batch.save()
        return batch

    @staticmethod
    def find_batch(id):
        return Batch.query.get(id)

    @staticmethod
    def get_batchs():
        batchs = Batch.query.where(Batch.status == 1).all()
        return [batch._to_json() for batch in batchs]

    @staticmethod
    def update_batch(id, *args, **kwargs):
        batch = Batch.query.get(id)
        batch.update(**kwargs)
        return batch

    @staticmethod
    def delete_batch(id):
        return Batch.query.get(id).delete()

    @staticmethod
    def get_all_batches(page, per_page, user_id=None):

        query = Batch.query
        if user_id is not None:
            query = query.filter(Batch.user_id == user_id)

        pagination = query.order_by(Batch.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return pagination
