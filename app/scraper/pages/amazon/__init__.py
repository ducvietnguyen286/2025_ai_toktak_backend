import hashlib
import json
import os
import random
import traceback
from bs4 import BeautifulSoup
import requests

from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from app.lib.url import un_shotend_url
from app.scraper.pages.amazon.parser import Parser
from app.services.crawl_data import CrawlDataService


class AmazonScraper:
    def __init__(self, params):
        self.url = params["url"]

    def proxies(self):
        return {
            "http": "http://hekqlibd-rotate:llv12cujeqjr@p.webshare.io:80/",
            "https": "http://hekqlibd-rotate:llv12cujeqjr@p.webshare.io:80/",
        }

    def run(self):
        return self.run_scraper()

    def run_scraper(self):
        request_url = self.url
        if "amzn." in request_url:
            request_url = un_shotend_url(request_url)

        crawl_url_hash = hashlib.sha1(request_url.encode()).hexdigest()
        exist_data = CrawlDataService.find_crawl_data(crawl_url_hash)
        if exist_data:
            return json.loads(exist_data.response)

        html = self.get_page_html(request_url)
        if not html:
            return {}

        response = Parser(html).parse(request_url)

        CrawlDataService.create_crawl_data(
            site="AMAZON",
            input_url=self.url,
            crawl_url=request_url,
            crawl_url_hash=crawl_url_hash,
            request=json.dumps({}),
            response=json.dumps(response),
        )

        return response

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
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "cache-control": "no-cache",
            "device-memory": "8",
            "downlink": "10",
            "dpr": "1",
            "ect": "4g",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "rtt": "50",
            "upgrade-insecure-requests": "1",
            "user-agent": user_agent,
            "viewport-width": "1920",
        }
        return headers
