import hashlib
import hmac
import json
import os
import traceback
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
from app.lib.logger import logger
from app.services.crawl_data import CrawlDataService


class AliExpressScraper:
    def __init__(self, params):
        self.url = params["url"]

    def run(self):
        return self.run_scraper()

    def run_call_api(self):
        return None

    def sign_api_request(self, api, parameters, secret):
        sort_dict = sorted(parameters)
        if "/" in api:
            parameters_str = "%s%s" % (
                api,
                str().join("%s%s" % (key, parameters[key]) for key in sort_dict),
            )
        else:
            parameters_str = str().join(
                "%s%s" % (key, parameters[key]) for key in sort_dict
            )

        h = hmac.new(
            secret.encode(encoding="utf-8"),
            parameters_str.encode(encoding="utf-8"),
            digestmod=hashlib.sha256,
        )

        return h.hexdigest().upper()

    def sign_business_request(self, params, app_secret, sign_method, api_name):
        """
        Sinh chữ ký API request dựa theo:
        1. Sắp xếp các tham số theo thứ tự ASCII của key.
        2. Nối chuỗi: api_name + (key + value của các tham số nếu không rỗng).
        3. Tính HMAC-SHA256 của chuỗi đã nối.
        4. Chuyển kết quả về dạng chuỗi hex in HOA.

        Nếu sử dụng Business Interface, có thể cần thêm:
            params['method'] = api_name
        """
        # Sắp xếp các key
        sorted_keys = sorted(params.keys())

        # Khởi tạo chuỗi với API name (với System Interface)
        query = api_name
        for key in sorted_keys:
            value = params.get(key)
            if self.are_not_empty(key, value):
                query += key + value

        # Sinh chữ ký
        if sign_method == "sha256":
            signature_bytes = self.encrypt_hmac_sha256(query, app_secret)
        else:
            raise ValueError("Unsupported sign method")

        # Trả về chữ ký dạng hex in hoa
        return self.byte2hex(signature_bytes)

    def encrypt_hmac_sha256(self, data, secret):
        """
        Tính HMAC-SHA256 của dữ liệu với secret.
        Trả về mảng byte kết quả.
        """
        try:
            secret_bytes = secret.encode("utf-8")
            data_bytes = data.encode("utf-8")
            signature = hmac.new(secret_bytes, data_bytes, hashlib.sha256).digest()
            return signature
        except Exception as e:
            raise Exception(str(e))

    def byte2hex(self, byte_arr):
        """
        Chuyển đổi mảng byte sang chuỗi hex in hoa.
        """
        return "".join("{:02X}".format(b) for b in byte_arr)

    def are_not_empty(self, key, value):
        """Kiểm tra key và value không rỗng."""
        return key is not None and value is not None and key != "" and value != ""

    def generate_sign(self, parameters, api_secret):
        sorted_params = sorted(parameters.items())
        sorted_string = "".join(f"{key}{value}" for key, value in sorted_params)
        sign_string = f"{api_secret}{sorted_string}{api_secret}"
        md5_hash = hashlib.md5(sign_string.encode("utf-8")).hexdigest().upper()
        return md5_hash

    def run_scraper(self):
        try:

            parsed_url = urlparse(self.url)
            real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

            crawl_url_hash = hashlib.sha1(real_url.encode()).hexdigest()
            exist_data = CrawlDataService.find_crawl_data(crawl_url_hash)
            if exist_data:
                return json.loads(exist_data.response)

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
            prices = data.get("prices", {})
            target_price = prices.get("targetSkuPriceInfo", {})
            price_show = target_price.get("salePriceString", "")
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

            result = {
                "name": data.get("title", ""),
                "description": text,
                "stock": 1 if in_stock else 0,
                "domain": real_url,
                "brand": "",
                "image": image_url,
                "sku_images": sku_images,
                "thumbnails": thumbnails,
                "price": price_show,
                "url": real_url,
                "url_crawl": real_url,
                "base_url": real_url,
                "store_name": store_name,
                "show_free_shipping": 0,
                "meta_url": "",
                "images": images,
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
