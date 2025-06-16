import json
import os
import random
import traceback

from bs4 import BeautifulSoup
import requests

from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from app.scraper.pages.walmart.parser import Parser
from urllib.parse import quote


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
        if not html:
            return {}

        response = Parser(html).parse(request_url)

        return response

    def get_cookies(self):
        cookies_path = os.path.join(
            os.getcwd(), "app/scraper/pages/walmart/cookies.json"
        )
        if not os.path.exists(cookies_path):
            logger.error("Cookies file not found: {0}".format(cookies_path))
            return {}

        with open(cookies_path, "r") as file:
            cookies = json.load(file)

        cookies_dict = {}
        for cookie in cookies:
            if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                cookies_dict[cookie["name"]] = cookie["value"]

        return cookies_dict

    def get_page_html(self, url, count=0, added_headers=None):
        try:
            if count > 10:
                return False

            session = requests.Session()
            headers = self.generate_random_headers_request(url)

            # cookies = self.get_cookies()
            proxies = self.proxies()

            # session.cookies.update(cookies)

            response = session.get(url, headers=headers, timeout=15, proxies=proxies)
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

    def generate_random_headers_request(self, url):
        user_agent = generate_desktop_user_agent()
        path = "/" + "/".join(url.split("/")[3:])
        path = quote(path, safe="/:?=&")
        headers = {
            "host": "www.walmart.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en",
            "priority": "u=0, i",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "upgrade-insecure-requests": "1",
            "user-agent": user_agent,
        }
        return headers
