from app.scraper.pages.coupang import CoupangScraper
from app.scraper.pages.domeggook import DomeggookScraper
from app.scraper.pages.aliexpress import AliExpressScraper
from app.scraper.pages.ebay import EbayScraper
from app.scraper.pages.naver import NaverScraper
from app.scraper.pages.shopee import ShopeeScarper
from app.scraper.pages.amazon import AmazonScraper
from app.scraper.pages.walmart import WalmartScraper
from app.lib.url import get_real_url, get_site_by_url

import requests
from app.lib.logger import logger
import random
from app.services.crawl_data import CrawlDataService
import hashlib
import json
from urllib.parse import urlparse


def get_page_scraper(params):
    url = params["url"]
    scraper = None
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc
    if "domeggook." in netloc:
        scraper = DomeggookScraper(params)
    elif "coupang." in netloc:
        scraper = CoupangScraper(params)
    elif "aliexpress." in netloc:
        scraper = AliExpressScraper(params)
    elif "amazon." in netloc or "amzn." in netloc:
        scraper = AmazonScraper(params)
    elif "ebay." in netloc:
        scraper = EbayScraper(params)
    elif "walmart." in netloc:
        scraper = WalmartScraper(params)
    elif "shopee." in netloc:
        scraper = ShopeeScarper(params)
    elif "naver." in netloc:
        scraper = NaverScraper(params)
    return scraper.run()


class Scraper:
    def scraper(self, params):
        response = get_page_scraper(params)
        if not response:
            parsed_url = urlparse(params["url"])
            netloc = parsed_url.netloc
            logger.info(netloc)
            params["netloc"] = netloc
            urls = [
                "https://scraper.vodaplay.vn/api/v1/maker/create-scraper",
                "https://scraper.play-tube.net/api/v1/maker/create-scraper",
                "https://scraper.canvasee.com/api/v1/maker/create-scraper",
                "https://scraper.bodaplay.ai/api/v1/maker/create-scraper",
            ]
            random.shuffle(urls)
            for url in urls:
                new_response = Scraper().call_api_and_get_data(url, params)
                if new_response:
                    response = new_response

                    real_url = get_real_url(params["url"])

                    site = get_site_by_url(real_url)

                    crawl_url_hash = hashlib.sha1(real_url.encode()).hexdigest()
                    # Check exists với crawl_url_hash
                    exists = CrawlDataService.find_crawl_data(crawl_url_hash, site)
                    if (
                        not exists
                        and response
                        and "images" in response
                        and len(response["images"]) > 0
                    ):
                        CrawlDataService.create_crawl_data(
                            site=site,
                            input_url=params["url"],
                            crawl_url=real_url,
                            crawl_url_hash=crawl_url_hash,
                            response=json.dumps(new_response),
                        )
                    break

        return response

    def call_api_and_get_data(self, url, params):
        data_post = {
            "url": params["url"],
        }

        response = requests.post(url, json=data_post, timeout=10)
        # Kiểm tra trạng thái HTTP trước
        if response.ok:
            result = response.json()

            # Kiểm tra trường 'code' trong dữ liệu trả về
            if result.get("code") == 200:
                return result.get("data")  # Lấy dữ liệu khi code == 200
            else:
                return None
        else:
            return None
