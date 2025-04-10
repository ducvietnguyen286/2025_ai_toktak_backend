import hashlib
from app.models.shorten import ShortenURL
from app.lib.string import generate_shortcode, should_replace_shortlink


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

    @staticmethod
    def shorted_link(url):
        if should_replace_shortlink(url):
            origin_hash = hashlib.sha256(url.encode()).hexdigest()
            existing_entry = ShortenServices.get_short_by_original_url(origin_hash)
            domain_share_url = "https://s.toktak.ai/"
            if not existing_entry:
                short_code = ShortenServices.make_short_url(url)

                existing_entry = ShortenServices.create_shorten(
                    original_url=url,
                    original_url_hash=origin_hash,
                    short_code=short_code,
                )

            shorten_link = f"{domain_share_url}{existing_entry.short_code}"
            return shorten_link, True
        return url, False
