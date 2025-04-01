from app.models.shorten import ShortenURL
from app.lib.string import generate_shortcode


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
    def get_short_by_original_url(origin_hash):
        return ShortenURL.query.filter_by(original_url_hash=origin_hash).first()

    @staticmethod
    def make_short_url(url):
        short_code = generate_shortcode()

        exist = ShortenURL.query.filter_by(short_code=short_code).first()
        while exist:
            short_code = generate_shortcode()
            exist = ShortenURL.query.filter_by(short_code=short_code).first()
        return short_code
