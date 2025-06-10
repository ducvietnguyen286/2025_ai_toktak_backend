import os
import random
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

    def proxies(self):
        auth = "hekqlibd:llv12cujeqjr"

        proxy_path = os.path.join(os.getcwd(), "app/scraper/pages/coupang/proxies.txt")

        if not os.path.exists(proxy_path):
            logger.error("Proxy file not found: {0}".format(proxy_path))
            return {}

        with open(proxy_path, "r") as file:
            proxy_list = file.read().splitlines()

        selected_proxy = random.choice(proxy_list)

        if not selected_proxy.startswith("http"):
            selected_proxy = f"http://{auth}@{selected_proxy}"

        return {
            "http": selected_proxy,
            "https": selected_proxy,
        }

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
            "Accept-Language": "en-US,en;q=0.9",
        }
        return headers
