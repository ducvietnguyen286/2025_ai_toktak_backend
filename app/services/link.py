from app.models.link import Link


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
