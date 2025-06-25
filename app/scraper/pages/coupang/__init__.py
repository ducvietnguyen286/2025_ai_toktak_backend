from http.cookiejar import CookieJar
import json
import os
import random
import time
import traceback
import uuid
from app.lib.header import generate_desktop_user_agent, generate_user_agent
from app.lib.logger import logger
from app.scraper.pages.coupang.headers import random_mobile_header, random_web_header
from app.scraper.pages.coupang.parser import Parser
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import requests
import hashlib
from app.extensions import redis_client

from app.services.crawl_data import CrawlDataService


class CoupangScraper:
    def __init__(self, params):
        self.url = params["url"]
        self.fire_crawl_key = ""

    def run(self):
        return self.run_crawler_mobile()

    def proxies(self):
        proxies = [
            "http://brd-customer-hl_8019b21f-zone-scraping_browser2-country-kr:wyfmhy3tqffj@brd.superproxy.io:33335",
            "http://brd-customer-hl_8019b21f-zone-scraping_browser2-country-il:wyfmhy3tqffj@brd.superproxy.io:33335",
        ]

        random_proxy = random.choice(proxies)
        # old_proxy = "http://hekqlibd-rotate:llv12cujeqjr@p.webshare.io:80/"
        # proxy = "http://b45ba2a7:xyuhqzh7dlyu@proxy.toolip.io:31113"
        return {
            "http": random_proxy,
            "https": random_proxy,
        }

    def cert_ssl_path(self):
        COUPANG_FOLDER = os.path.join(os.getcwd(), "app/scraper/pages/coupang")
        return os.path.join(COUPANG_FOLDER, "ca_cert.crt")

    def run_selenium(self):
        try:
            req_id = str(uuid.uuid4())

            real_url = self.url

            parsed_url = urlparse(real_url)
            netloc = parsed_url.netloc

            if netloc == "link.coupang.com":
                real_url = self.un_shortend_url(real_url)
                parsed_url = urlparse(real_url)

            path = parsed_url.path

            query_params = parsed_url.query
            query_params_dict = parse_qs(query_params)

            item_id = query_params_dict.get("itemId")
            vendor_item_id = query_params_dict.get("vendorItemId")

            path = path.replace("/vp/", "/vm/")
            target_item_id = item_id[0] if item_id else ""
            target_vendor_item_id = vendor_item_id[0] if vendor_item_id else ""

            path_mobile = path
            query_params = ""
            if target_item_id != "":
                query_params = query_params + "&itemId=" + target_item_id
            if target_vendor_item_id != "":
                query_params = query_params + "&vendorItemId=" + target_vendor_item_id
            query_params = query_params[1:]
            real_url = "https://m.coupang.com" + path_mobile + "?" + query_params

            task = {
                "req_id": req_id,
                "url": real_url,
            }
            redis_client.rpush("toktak:crawl_coupang_queue", json.dumps(task))
            timeout = 30  # Giây
            start_time = time.time()
            while time.time() - start_time < timeout:
                result = redis_client.get(f"toktak:result_coupang:{req_id}")
                print("result", result)
                if result:
                    redis_client.delete(f"toktak:result_coupang:{req_id}")
                    return json.loads(result)
                time.sleep(0.5)

            # parsed_url = urlparse(self.url)

            # real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

            real_url = real_url + "&failRedirectApp=true"

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

    def un_shortend_url(self, url, retry=0):
        try:
            cookie_jar = CookieJar()
            session = requests.Session()
            session.cookies = cookie_jar
            headers = random_mobile_header()
            user_agent = generate_desktop_user_agent()
            headers.update({"user-agent": user_agent})

            logger.info("Unshortend URL: {0}".format(url))
            response = session.get(
                url, allow_redirects=False, headers=headers, timeout=5
            )
            if "Location" in response.headers:
                redirect_url = response.headers["Location"]
                if not urlparse(redirect_url).netloc:
                    redirect_url = (
                        urlparse("https://www.coupang.com")
                        ._replace(path=redirect_url)
                        .geturl()
                    )
                logger.info("Unshortend URL AFTER 22: {0}".format(redirect_url))
                return redirect_url
            else:
                return url
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            if retry < 3:
                return self.un_shortend_url(url, retry + 1)
            return url

    def run_crawler_mobile(self):
        try:
            base_url = self.url
            real_url = self.url

            parsed_url = urlparse(real_url)
            netloc = parsed_url.netloc

            if netloc == "link.coupang.com":
                real_url = self.un_shortend_url(real_url)
                parsed_url = urlparse(real_url)

            path = parsed_url.path

            query_params = parsed_url.query
            query_params_dict = parse_qs(query_params)

            item_id = query_params_dict.get("itemId")
            vendor_item_id = query_params_dict.get("vendorItemId")

            path = path.replace("/vp/", "/vm/")
            target_item_id = item_id[0] if item_id else ""
            target_vendor_item_id = vendor_item_id[0] if vendor_item_id else ""

            path_mobile = path
            query_params = ""
            if target_item_id != "":
                query_params = query_params + "&itemId=" + target_item_id
            if target_vendor_item_id != "":
                query_params = query_params + "&vendorItemId=" + target_vendor_item_id
            query_params = query_params[1:]
            real_url = "https://m.coupang.com" + path_mobile + "?" + query_params

            crawl_url_hash = hashlib.sha1(real_url.encode()).hexdigest()
            # exist_data = CrawlDataService.find_crawl_data(crawl_url_hash)
            # if exist_data:
            #     return json.loads(exist_data.response)

            # added_headers = {"referer": real_url}

            real_url = real_url + "&failRedirectApp=true"

            coupang_data = self.get_page_html(real_url)

            if not coupang_data:
                return None
            html = coupang_data["html"]
            url = coupang_data["url"]
            headers = coupang_data["headers"]
            response = Parser(html, url).parse(base_url)

            if response:
                meta_url = response.get("meta_url")
                logger.info("meta_url: {0}".format(meta_url))
                coupang_btf_content = self.get_coupang_btf_content(meta_url, headers)
                response.update(coupang_btf_content)

                if response and "images" in response and len(response["images"]) > 0:
                    CrawlDataService.create_crawl_data(
                        site="COUPANG",
                        input_url=base_url,
                        crawl_url=real_url,
                        crawl_url_hash=crawl_url_hash,
                        request=json.dumps(headers),
                        response=json.dumps(response),
                    )
            return response
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            return None

    def get_coupang_btf_content(self, meta_url, headers, retry=0):
        try:
            parsed_url = urlparse(meta_url)
            path = parsed_url.path
            query_params = parsed_url.query
            query_params_dict = parse_qs(query_params)
            item_id = query_params_dict.get("itemId")
            vendor_item_id = query_params_dict.get("vendorItemId")
            product_id = path.split("/")[-1]

            btf_url = "https://m.coupang.com/vm/sdp/v3/mweb/products/{0}/items/{1}/vendor-items/{2}/btf?invalid=false&isFashion=true&freshProduct=false&memberEligible=true&src=&spec=&lptag=&ctag=&addtag=".format(
                product_id, item_id[0] or "", vendor_item_id[0] or ""
            )

            proxies = self.proxies()
            cert_ssl_path = self.cert_ssl_path()

            session = requests.Session()
            response = session.get(
                btf_url,
                headers=headers,
                timeout=5,
                proxies=proxies,
                verify=cert_ssl_path,
            )
            btf_content = response.json()
            r_data = btf_content.get("rData")

            if r_data is None:
                return {}
            page_list = r_data.get("pageList")

            if page_list is None:
                return {}
            widget_list = None
            for page in page_list:
                if "widgetList" in page:
                    widget_list = page.get("widgetList")
                    break
            if widget_list is None:
                return {}

            result_images = []
            iframes = []
            gifs = []
            text = ""

            for widget in widget_list:
                if "data" not in widget:
                    continue
                if (
                    "widgetBeanName" not in widget
                    and widget.get("widgetBeanName") != "MwebContentDetailWidget"
                ):
                    continue
                data = widget.get("data")
                if "vendorItemContent" not in data:
                    continue
                vendor_item_contents = data.get("vendorItemContent")
                if vendor_item_contents is None:
                    continue

                vendor_item_content_descriptions = []
                vendor_html_item_content_descriptions = []
                is_html = False
                no_space_images = []
                for vendor_item_content in vendor_item_contents:
                    if "contentType" in vendor_item_content and (
                        vendor_item_content["contentType"] == "HTML"
                        or vendor_item_content["contentType"] == "HTML_NO_SPACE"
                        or vendor_item_content["contentType"] == "TEXT"
                    ):
                        html_item = vendor_item_content.get(
                            "vendorItemContentDescriptions"
                        )
                        vendor_html_item_content_descriptions.append(html_item[0])
                        is_html = True
                    elif "contentType" in vendor_item_content and (
                        vendor_item_content["contentType"] == "IMAGE_NO_SPACE"
                        or vendor_item_content["contentType"] == "IMAGE"
                    ):
                        vendor_item_content_descriptions = vendor_item_content.get(
                            "vendorItemContentDescriptions"
                        )
                        for (
                            vendor_item_content_description
                        ) in vendor_item_content_descriptions:
                            if (
                                "contents" in vendor_item_content_description
                                and "detailType" in vendor_item_content_description
                                and vendor_item_content_description["detailType"]
                                == "IMAGE"
                            ):
                                no_space_images.append(
                                    vendor_item_content_description.get("contents")
                                )

                result_images.extend(no_space_images)
                if is_html:
                    contents = ""
                    for (
                        vendor_item_content_description
                    ) in vendor_html_item_content_descriptions:
                        if (
                            "contents" in vendor_item_content_description
                            and "detailType" in vendor_item_content_description
                            and vendor_item_content_description["detailType"] == "TEXT"
                        ):
                            contents = vendor_item_content_description.get("contents")
                            break

                    if contents == "":
                        continue

                    images, gifs, iframes, text = self.extract_images_and_text(contents)

                    result_images.extend(images)

            logger.info("Get Images Successfully")
            return {
                "images": result_images,
                "text": text,
                "gifs": gifs,
                "iframes": iframes,
            }
        except Exception as e:
            logger.error("Exception GET COUPANG BRF: {0}".format(str(e)))
            traceback.print_exc()
            if retry < 3:
                return self.get_coupang_btf_content(meta_url, headers, retry + 1)
            return {
                "images": [],
                "text": "",
                "gifs": [],
                "iframes": [],
            }

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

    def get_page_html(self, url, count=0, added_headers=None):
        try:
            if count > 5:
                return False

            cookie_jar = CookieJar()
            session = requests.Session()
            session.cookies = cookie_jar
            headers = random_mobile_header()
            if added_headers is not None:
                headers.update(added_headers)

            proxies = self.proxies()
            cert_ssl_path = self.cert_ssl_path()

            response = session.get(
                url,
                headers=headers,
                timeout=5,
                proxies=proxies,
                verify=cert_ssl_path,
            )
            info = response.content

            html = BeautifulSoup(info, "html.parser")
            # file_html = open("demo.html", "w", encoding="utf-8")
            # file_html.write(info.decode("utf-8"))
            # file_html.close()
            ld_json = html.find("script", {"type": "application/ld+json"})
            if ld_json is None:
                count = count + 1
                return self.get_page_html(url, count, added_headers)
            return {"html": html, "url": response.url, "headers": headers}
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            count = count + 1
            return self.get_page_html(url, count, added_headers)
