import os
import random
import traceback

from bs4 import BeautifulSoup
import requests

from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from app.scraper.pages.walmart.parser import Parser


class WalmartScraper:
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

        html = self.get_page_html(request_url)
        print(html)
        if not html:
            return {}

        # response = Parser(html).parse(request_url)

        # return response

    def get_page_html(self, url, count=0, added_headers=None):
        try:
            if count > 10:
                return False

            session = requests.Session()
            headers = self.generate_random_headers_request()

            # proxies = self.proxies()

            # print(proxies)
            print(headers)

            response = session.get(url, headers=headers, timeout=5)
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
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "cache-control": "no-cache",
            "downlink": "10",
            "dpr": "1",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "referer": "https://www.google.com/",
            "user-agent": user_agent,
            "host": "www.walmart.com",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive",
        }
        return headers
