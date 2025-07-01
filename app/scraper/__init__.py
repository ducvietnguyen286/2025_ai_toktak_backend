from app.lib.string import un_shotend_url
from app.scraper.pages.coupang import CoupangScraper
from app.scraper.pages.domeggook import DomeggookScraper
from app.scraper.pages.aliexpress import AliExpressScraper
from app.scraper.pages.ebay import EbayScraper
from app.scraper.pages.shopee import ShopeeScarper
from app.scraper.pages.amazon import AmazonScraper

from urllib.parse import parse_qs, urlparse
import requests
from app.lib.logger import logger
import random
from app.scraper.pages.walmart import WalmartScraper
from app.services.crawl_data import CrawlDataService
import hashlib
import json


def get_coupang_real_url(real_url, netloc):
    if netloc == "link.coupang.com":
        real_url = un_shotend_url(real_url)
        parsed_url = urlparse(real_url)

    path = parsed_url.path

    query_params = parsed_url.query
    query_params_dict = parse_qs(query_params)

    item_id = query_params_dict.get("itemId")
    vendor_item_id = query_params_dict.get("vendorItemId")

    path = path.replace("/vp/", "/vm/")
    target_item_id = item_id[0] if item_id else ""
    target_vendor_item_id = vendor_item_id[0] if vendor_item_id else ""

    path_mobile = path
    query_params = ""
    if target_item_id != "":
        query_params = query_params + "&itemId=" + target_item_id
    if target_vendor_item_id != "":
        query_params = query_params + "&vendorItemId=" + target_vendor_item_id
    query_params = query_params[1:]
    real_url = "https://m.coupang.com" + path_mobile + "?" + query_params
    return real_url


def get_domeggook_real_url(real_url, parsed_url):
    path = parsed_url.path
    if not path.strip("/").isdigit():
        real_url = un_shotend_url(real_url)
        parsed_url = urlparse(real_url)
    else:
        real_url = real_url

    if "mobile." in real_url:
        real_url = real_url.replace("mobile.", "")

    real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    return real_url


def get_aliexpress_real_url(real_url, parsed_url):

    if (
        "https://s.click.aliexpress.com/" in real_url
        or "https://a.aliexpress.com/" in real_url
    ):
        real_url = un_shotend_url(real_url)
        parsed_url = urlparse(real_url)
    else:
        real_url = real_url

    real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

    return real_url


def get_real_url(url):
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc
    if "coupang." in netloc:
        return get_coupang_real_url(url, netloc)
    elif "domeggook." in netloc:
        return get_domeggook_real_url(url, parsed_url)
    elif "aliexpress." in netloc:
        return get_aliexpress_real_url(url, parsed_url)
    return url


def get_site_by_url(url):
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc
    if "coupang." in netloc:
        return "COUPANG"
    elif "domeggook." in netloc:
        return "DOMEGGOOK"
    elif "aliexpress." in netloc:
        return "ALIEXPRESS"
    elif "amazon." in netloc or "amzn." in netloc:
        return "AMAZON"
    elif "ebay." in netloc:
        return "EBAY"
    elif "walmart." in netloc:
        return "WALMART"
    elif "shopee." in netloc:
        return "SHOPEE"
    return "UNKNOWN"


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
    return scraper.run()


class Scraper:

    def scraper(self, params):
        response = get_page_scraper(params)
        if not response:
            #     # 103.98.152.125
            #     # 3.38.117.230
            #     # 43.203.118.116
            #     # 3.35.172.6
            #     # #

            parsed_url = urlparse(params["url"])
            netloc = parsed_url.netloc
            logger.info(netloc)
            params["netloc"] = netloc
            urls = [
                "https://scraper.vodaplay.vn/api/v1/maker/create-scraper",
                "https://apitoktak.voda-play.com/api/v1/maker/create-scraper",
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

                    crawl_url_hash = hashlib.sha1(real_url.encode()).hexdigest()
                    # Check exists với crawl_url_hash
                    exists = CrawlDataService.find_crawl_data(crawl_url_hash)
                    if (
                        not exists
                        and response
                        and "images" in response
                        and len(response["images"]) > 0
                    ):
                        site = get_site_by_url(real_url)
                        CrawlDataService.create_crawl_data(
                            site=site,
                            input_url=params["url"],
                            crawl_url=real_url,
                            crawl_url_hash=crawl_url_hash,
                            # request=json.dumps(headers),
                            response=json.dumps(new_response),
                        )
                    break

        return response

    def call_api_and_get_data(self, url, params):

        data_post = {
            "url": params["url"],
        }

        response = requests.post(url, json=data_post)

        # Kiểm tra trạng thái HTTP trước
        if response.ok:
            result = response.json()

            # Kiểm tra trường 'code' trong dữ liệu trả về
            if result.get("code") == 200:
                return result.get("data")  # Lấy dữ liệu khi code == 200
            else:
                logger.error(
                    f"Lỗi {url} từ API: code = {result.get('code')}, message = {result.get('message')}"
                )
                return None
        else:
            logger.error(
                f"Lỗi {url} HTTP: {response.status_code}, Nội dung lỗi: {response.text}"
            )
            return None
