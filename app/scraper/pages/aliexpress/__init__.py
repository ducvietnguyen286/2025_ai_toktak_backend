import hashlib
import json
import os
import traceback
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
from app.lib.logger import logger
from app.services.crawl_data import CrawlDataService
from app.lib.url import get_real_url


class AliExpressScraper:
    def __init__(self, params):
        self.url = params["url"]

    def run(self):
        return self.run_scraper()

    def run_scraper(self):
        real_url = get_real_url(self.url)

        # Push

        data = self.run_api_ali_data_hub_6(real_url)
        if not data:
            data = self.run_api_ali_data(real_url)
        if not data:
            data = self.run_api_ali_data_hub_2(real_url)
        if not data:
            return {}
        return data

    def run_api_ali_data_hub_6(self, real_url):
        try:
            crawl_url_hash = hashlib.sha1(real_url.encode()).hexdigest()
            exist_data = CrawlDataService.find_crawl_data(crawl_url_hash)
            if exist_data:
                return json.loads(exist_data.response)

            parsed_url = urlparse(real_url)
            product_id = parsed_url.path.split("/")[-1].split(".")[0]

            RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

            headers = {
                "x-rapidapi-key": RAPIDAPI_KEY,
                "x-rapidapi-host": "aliexpress-datahub.p.rapidapi.com",
            }

            querystring = {
                "itemId": product_id,
                "currency": "KRW",
                "region": "kr",
                "locale": "ko_KR",
            }

            url = "https://aliexpress-datahub.p.rapidapi.com/item_detail_6"

            response = requests.get(url, headers=headers, params=querystring)
            res = response.json()
            data = res.get("result", {})

            if not data:
                return {}

            status = data.get("status", {})
            data_status = status.get("data", "")
            if data_status != "success":
                return {}

            item = data.get("item", {})
            seller = item.get("seller", {})

            description = item.get("description", {})
            description_html = description.get("html", "")
            images, gifs, iframes, text = self.extract_images_and_text(description_html)
            in_stock = True
            store_name = seller.get("storeTitle", "")
            price_show = ""
            thumbnails = item.get("images", [])
            sku = item.get("sku", {})
            sku_images = []
            if sku:
                sku_images = sku.get("skuImages", {})

                if sku_images:
                    sku_images = [
                        f"https:{img}" if img.startswith("//") else img
                        for img in sku_images.values()
                    ]

            video = item.get("video", {})
            video_url = ""
            video_thumbnail = ""
            if video:
                video_thumbnail = video.get("thumbnail", "")
                video_url = video.get("url", "")

            for thumbnail in thumbnails:
                if thumbnail.startswith("//"):
                    thumbnail = "https:" + thumbnail

            image_url = thumbnails[0] if thumbnails else ""

            if image_url.startswith("//"):
                image_url = "https:" + image_url

            image_datas = []
            if images:
                image_datas = [
                    f"https:{img}" if img.startswith("//") else img for img in images
                ]
            thumbnails_datas = []
            if thumbnails:
                thumbnails_datas = [
                    f"https:{img}" if img.startswith("//") else img
                    for img in thumbnails
                ]

            if video_url.startswith("//"):
                video_url = "https:" + video_url
            if video_thumbnail.startswith("//"):
                video_thumbnail = "https:" + video_thumbnail

            result = {
                "name": item.get("title", ""),
                "description": text,
                "stock": 1 if in_stock else 0,
                "domain": real_url,
                "brand": "",
                "image": image_url,
                "sku_images": sku_images,
                "thumbnails": thumbnails_datas,
                "price": price_show,
                "url": real_url,
                "url_crawl": real_url,
                "base_url": self.url,
                "store_name": store_name,
                "show_free_shipping": 0,
                "meta_url": "",
                "item_id": product_id,
                "vendor_id": "",
                "images": image_datas,
                "text": text,
                "iframes": iframes,
                "gifs": gifs,
                "video_url": video_url,
                "video_thumbnail": video_thumbnail,
            }
            CrawlDataService.create_crawl_data(
                site="ALIEXPRESS",
                input_url=self.url,
                crawl_url=real_url,
                crawl_url_hash=crawl_url_hash,
                request=json.dumps(
                    {
                        "x-rapidapi-host": headers["x-rapidapi-host"],
                        "querystring": querystring,
                    }
                ),
                response=json.dumps(result),
            )
            return result

        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return {}

    def run_api_ali_data_hub_2(self, real_url):
        try:
            crawl_url_hash = hashlib.sha1(real_url.encode()).hexdigest()
            exist_data = CrawlDataService.find_crawl_data(crawl_url_hash)
            if exist_data:
                return json.loads(exist_data.response)

            parsed_url = urlparse(real_url)
            product_id = parsed_url.path.split("/")[-1].split(".")[0]

            RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

            headers = {
                "x-rapidapi-key": RAPIDAPI_KEY,
                "x-rapidapi-host": "aliexpress-datahub.p.rapidapi.com",
            }

            querystring = {
                "productId": product_id,
                "currency": "KRW",
                "region": "kr",
                "locale": "ko_KR",
            }

            url = "https://aliexpress-datahub.p.rapidapi.com/item_detail_2"

            response = requests.get(url, headers=headers, params=querystring)
            res = response.json()
            data = res.get("result", {})
            if not data:
                return {}

            status = data.get("status", {})
            data_status = status.get("data", "")
            if data_status != "success":
                return {}

            description_url = "https://aliexpress-datahub.p.rapidapi.com/item_desc_2"
            desc_querystring = {"itemId": product_id, "locale": "ko_KR"}
            description_res = requests.get(
                description_url, headers=headers, params=desc_querystring
            )
            description_res = description_res.json()
            description_data = description_res.get("result", {})
            desc_item = description_data.get("item", {})

            item = data.get("item", {})
            seller = item.get("seller", {})

            description = desc_item.get("description", {})
            description_html = description.get("html", "")
            images, gifs, iframes, text = self.extract_images_and_text(description_html)
            in_stock = True
            store_name = seller.get("storeTitle", "")
            price_show = ""
            thumbnails = item.get("images", [])
            sku = item.get("sku", {})
            sku_images = []
            if sku:
                sku_images = sku.get("skuImages", [])
            video = item.get("video", {})
            video_url = ""
            video_thumbnail = ""
            if video:
                video_thumbnail = video.get("thumbnail", "")
                video_url = video.get("url", "")

            for thumbnail in thumbnails:
                if thumbnail.startswith("//"):
                    thumbnail = "https:" + thumbnail
            for sku_image in sku_images:
                if sku_image.startswith("//"):
                    sku_image = "https:" + sku_image

            image_url = thumbnails[0] if thumbnails else ""

            if image_url.startswith("//"):
                image_url = "https:" + image_url

            image_datas = []
            if images:
                image_datas = [
                    f"https:{img}" if img.startswith("//") else img for img in images
                ]
            thumbnails_datas = []
            if thumbnails:
                thumbnails_datas = [
                    f"https:{img}" if img.startswith("//") else img
                    for img in thumbnails
                ]

            if video_url.startswith("//"):
                video_url = "https:" + video_url
            if video_thumbnail.startswith("//"):
                video_thumbnail = "https:" + video_thumbnail

            result = {
                "name": item.get("title", ""),
                "description": text,
                "stock": 1 if in_stock else 0,
                "domain": real_url,
                "brand": "",
                "image": image_url,
                "sku_images": sku_images,
                "thumbnails": thumbnails_datas,
                "price": price_show,
                "url": real_url,
                "url_crawl": real_url,
                "base_url": self.url,
                "store_name": store_name,
                "show_free_shipping": 0,
                "meta_url": "",
                "item_id": product_id,
                "vendor_id": "",
                "images": image_datas,
                "text": text,
                "iframes": iframes,
                "gifs": gifs,
                "video_url": video_url,
                "video_thumbnail": video_thumbnail,
            }
            CrawlDataService.create_crawl_data(
                site="ALIEXPRESS",
                input_url=self.url,
                crawl_url=real_url,
                crawl_url_hash=crawl_url_hash,
                request=json.dumps(
                    {
                        "x-rapidapi-host": headers["x-rapidapi-host"],
                        "querystring": querystring,
                    }
                ),
                response=json.dumps(result),
            )
            return result

        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return {}

    def run_api_ali_data(self, real_url):
        try:
            crawl_url_hash = hashlib.sha1(real_url.encode()).hexdigest()
            exist_data = CrawlDataService.find_crawl_data(crawl_url_hash)
            if exist_data:
                return json.loads(exist_data.response)

            parsed_url = urlparse(real_url)
            product_id = parsed_url.path.split("/")[-1].split(".")[0]

            RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

            headers = {
                "x-rapidapi-key": RAPIDAPI_KEY,
                "x-rapidapi-host": "aliexpress-data.p.rapidapi.com",
            }

            querystring = {
                "productId": product_id,
                "country": "ko",
                "currency": "KRW",
            }

            url = "https://aliexpress-data.p.rapidapi.com/product/descriptionv5"

            response = requests.get(url, headers=headers, params=querystring)
            res = response.json()
            data = res.get("data", {})
            if not data:
                return {}

            description = data.get("description", {})
            description_html = description.get("descriptionHtml", "")
            images, gifs, iframes, text = self.extract_images_and_text(description_html)
            in_stock = data.get("hasStock", False)
            shop_info = data.get("shopInfo", {})
            store_name = shop_info.get("storeName", "")
            image_url = data.get("image", "")
            # prices = data.get("prices", {})
            # target_price = prices.get("targetSkuPriceInfo", {})
            # price_show = target_price.get("salePriceString", "")
            price_show = ""
            media = data.get("media", {})
            thumbnails = media.get("images", [])
            sku_images = media.get("currentSkuImages", [])
            video = media.get("video", {})
            video_url = ""
            video_thumbnail = ""
            if video:
                video_info = video.get("videoPlayInfo", {})
                video_thumbnail = video.get("posterUrl", "")
                video_url = video_info.get("webUrl", "")

            if image_url.startswith("//"):
                image_url = "https:" + image_url

            image_datas = []
            if images:
                image_datas = [
                    f"https:{img}" if img.startswith("//") else img for img in images
                ]
            thumbnails_datas = []
            if thumbnails:
                thumbnails_datas = [
                    f"https:{img}" if img.startswith("//") else img
                    for img in thumbnails
                ]

            result = {
                "name": data.get("title", ""),
                "description": text,
                "stock": 1 if in_stock else 0,
                "domain": real_url,
                "brand": "",
                "image": image_url,
                "sku_images": sku_images,
                "thumbnails": thumbnails_datas,
                "price": price_show,
                "url": real_url,
                "url_crawl": real_url,
                "base_url": self.url,
                "store_name": store_name,
                "show_free_shipping": 0,
                "meta_url": "",
                "item_id": product_id,
                "vendor_id": "",
                "images": image_datas,
                "text": text,
                "iframes": iframes,
                "gifs": gifs,
                "video_url": video_url,
                "video_thumbnail": video_thumbnail,
            }
            CrawlDataService.create_crawl_data(
                site="ALIEXPRESS",
                input_url=self.url,
                crawl_url=real_url,
                crawl_url_hash=crawl_url_hash,
                request=json.dumps(
                    {
                        "x-rapidapi-host": headers["x-rapidapi-host"],
                        "querystring": querystring,
                    }
                ),
                response=json.dumps(result),
            )
            return result

        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return {}

    def extract_images_and_text(self, html):
        soup = BeautifulSoup(html, "html.parser")

        images = []
        gifs = []
        iframes = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                if src.endswith(".gif"):
                    gifs.append(src)
                else:
                    images.append(src)

        for iframe in soup.find_all("iframe"):
            src = iframe.get("src")
            if src:
                iframes.append(src)

        text = soup.get_text(separator=" ", strip=True)

        return images, gifs, iframes, text
