import hashlib
import json
import random
import time
import traceback
import uuid
from bs4 import BeautifulSoup
import requests
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from http.cookiejar import CookieJar

from app.scraper.pages.aliexpress.parser import Parser
from app.extensions import redis_client
from app.scraper.pages.coupang.headers import random_mobile_header


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
            #     time.sleep(1)

            # parsed_url = urlparse(self.url)

            # real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            ali_data = self.get_page_html(self.url)
            if not ali_data:
                return {}
            ali_base_data = Parser(ali_data).parse(self.url)

            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(str(ali_data))
            # file_html.close()
            return ali_base_data
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return {}

    def generate_fake_sign(self, token, timestamp, app_key, data):
        """
        Hàm fake sign nhận vào:
          - token: mã token (từ options hoặc fake)
          - timestamp: thời gian hiện tại (milliseconds)
          - app_key: appKey được sử dụng
          - data: chuỗi dữ liệu JSON
        Trả về MD5 hash của chuỗi ghép theo định dạng:
          "{token}&{timestamp}&{app_key}&{data}"
        """
        raw_string = f"{token}&{timestamp}&{app_key}&{data}"
        sign = hashlib.md5(raw_string.encode("utf-8")).hexdigest().lower()
        return sign

    def get_page_html(self, url):
        try:
            cookie_jar = CookieJar()
            session = requests.Session()
            session.cookies = cookie_jar
            headers = self.get_headers()

            response = session.get(
                url, headers=headers, timeout=5, allow_redirects=True
            )
            info = response.content
            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(str(info))
            # file_html.close()
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

    def get_headers(self):
        """
        Generate request headers with a random user agent to prevent blocking.
        Includes necessary cookies and headers for AliExpress requests.
        """
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Cookie": "aep_usuc_f=site=glo&c_tp=USD&region=US&b_locale=en_US",
        }
