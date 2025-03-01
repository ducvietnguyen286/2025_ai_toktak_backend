from app.models.crawl_data import CrawlData



class CrawlDataService:

    @staticmethod
    def create_crawl_data(*args, **kwargs):
        crawl_data = CrawlData(*args, **kwargs)
        crawl_data.save()
        return crawl_data

    @staticmethod
    def find_crawl_data(hash):
        return CrawlData.query.filter_by(crawl_url_hash=hash).first()
    
    