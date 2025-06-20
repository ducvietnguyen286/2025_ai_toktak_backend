import hashlib
from app.models.shorten import ShortenURL
from app.lib.string import generate_shortcode, should_replace_shortlink
from app.lib.query import (
    select_by_id,
    select_with_filter_one,
)

from app.extensions import db


class ShortenServices:

    @staticmethod
    def create_shorten(*args, **kwargs):
        short_url = ShortenURL(*args, **kwargs)
        short_url.save()
        return short_url

    @staticmethod
    def find_post(id):
        short_url = select_by_id(ShortenURL, id)
        return short_url

    @staticmethod
    def get_short_by_original_url(origin_hash):
        shorten_link = select_with_filter_one(
            ShortenURL,
            filters=[
                ShortenURL.original_url_hash == origin_hash,
                ShortenURL.status == 1,
            ],
        )
        return shorten_link

    @staticmethod
    def make_short_url():
        while True:
            short_code = generate_shortcode()
            exist = select_with_filter_one(
                ShortenURL,
                filters=[
                    ShortenURL.short_code == short_code,
                ],
            )
            if not exist:
                break
        return short_code

    @staticmethod
    def shorted_link(url):
        if should_replace_shortlink(url):
            origin_hash = hashlib.sha256(url.encode()).hexdigest()
            existing_entry = ShortenServices.get_short_by_original_url(origin_hash)
            domain_share_url = "https://s.toktak.ai/"
            if not existing_entry:
                short_code = ShortenServices.make_short_url()

                existing_entry = ShortenServices.create_shorten(
                    original_url=url,
                    original_url_hash=origin_hash,
                    short_code=short_code,
                )

            shorten_link = f"{domain_share_url}{existing_entry.short_code}"
            return shorten_link, True
        return url, False

    @staticmethod
    def shorted_link_with_task(url, session=None):
        if should_replace_shortlink(url):
            origin_hash = hashlib.sha256(url.encode()).hexdigest()
            existing_entry = ShortenServices.get_short_by_original_url_with_task(
                origin_hash, session=session
            )
            domain_share_url = "https://s.toktak.ai/"
            if not existing_entry:
                short_code = ShortenServices.make_short_url_with_task()
                existing_entry = ShortenServices.create_shorten_with_task(
                    original_url=url,
                    original_url_hash=origin_hash,
                    short_code=short_code,
                    session=session,
                )
            shorten_link = f"{domain_share_url}{existing_entry.short_code}"
            return shorten_link, True
        return url, False

    @staticmethod
    def get_short_by_original_url_with_task(origin_hash):
        if session is None:
            session = db.session
        return (
            session.query(ShortenURL)
            .filter(ShortenURL.original_url_hash == origin_hash, ShortenURL.status == 1)
            .first()
        )

    @staticmethod
    def make_short_url_with_task(session=None):
        if session is None:
            session = db.session
        while True:
            short_code = generate_shortcode()
            exist = (
                session.query(ShortenURL)
                .filter(ShortenURL.short_code == short_code)
                .first()
            )
            if not exist:
                break
        return short_code

    @staticmethod
    def create_shorten_with_task(session=None, **kwargs):
        if session is None:
            session = db.session
        short_url = ShortenURL(**kwargs)
        session.add(short_url)
        session.commit()
        return short_url
