from app.models.youtube_client import YoutubeClient
import random
from app.lib.query import (
    delete_by_id,
    select_with_filter,
    select_by_id,
    select_with_filter_one,
    update_by_id,
)


class YoutubeClientService:

    @staticmethod
    def get_client_by_user_id(user_id):
        int_user_id = int(user_id)
        user_id_pattern = f"%,{int_user_id},%"
        filters = [
            YoutubeClient.user_ids.like(user_id_pattern),
            YoutubeClient.status == 1,
        ]
        return select_with_filter_one(YoutubeClient, filters=filters)

    @staticmethod
    def get_random_client():
        clients = select_with_filter(
            YoutubeClient,
            [YoutubeClient.status == 1],
        )
        if not clients:
            return None

        max_client = max(clients, key=lambda c: c.member_count)
        avg_member_count = sum(c.member_count for c in clients) / len(clients)

        if max_client.member_count > 2 * avg_member_count:
            clients = [c for c in clients if c != max_client]

        return random.choice(clients)

    @staticmethod
    def find_client_by_id(id):
        return select_by_id(YoutubeClient, id)

    @staticmethod
    def create_youtube_client(*args, **kwargs):
        youtube_client = YoutubeClient(*args, **kwargs)
        youtube_client.save()
        return youtube_client

    @staticmethod
    def update_youtube_client(id, **kwargs):
        return update_by_id(YoutubeClient, id, kwargs)

    @staticmethod
    def delete_youtube_client(id):
        delete_by_id(YoutubeClient, id)
        return True

    @staticmethod
    def get_youtube_clients():
        return select_with_filter(YoutubeClient)
