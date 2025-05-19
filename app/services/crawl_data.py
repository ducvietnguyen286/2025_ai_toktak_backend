from app.models.crawl_data import CrawlData
from app.lib.query import select_with_filter_one


class CrawlDataService:

    @staticmethod
    def create_crawl_data(*args, **kwargs):
        crawl_data = CrawlData(*args, **kwargs)
        crawl_data.save()
        return crawl_data

    @staticmethod
    def find_crawl_data(hash):
        crawl_data = select_with_filter_one(
            CrawlData, filters=[CrawlData.crawl_url_hash == hash]
        )
        return crawl_data
