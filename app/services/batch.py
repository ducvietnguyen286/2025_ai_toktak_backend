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
        return Batch.query.where(Batch.status == 1).all()

    @staticmethod
    def update_batch(id, *args, **kwargs):
        batch = Batch.query.get(id)
        batch.update(*kwargs)
        return batch

    @staticmethod
    def delete_batch(id):
        return Batch.query.get(id).delete()
