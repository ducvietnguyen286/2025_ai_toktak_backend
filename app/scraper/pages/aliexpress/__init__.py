import hashlib
import hmac
from http.cookiejar import CookieJar
import json
import os
import traceback
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
from app.lib.header import generate_desktop_user_agent
from app.lib.logger import logger
from app.services.crawl_data import CrawlDataService


class AliExpressScraper:
    def __init__(self, params):
        self.url = params["url"]

    def run(self):
        return self.run_scraper()

    def un_shortend_url(self, url, retry=0):
        try:
            cookie_jar = CookieJar()
            session = requests.Session()
            session.cookies = cookie_jar
            user_agent = generate_desktop_user_agent()
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en",
                "priority": "u=0, i",
                "referer": "",
                "upgrade-insecure-requests": "1",
                "user-agent": user_agent,
            }
            logger.info("Unshortend URL: {0}".format(url))
            response = session.get(
                url, allow_redirects=False, headers=headers, timeout=5
            )
            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(response.content.decode("utf-8"))
            # file_html.close()

            # logger.info("Unshortend Text: {0}".format(response.content))
            # print(response)
            if "Location" in response.headers:
                redirect_url = response.headers["Location"]
                if not urlparse(redirect_url).netloc:
                    redirect_url = (
                        urlparse("https://ko.aliexpress.com")
                        ._replace(path=redirect_url)
                        .geturl()
                    )
                logger.info("Unshortend URL AFTER: {0}".format(redirect_url))
                return redirect_url
            else:
                return url
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            if retry < 3:
                return self.un_shortend_url(url, retry + 1)
            return url

    def run_scraper(self):
        try:
            is_shorted_link = False
            if "https://s.click.aliexpress.com/" in self.url:
                request_url = self.un_shortend_url(self.url)
                is_shorted_link = True
            else:
                request_url = self.url
            parsed_url = urlparse(request_url)
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
                "base_url": self.url,
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
