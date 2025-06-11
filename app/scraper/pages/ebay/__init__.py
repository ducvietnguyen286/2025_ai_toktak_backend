import os
import random
import traceback

from bs4 import BeautifulSoup
import requests

from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger


class EbayScraper:
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
        print("run")
        return self.run_scraper()

    def run_scraper(self):
        request_url = self.url
        print("request_url", request_url)

        html = self.get_page_html(request_url)
        print(html)
        if not html:
            return {}

        return html

    def get_page_description(self, html):
        params = {
            "t": 0,
            "category": 15709,
            "seller": "officialpumastore",
            "excSoj": 1,
            "ver": 0,
            "excTrk": 1,
            "lsite": 0,
            "ittenable": False,
            "domain": "ebay.com",
            "descgauge": 1,
            "cspheader": 1,
            "oneClk": 2,
            "secureDesc": 1,
            "variationId": 2560341887251,
        }

        URL_REQUEST = "https://itm.ebaydesc.com/itmdesc/277003406532"

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

            file_html = open("demo.html", "w", encoding="utf-8")
            file_html.write(info.decode("utf-8"))
            file_html.close()

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
