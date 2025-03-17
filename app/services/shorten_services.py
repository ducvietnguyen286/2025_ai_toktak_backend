from app.models.shorten import ShortenURL
from app.lib.string import generate_short_code


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
    def get_short_by_original_url(original_url):
        return ShortenURL.query.filter_by(original_url=original_url).first()

    @staticmethod
    def make_short_url(url):
        short_code = generate_short_code(url)

        while ShortenURL.query.filter_by(short_code=short_code).first():
            short_code = generate_short_code(url)
        return short_code
