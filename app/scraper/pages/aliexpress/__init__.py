import json
import time
import traceback
import uuid
from bs4 import BeautifulSoup
import requests
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from urllib.parse import urlparse, urlencode

from app.scraper.pages.aliexpress.parser import Parser
from app.extensions import redis_client


class AliExpressScraper:
    def __init__(self, params):
        self.url = params["url"]

    def run(self):
        return self.run_scraper()

    def run_call_api(self):
        return None

    def run_scraper(self):
        try:
            # req_id = str(uuid.uuid4())
            # task = {
            #     "req_id": req_id,
            #     "url": self.url,
            #     "wait_id": "product-description",
            #     "wait_class": "",
            #     "page": "ali",
            # }
            # redis_client.rpush("toktak:crawl_ali_queue", json.dumps(task))
            # timeout = 30  # Giây
            # start_time = time.time()
            # while time.time() - start_time < timeout:
            #     result = redis_client.get(f"toktak:result-ali:{req_id}")
            #     print("result", result)
            #     if result:
            #         redis_client.delete(f"toktak:result-ali:{req_id}")
            #         return json.loads(result)
            #     time.sleep(0.5)

            parsed_url = urlparse(self.url)

            real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            ali_data = self.get_page_html(real_url)
            if not ali_data:
                return {}
            ali_base_data = Parser(ali_data).parse(real_url)

            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(str(ali_data))
            # file_html.close()
            return ali_base_data
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return {}

    def get_page_html(self, url):
        try:
            session = requests.Session()
            headers = self.generate_random_headers_request()

            response = session.get(url, headers=headers, timeout=5)
            info = response.content
            html = BeautifulSoup(info, "html.parser")
            return html
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            return None

    def generate_random_headers_request(self):
        user_agent = generate_desktop_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, compress, br",
        }
        return headers
