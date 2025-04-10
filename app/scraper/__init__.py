from app.scraper.pages.coupang import CoupangScraper
from app.scraper.pages.domeggook import DomeggookScraper
from app.scraper.pages.aliexpress import AliExpressScraper
from app.scraper.pages.shopee import ShopeeScarper

from urllib.parse import urlparse
import requests
from app.lib.logger import logger


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

    elif "shopee." in netloc:
        scraper = ShopeeScarper(params)
    return scraper.run()


class Scraper:

    def scraper(self, params):
        response = get_page_scraper(params)
        if not response:
            url = "https://scraper.vodaplay.vn/api/v1/maker/create-scraper"
            new_response = Scraper().call_api_and_get_data(url, params)
            return new_response

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
