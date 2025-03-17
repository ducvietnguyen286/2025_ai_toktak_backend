from app.models.shorten import ShortenURL


class ShortenServices:

    @staticmethod
    def create_shorten(*args, **kwargs):
        short_url = ShortenURL(*args, **kwargs)
        short_url.save()
        return short_url

    @staticmethod
    def find_post(id):
        return ShortenURL.query.get(id)

    @staticmethod
    def get_short_urls():
        short_urls = ShortenURL.query.where(ShortenURL.status == 1).all()
        return [short_urls._to_json() for post in short_urls]
