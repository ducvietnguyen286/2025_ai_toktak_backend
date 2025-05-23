from app.models.crawl_data_mongo import CrawlDataMongo


class CrawlDataMongoService:

    @staticmethod
    def create_crawl_data(**kwargs):
        crawl_data = CrawlDataMongo(**kwargs)
        crawl_data.save()
        return crawl_data

    @staticmethod
    def find_crawl_data(hash):
        return CrawlDataMongo.objects(crawl_url_hash=hash).first()
