from app.models.crawl_data import CrawlData
from app.lib.query import select_with_filter_one, update_by_id


class CrawlDataService:

    @staticmethod
    def create_crawl_data(*args, **kwargs):
        crawl_data = CrawlData(*args, **kwargs)
        crawl_data.save()
        return crawl_data

    @staticmethod
    def find_crawl_data(hash, site):
        crawl_data = select_with_filter_one(
            CrawlData,
            filters=[
                CrawlData.crawl_url_hash == hash,
                CrawlData.site == site,
            ],
        )
        return crawl_data

    @staticmethod
    def update_crawl_data(id, **kwargs):
        update_by_id(CrawlData, id, kwargs)
        return True
