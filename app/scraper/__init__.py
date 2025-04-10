from app.scraper.pages.coupang import CoupangScraper
from app.scraper.pages.domeggook import DomeggookScraper
from app.scraper.pages.aliexpress import AliExpressScraper
from app.scraper.pages.shopee import ShopeeScarper

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
    elif "shopee." in netloc:
        scraper = ShopeeScarper(params)
    return scraper.run()


class Scraper:

    def scraper(self, params):
        response = get_page_scraper(params)
        return response
