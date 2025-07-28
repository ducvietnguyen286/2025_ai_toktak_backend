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
from app.scraper.pages.domeggook.parser import Parser, extract_images_and_text
from urllib.parse import unquote


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

            url = f"https://esapi.domeggook.com/product/_doc/{product_id}"

            domeggook_token = os.getenv("DOMEGGOOK_TOKEN", "")

            headers = {"Authorization": f"Bearer {domeggook_token}"}

            res = requests.get(url, headers=headers)
            res_json = res.json()

            if not res_json.get("result"):
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

            product_info = res_json.get("data")
            product_source = product_info.get("_source")

            quantity = product_source.get("qty")
            quantity_number = quantity.get("inventory", 0)
            thumbnail = product_source.get("thumb")
            image = thumbnail.get("original", "")
            price = product_source.get("price")
            price_number = price.get("dome", 0)
            price_formatted = f"{price_number:,}원"
            seller = product_source.get("seller")
            seller_company = seller.get("company")
            seller_name = seller_company.get("name")

            description = product_source.get("desc")
            description_contents = description.get("contents", "")
            description_contents_html = BeautifulSoup(
                description_contents.get("item", ""), "html.parser"
            )
            images, gifs, iframes, text = extract_images_and_text(
                description_contents_html
            )

            result = {
                "name": product_source.get("title"),
                "description": "",
                "stock": quantity_number > 0,
                "domain": real_url,
                "brand": "",
                "image": image,
                "thumbnails": [image],
                "price": price_formatted,
                "url": real_url,
                "base_url": real_url,
                "store_name": seller_name,
                "url_crawl": real_url,
                "show_free_shipping": 0,
                "images": images,
                "text": text,
                "iframes": iframes,
                "gifs": gifs,
            }
            return result

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
