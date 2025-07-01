from http.cookiejar import CookieJar
import os
import random
import traceback
from bs4 import BeautifulSoup
import requests
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from urllib.parse import urlparse

from app.scraper.pages.domeggook.parser import Parser
from app.lib.url import get_real_url


class DomeggookScraper:
    def __init__(self, params):
        self.url = params["url"]

    def proxies(self):
        return {
            "http": "http://hekqlibd-rotate:llv12cujeqjr@p.webshare.io:80/",
            "https": "http://hekqlibd-rotate:llv12cujeqjr@p.webshare.io:80/",
        }

    def run(self):
        try:
            real_url = get_real_url(self.url)
            parsed_url = urlparse(real_url)
            product_id = parsed_url.path.strip("/").split("/")[-1]
            domeggook_data = self.get_page_html(real_url)
            if not domeggook_data:
                return {}
            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(str(domeggook_data))
            # file_html.close()
            response = Parser(domeggook_data).parse(real_url)

            response["meta_id"] = ""
            response["item_id"] = product_id
            response["vendor_id"] = ""
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
            proxies = self.proxies()
            response = session.get(url, headers=headers, timeout=5, proxies=proxies)
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
