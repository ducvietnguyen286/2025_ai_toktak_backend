import traceback
from bs4 import BeautifulSoup
import requests
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from urllib.parse import urlparse

from app.scraper.pages.domeggook.parser import Parser


class DomeggookScraper:
    def __init__(self, params):
        self.url = params["url"]

    def run(self):
        try:
            parsed_url = urlparse(self.url)
            real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            domeggook_data = self.get_page_html(real_url)
            if not domeggook_data:
                return {}
            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(str(domeggook_data))
            # file_html.close()
            response = Parser(domeggook_data).parse()
            return response
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
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
            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(info.decode("utf-8"))
            # file_html.close()
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
        }
        return headers
