import json
import os
import time
import traceback
from urllib.parse import urlparse
from app.lib.logger import logger
from app.lib.string import un_shotend_url
import requests
from gevent import sleep

from app.services.crawl_data import CrawlDataService


class NaverScraper:
    def __init__(self, params):
        self.params = params
        self.url = params.get("url")
        self.api_key = os.getenv("BRIGHT_DATA_API_KEY", "")

    def run(self):
        if "naver.me" in self.url:
            request_url = un_shotend_url(self.url)
        else:
            request_url = self.url

        return self.run_api_bright_data(request_url)

    def run_api_bright_data(self, request_url):
        try:
            logger.info(f"Request URL: {request_url}")
            logger.info(f"API Key: {self.api_key}")
            parsed_url = urlparse(request_url)
            real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

            product_id = parsed_url.path.split("/")[-1]
            if not product_id:
                return None

            exist_data = CrawlDataService.find_crawl_data(product_id, "NAVER")
            if exist_data:
                return json.loads(exist_data.response)

            url = "https://api.brightdata.com/datasets/v3/trigger"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            params = {
                "dataset_id": "gd_m9qqjxxr1hab7okefj",
                "include_errors": "true",
            }
            data = [
                {"url": real_url},
            ]

            logger.info(f"Data: {data}")

            response = requests.post(url, headers=headers, params=params, json=data)

            logger.info(f"Response TEXT: {response.text}")
            response_json = response.json()
            if response_json.get("error"):
                logger.error(f"Error: {response_json.get('error')}")
                return None

            if "snapshot_id" not in response_json:
                logger.error(f"Error: {response_json}")
                return None

            snapshot_id = response_json["snapshot_id"]
            start_time = time.time()
            while True:
                status = self.check_status_bright_data(snapshot_id)
                sleep(2)
                if status["status"] == "ready" or status["status"] == "failed":
                    break
                if time.time() - start_time > 300:
                    break
            if status["status"] != "ready":
                return None
            data = self.get_data_bright_data(snapshot_id)
            product_data = data[0] if data else None
            if not product_data:
                return None

            images = product_data.get("images", [])
            image_datas = [image.get("link", "") for image in images]

            sold_out = product_data.get("sold_out", False)

            price = product_data.get("final_price", 0)
            price_formated = "{:,}".format(int(price))
            price_show = f"{price_formated}원"

            sellers = product_data.get("sellers", [])
            seller_name = sellers[0].get("name", "") if sellers else ""
            product_id = product_data.get("product_id", "")

            result = {
                "name": product_data.get("title", ""),
                "description": product_data.get("description", ""),
                "stock": 1 if not sold_out else 0,
                "domain": real_url,
                "brand": "",
                "image": image_datas[0] if image_datas else "",
                "sku_images": [],
                "thumbnails": image_datas,
                "price": price_show,
                "url": real_url,
                "url_crawl": real_url,
                "base_url": self.url,
                "store_name": seller_name,
                "show_free_shipping": 0,
                "meta_url": "",
                "item_id": product_id,
                "vendor_id": "",
                "images": [],
                "text": "",
                "iframes": [],
                "gifs": [],
                "video_url": "",
                "video_thumbnail": "",
            }

            CrawlDataService.create_crawl_data(
                site="NAVER",
                input_url=self.url,
                crawl_url=real_url,
                crawl_url_hash=product_id,
                request=json.dumps("{}"),
                response=json.dumps(result),
            )
            return result
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error: {traceback.format_exc()}")
            logger.error(f"Error: {e}")
            return None

    def check_status_bright_data(self, snapshot_id):
        url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        response = requests.get(url, headers=headers)
        response_json = response.json()
        return response_json

    def get_data_bright_data(self, snapshot_id):
        url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        params = {
            "format": "json",
        }

        response = requests.get(url, headers=headers, params=params)
        return response.json()
