from app.scraper.pages.coupang import CoupangScraper

# from app.scraper.pages.domeggook import DomeggookScraper
# from app.scraper.pages.naver import NaverScraper
# from app.scraper.pages.st11 import St11Scraper
from urllib.parse import urlparse


def get_page_scraper(params):
    url = params["url"]
    scraper = None
    # parsed_url = urlparse(url)
    # netloc = parsed_url.netloc
    # if "naver." in netloc:
    #     scraper = NaverScraper(params)
    # elif "domeggook." in netloc:
    #     scraper = DomeggookScraper(params)
    # elif "11st." in netloc:
    #     scraper = St11Scraper(params)
    # elif "coupang." in netloc:
    scraper = CoupangScraper(params)
    return scraper.run()


class Scraper:

    def scraper(self, params):
        response = get_page_scraper(params)
        return response
