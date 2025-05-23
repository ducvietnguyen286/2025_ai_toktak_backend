from http.cookiejar import CookieJar
import json
import random
import traceback
from app.lib.header import generate_desktop_user_agent, generate_user_agent
from app.lib.logger import logger
from app.scraper.pages.coupang.headers import random_mobile_header
from app.scraper.pages.coupang.parser import Parser
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import requests
import hashlib
from app.lib.json_repair import loads

from app.services.crawl_data_mongo import CrawlDataMongoService


class CoupangScraper:
    def __init__(self, params):
        self.url = params["url"]
        self.fire_crawl_key = ""

    def run(self):
        return self.run_crawler()

    def proxies(self):
        auth = "dyhnvzbd:ikzxkk88sckd"

        proxy_list = [
            f"http://{auth}@198.23.239.134:6540",
            f"http://{auth}@107.172.163.27:6543",
            f"http://{auth}@207.244.217.165:6712",
            f"http://{auth}@161.123.152.115:6360",
            f"http://{auth}@23.94.138.75:6349",
            f"http://{auth}@216.10.27.159:6837",
            f"http://{auth}@136.0.207.84:6661",
            f"http://{auth}@64.64.118.149:6732",
            f"http://{auth}@142.147.128.93:6593",
        ]
        selected_proxy = random.choice(proxy_list)
        return {
            "http": selected_proxy,
            "https": selected_proxy,
        }

    def run_fire_crawler(self):
        try:
            crawl_url_hash = hashlib.sha1(self.url.encode()).hexdigest()
            exist_data = CrawlDataMongoService.find_crawl_data(crawl_url_hash)
            if exist_data:
                return json.loads(exist_data.response)

            url = "https://api.firecrawl.dev/v1/scrape"

            payload = {
                "url": self.url,
                "formats": ["rawHtml"],
                "timeout": 30000,
                "onlyMainContent": True,
                "blockAds": True,
                "proxy": "basic",
            }
            headers = {
                "Authorization": f"Bearer {self.fire_crawl_key}",
                "Content-Type": "application/json",
            }

            response = requests.request("POST", url, json=payload, headers=headers)

            if response.status_code == 200:
                json_response = response.json()
                data = json_response.get("data")
                if "rawHtml" in data:
                    raw_html = data["rawHtml"]
                    html = BeautifulSoup(raw_html, "html.parser")
                    response_data = Parser(html, self.url).parse(self.url)

                    if response_data:
                        meta_url = response_data.get("meta_url")
                        logger.info("meta_url: {0}".format(meta_url))
                        coupang_btf_content = self.run_crawler_fire_get_detail(meta_url)
                        response_data.update(coupang_btf_content)

                        if (
                            response_data
                            and "images" in response_data
                            and len(response_data["images"]) > 0
                        ):
                            CrawlDataMongoService.create_crawl_data(
                                site="COUPANG",
                                input_url=self.url,
                                crawl_url=self.url,
                                crawl_url_hash=crawl_url_hash,
                                request=json.dumps(headers),
                                response=json.dumps(response_data),
                            )

                        return response_data

            return {}
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            return {}

    def run_crawler_fire_get_detail(self, meta_url):
        try:
            parsed_base_url = urlparse(self.url)
            path = parsed_base_url.path
            parsed_url = urlparse(meta_url)
            query_params = parsed_url.query
            query_params_dict = parse_qs(query_params)
            item_id = query_params_dict.get("itemId")
            vendor_item_id = query_params_dict.get("vendorItemId")
            product_id = path.split("/")[-1]
            item_id = item_id[0] if item_id else ""
            vendor_item_id = vendor_item_id[0] if vendor_item_id else ""

            btf_url = "https://m.coupang.com/vm/sdp/v3/mweb/products/{0}/items/{1}/vendor-items/{2}/btf?invalid=false&isFashion=true&freshProduct=false&memberEligible=true&src=&spec=&lptag=&ctag=&addtag=".format(
                product_id, item_id, vendor_item_id
            )

            url = "https://api.firecrawl.dev/v1/scrape"

            payload = {
                "url": btf_url,
                "formats": ["rawHtml"],
                "timeout": 30000,
                "onlyMainContent": True,
                "blockAds": True,
                "proxy": "basic",
            }
            headers = {
                "Authorization": f"Bearer {self.fire_crawl_key}",
                "Content-Type": "application/json",
            }

            response = requests.request("POST", url, json=payload, headers=headers)

            result_images = []
            iframes = []
            gifs = []
            text = ""

            if response.status_code == 200:
                json_response = response.json()
                data = json_response.get("data")
                if "rawHtml" in data:
                    markdown = data["rawHtml"]
                    btf_content = json.loads(markdown)

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

                    for widget in widget_list:
                        if "data" not in widget:
                            continue
                        if (
                            "widgetBeanName" not in widget
                            and widget.get("widgetBeanName")
                            != "MwebContentDetailWidget"
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
                                vendor_html_item_content_descriptions.append(
                                    html_item[0]
                                )
                                is_html = True
                            elif "contentType" in vendor_item_content and (
                                vendor_item_content["contentType"] == "IMAGE_NO_SPACE"
                                or vendor_item_content["contentType"] == "IMAGE"
                            ):
                                vendor_item_content_descriptions = (
                                    vendor_item_content.get(
                                        "vendorItemContentDescriptions"
                                    )
                                )
                                for (
                                    vendor_item_content_description
                                ) in vendor_item_content_descriptions:
                                    if (
                                        "contents" in vendor_item_content_description
                                        and "detailType"
                                        in vendor_item_content_description
                                        and vendor_item_content_description[
                                            "detailType"
                                        ]
                                        == "IMAGE"
                                    ):
                                        no_space_images.append(
                                            vendor_item_content_description.get(
                                                "contents"
                                            )
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
                                    and vendor_item_content_description["detailType"]
                                    == "TEXT"
                                ):
                                    contents = vendor_item_content_description.get(
                                        "contents"
                                    )
                                    break

                            if contents == "":
                                continue

                            images, gifs, iframes, text = self.extract_images_and_text(
                                contents
                            )

                            result_images.extend(images)

                    logger.info("Get Images Successfully")

            return {
                "images": result_images,
                "text": text,
                "gifs": gifs,
                "iframes": iframes,
            }
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            return {
                "images": [],
                "text": "",
                "gifs": [],
                "iframes": [],
            }

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

    def run_crawler(self):
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
            exist_data = CrawlDataMongoService.find_crawl_data(crawl_url_hash)
            if exist_data:
                return json.loads(exist_data.response)

            added_headers = {"referer": real_url}
            coupang_data = self.get_page_html(real_url, 0, added_headers)

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
                    CrawlDataMongoService.create_crawl_data(
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

            session = requests.Session()
            response = session.get(btf_url, headers=headers, timeout=5, proxies=proxies)
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
            mobile_user_agent = generate_user_agent()
            headers.update({"user-agent": mobile_user_agent})

            proxies = self.proxies()

            response = session.get(url, headers=headers, timeout=5, proxies=proxies)
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
