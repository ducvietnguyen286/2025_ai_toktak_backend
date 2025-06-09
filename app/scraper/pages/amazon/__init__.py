import traceback
from bs4 import BeautifulSoup
import requests

from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from app.lib.string import un_shotend_url
from app.scraper.pages.amazon.parser import Parser


class AmazonScraper:
    def __init__(self, params):
        self.url = params["url"]

    def run(self):
        return self.run_scraper()

    def run_scraper(self):
        request_url = self.url
        if "amzn." in request_url:
            request_url = un_shotend_url(request_url)

        html = self.get_page_html(request_url)
        if not html:
            return {}

        response = Parser(html).parse(request_url)

        print(response)

        return {}

    def get_page_html(self, url, count=0, added_headers=None):
        try:
            if count > 10:
                return False

            session = requests.Session()
            headers = self.generate_random_headers_request()

            response = session.get(url, headers=headers, timeout=5)
            info = response.content
            html = BeautifulSoup(info, "html.parser")
            return html
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            count = count + 1
            return self.get_page_html(url, count, added_headers)

    def generate_random_headers_request(self):
        user_agent = generate_desktop_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, compress, br",
            "Accept-Language": "en-US,en;q=0.9",
        }
        return headers
