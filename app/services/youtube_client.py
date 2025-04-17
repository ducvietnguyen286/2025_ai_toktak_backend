from app.models.youtube_client import YoutubeClient
import random


class YoutubeClientService:

    @staticmethod
    def get_client_by_user_id(user_id):
        int_user_id = int(user_id)
        client = YoutubeClient.objects.filter(user_ids__contains=int_user_id).first()
        return client if client else None

    @staticmethod
    def get_random_client():
        clients = YoutubeClient.objects.all()
        if not clients:
            return None

        max_client = max(clients, key=lambda client: client.member_count)
        average_member_count = sum(client.member_count for client in clients) / len(
            clients
        )

        if max_client.member_count > 2 * average_member_count:
            clients = [client for client in clients if client != max_client]

        return random.choice(clients)

    @staticmethod
    def find_client_by_id(id):
        client = YoutubeClient.objects.get(id=id)
        return client if client else None

    @staticmethod
    def create_youtube_client(*args, **kwargs):
        youtube_client = YoutubeClient(*args, **kwargs)
        youtube_client.save()
        return youtube_client

    @staticmethod
    def update_youtube_client(id, **args):
        youtube_client = YoutubeClient.objects.get(id=id)
        youtube_client.update(**args)
        return youtube_client

    @staticmethod
    def delete_youtube_client(id):
        return YoutubeClient.objects.get(id=id).delete()

    @staticmethod
    def get_youtube_clients():
        return YoutubeClient.objects.all()
