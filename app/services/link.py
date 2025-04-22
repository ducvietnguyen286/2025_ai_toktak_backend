from app.models.link import Link

from app.extensions import redis_client
import json


class LinkService:

    @staticmethod
    def create_link(*args, **kwargs):
        link = Link(*args, **kwargs)
        link.save()
        return link

    @staticmethod
    def find_link(id):
        return Link.query.get(id)

    @staticmethod
    def find_link_by_type(type):
        return Link.query.where(Link.type == type).first()

    @staticmethod
    def get_links():
        links = Link.query.where(Link.status == 1).all()
        return [link._to_json() for link in links]

    @staticmethod
    def get_not_json_links():
        links = Link.query.where(Link.status == 1).all()
        return links

    @staticmethod
    def update_link(id, *args):
        link = Link.query.get(id)
        link.update(*args)
        return link

    @staticmethod
    def delete_link(id):
        return Link.query.get(id).delete()

    @staticmethod
    def get_all_links():
        redis_key = "links_all_sns"
        ttl = 86400
        cached = redis_client.get(redis_key)
        if cached:
            try:
                return json.loads(cached)
            except:
                pass
        links = Link.query.where(Link.status == 1).all()
        data = [link._to_json() for link in links]
        redis_client.set(redis_key, json.dumps(data), ex=ttl)
        return data
