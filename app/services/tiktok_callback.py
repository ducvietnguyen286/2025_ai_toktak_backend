from app.models.tiktok_callback import TiktokCallback


class TiktokCallbackService:

    @staticmethod
    def create_tiktok_callback(*args, **kwargs):
        tiktok_callback = TiktokCallback(*args, **kwargs)
        tiktok_callback.save()
        return tiktok_callback

    @staticmethod
    def find_tiktok_callback(id):
        return TiktokCallback.query.get(id)

    @staticmethod
    def get_tiktok_callbacks():
        tiktok_callbacks = TiktokCallback.query.where(TiktokCallback.status == 1).all()
        return [tiktok_callback._to_json() for tiktok_callback in tiktok_callbacks]

    @staticmethod
    def update_tiktok_callback(id, *args, **kwargs):
        tiktok_callback = TiktokCallback.query.get(id)
        tiktok_callback.update(**kwargs)
        return tiktok_callback

    @staticmethod
    def delete_tiktok_callback(id):
        return TiktokCallback.query.get(id).delete()

    @staticmethod
    def get_tiktok_callbacks_by_batch_id(batch_id):
        tiktok_callbacks = TiktokCallback.query.where(
            TiktokCallback.batch_id == batch_id
        ).all()
        return [tiktok_callback._to_json() for tiktok_callback in tiktok_callbacks]
