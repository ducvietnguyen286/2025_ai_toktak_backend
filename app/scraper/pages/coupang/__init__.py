import datetime
import hmac
from http.cookiejar import CookieJar
import json
import os
import random
import time
import traceback
import uuid

from app.lib.header import generate_user_agent
from app.lib.logger import logger
from app.scraper.pages.coupang.headers import random_mobile_header
from app.scraper.pages.coupang.parser import Parser
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import requests
import hashlib
from app.extensions import redis_client
import concurrent.futures
from app.lib.url import get_real_url

from app.services.crawl_data import CrawlDataService


class CoupangScraper:
    def __init__(self, params):
        self.url = params["url"]
        self.batch_id = params.get("batch_id", "")
        self.fire_crawl_key = ""
        self.real_url = get_real_url(self.url)
        self.crawl_url_hash = hashlib.sha1(self.real_url.encode()).hexdigest()
        self.count_retry = 5

    def run(self):
        return self.run_wrap_sub_server()

    def run_wrap_sub_server(self):
        try:
            exist_data = CrawlDataService.find_crawl_data(
                self.crawl_url_hash, "COUPANG"
            )
            if exist_data:
                now = datetime.datetime.now()
                if (now - exist_data.created_at) <= datetime.timedelta(days=30):
                    return json.loads(exist_data.response)

                new_data = self.run_sub_server()
                if new_data:
                    try:
                        CrawlDataService.update_crawl_data(
                            exist_data.id, json.dumps(new_data)
                        )
                    except Exception as e:
                        logger.error(f"Error updating crawl data: {e}")
                    return new_data
                else:
                    return json.loads(exist_data.response)

            return self.run_sub_server()
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            return None

    def run_sub_server(self):
        try:
            sub_server_urls = os.getenv("SUB_SERVER_URLS", "")
            sub_server_urls = sub_server_urls.split(",")

            if len(sub_server_urls) == 0:
                return None

            api_config = []

            for sub_server_url in sub_server_urls:
                api_config.append(
                    {
                        "scraper_url": f"{sub_server_url}/api/crawl",
                        "cancel_url": f"{sub_server_url}/api/crawl/:request_id",
                        "status_url": f"{sub_server_url}/api/status",
                        "health_check_url": f"{sub_server_url}/api/health",
                    }
                )

            def generate_signature(body):
                minified = ""
                if body:
                    minified = json.dumps(body, separators=(",", ":"), sort_keys=True)
                timestamp = int(time.time())
                secret_key = os.getenv("SIGNATURE_SECRET_KEY", "")
                signature_base = f"{minified}|{timestamp}|{secret_key}"
                signature_hash = hmac.new(
                    secret_key.encode("utf-8"),
                    signature_base.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                return signature_hash, timestamp

            def health_check(health_check_url):
                try:
                    signature, timestamp = generate_signature(None)
                    resp = requests.get(
                        health_check_url,
                        headers={
                            "x-signature": signature,
                            "x-timestamp": str(timestamp),
                        },
                    )
                    res_json = resp.json()
                    if resp.status_code == 200 and res_json.get("overall") == True:
                        return True
                except Exception as e:
                    logger.error(f"Error health checking: {e}")

            final_api_config = []
            for config in api_config:
                if health_check(config["health_check_url"]):
                    final_api_config.append(config)

            random.shuffle(final_api_config)

            def call_api(api_url):
                try:
                    payload = {"url": self.url, "request_id": str(self.batch_id)}
                    signature, timestamp = generate_signature(payload)
                    resp = requests.post(
                        api_url,
                        headers={
                            "x-signature": signature,
                            "x-timestamp": str(timestamp),
                        },
                        json=payload,
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        res_json = resp.json()
                        return res_json
                except Exception as e:
                    logger.error(f"Error calling {api_url}: {e}")
                    print("error", e)
                return None

            def poll_status(status_url, timeout_seconds=120):
                """Poll status API cho đến khi có kết quả hoặc timeout"""
                start_time = time.time()
                poll_interval = 5  # Poll mỗi 5 giây

                while time.time() - start_time < timeout_seconds:
                    try:
                        resp = requests.get(
                            f"{status_url}",
                            params={"request_id": self.batch_id},
                            timeout=10,
                        )

                        if resp.status_code == 200:
                            result = resp.json()
                            status = result.get("status")

                            logger.info(
                                f"Poll status: {status} for request_id: {self.batch_id}"
                            )

                            if status == "completed":
                                logger.info(
                                    f"Job completed for request_id: {self.batch_id}"
                                )
                                return result  # Trả về data
                            elif status == "failed":
                                logger.error(
                                    f"Job failed for request_id: {self.batch_id}"
                                )
                                return None
                            elif status == "queued" or status == "in_progress":
                                # Tiếp tục polling
                                time.sleep(poll_interval)
                            else:
                                logger.warning(
                                    f"Unknown status: {status} for request_id: {self.batch_id}"
                                )
                                time.sleep(poll_interval)
                        else:
                            logger.error(
                                f"Status API returned {resp.status_code} for request_id: {self.batch_id}"
                            )
                            time.sleep(poll_interval)
                    except Exception as e:
                        logger.error(
                            f"Error polling status for request_id {self.batch_id}: {e}"
                        )
                        time.sleep(poll_interval)

                logger.error(f"Polling timeout for request_id: {self.batch_id}")
                return None

            def cancel_job(cancel_url):
                try:
                    final_url = cancel_url.replace(":request_id", self.batch_id)
                    signature, timestamp = generate_signature(None)
                    resp = requests.delete(
                        final_url,
                        headers={
                            "x-signature": signature,
                            "x-timestamp": str(timestamp),
                        },
                        timeout=10,
                    )
                    logger.info(
                        f"Cancel job request sent to {final_url}, status: {resp.status_code}"
                    )
                except Exception as e:
                    logger.error(f"Error canceling job at {cancel_url}: {e}")

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_config = {
                    executor.submit(call_api, config["scraper_url"]): config
                    for config in final_api_config
                }

                logger.info(f"Started {len(future_to_config)} concurrent API calls")

                completed_futures = []
                for future in concurrent.futures.as_completed(
                    future_to_config, timeout=60
                ):
                    try:
                        result = future.result()
                        config = future_to_config[future]

                        logger.info(
                            f"API {config['scraper_url']} completed, result: {result is not None}"
                        )

                        if result and isinstance(result, dict):
                            logger.info(
                                f"Valid result received from {config['scraper_url']}"
                            )

                            if result.get("status") == "queued":
                                logger.info(
                                    f"Job queued, polling status for request_id: {self.batch_id}"
                                )

                                final_result = poll_status(config["status_url"], 120)

                                if final_result:
                                    for other_future in future_to_config:
                                        if (
                                            other_future != future
                                            and not other_future.done()
                                        ):
                                            cancelled = other_future.cancel()
                                            other_config = future_to_config[
                                                other_future
                                            ]
                                            logger.info(
                                                f"Cancel future {other_config['scraper_url']}: {cancelled}"
                                            )

                                    for other_config in api_config:
                                        if other_config != config:
                                            logger.info(
                                                f"Sending cancel request to {other_config['cancel_url']}"
                                            )
                                            cancel_job(other_config["cancel_url"])

                                    logger.info(
                                        f"Job completed successfully from {config['scraper_url']}"
                                    )

                                    result = (
                                        final_result.get("data")
                                        if final_result
                                        else None
                                    )

                                    if not result:
                                        return None

                                    CrawlDataService.create_crawl_data(
                                        site="COUPANG",
                                        input_url=self.url,
                                        crawl_url=self.real_url,
                                        crawl_url_hash=self.crawl_url_hash,
                                        request=json.dumps("{}"),
                                        response=json.dumps(result),
                                    )
                                    return result
                                else:
                                    logger.error(
                                        f"Polling failed for request_id: {self.batch_id}"
                                    )
                                    return None
                            else:
                                for other_future in future_to_config:
                                    if (
                                        other_future != future
                                        and not other_future.done()
                                    ):
                                        cancelled = other_future.cancel()
                                        other_config = future_to_config[other_future]
                                        logger.info(
                                            f"Cancel future {other_config['scraper_url']}: {cancelled}"
                                        )

                                for other_config in api_config:
                                    if other_config != config:
                                        logger.info(
                                            f"Sending cancel request to {other_config['cancel_url']}"
                                        )
                                        cancel_job(other_config["cancel_url"])

                                logger.info(
                                    f"Job completed successfully from {config['scraper_url']}"
                                )

                                result = result.get("data") if result else None

                                if not result:
                                    return None

                                CrawlDataService.create_crawl_data(
                                    site="COUPANG",
                                    input_url=self.url,
                                    crawl_url=self.real_url,
                                    crawl_url_hash=self.crawl_url_hash,
                                    request=json.dumps("{}"),
                                    response=json.dumps(result),
                                )
                                return result
                        else:
                            logger.warning(
                                f"Invalid or empty result from {config['scraper_url']}"
                            )
                            return None

                    except Exception as e:
                        config = future_to_config[future]
                        logger.error(f"Exception in {config['scraper_url']}: {e}")
                        return None

                logger.warning(
                    f"All {len(completed_futures)} API calls completed but no valid result found"
                )

            return None
        except concurrent.futures.TimeoutError:
            logger.error("All API calls timed out")
            return None
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            return None

    def proxies(self, index=0):
        proxies = [
            {
                "server": "http://brd-customer-hl_8019b21f-zone-scraping_browser2-country-kr:wyfmhy3tqffj@brd.superproxy.io:33335",
                "is_crt": True,
            },
            {
                "server": "http://brd-customer-hl_8019b21f-zone-scraping_browser2-country-il:wyfmhy3tqffj@brd.superproxy.io:33335",
                "is_crt": True,
            },
            {
                "server": "http://27222558ddfa5c9d6449__cr.kr:69271afa03d6c430@gw.dataimpulse.com:823",
                "is_crt": False,
            },
            {
                "server": "http://spfvio0gqs:ypnQgFBX0r_ot377ec@kr.decodo.com:10000",
                "is_crt": False,
            },
            {
                "server": "http://hekqlibd-rotate:llv12cujeqjr@p.webshare.io:80",
                "is_crt": False,
            },
        ]
        random_proxy = proxies[index] if index < len(proxies) else proxies[0]
        return {
            "server": {
                "http": random_proxy["server"],
                "https": random_proxy["server"],
            },
            "is_crt": random_proxy["is_crt"],
            "count": 3,
        }

    def cert_ssl_path(self):
        COUPANG_FOLDER = os.path.join(os.getcwd(), "app/scraper/pages/coupang")
        return os.path.join(COUPANG_FOLDER, "ca_cert.crt")

    def run_puppeteer(self):
        req_id = str(uuid.uuid4())
        real_url = self.url

        mobile_url = get_real_url(real_url)

        task = {
            "req_id": req_id,
            "url": mobile_url,
        }
        # Publish task to puppeteer service
        redis_client.rpush("toktak:coupang_tasks", json.dumps(task))

        timeout = 30  # Giây
        start_time = time.time()
        print(f"Waiting for puppeteer result for req_id: {req_id}")
        while time.time() - start_time < timeout:
            result = redis_client.get(f"toktak:coupang_results:{req_id}")
            if result:
                redis_client.delete(f"toktak:coupang_results:{req_id}")
                data = json.loads(result.decode("utf-8"))
                if "error" in data:
                    return None
                return data
            time.sleep(1)

        redis_client.delete(f"toktak:coupang_results:{req_id}")

        print(f"Timeout waiting for puppeteer result for req_id: {req_id}")
        return None

    def run_selenium(self):
        try:
            req_id = str(uuid.uuid4())

            real_url = self.url

            real_url = get_real_url(real_url)

            task = {
                "req_id": req_id,
                "url": real_url,
            }
            redis_client.rpush("toktak:crawl_coupang_queue", json.dumps(task))
            timeout = 30  # Giây
            start_time = time.time()
            while time.time() - start_time < timeout:
                result = redis_client.get(f"toktak:result_coupang:{req_id}")
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

    def run_crawler_mobile(self):
        try:
            base_url = self.url
            real_url = self.url

            real_url = get_real_url(real_url)

            crawl_url_hash = hashlib.sha1(real_url.encode()).hexdigest()
            exist_data = CrawlDataService.find_crawl_data(crawl_url_hash, "COUPANG")
            if exist_data:
                return json.loads(exist_data.response)

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

            proxies = self.proxies(retry)
            server = proxies["server"]
            is_crt = proxies["is_crt"]
            if is_crt:
                cert_ssl_path = self.cert_ssl_path()
            else:
                cert_ssl_path = None

            session = requests.Session()
            response = session.get(
                btf_url,
                headers=headers,
                timeout=5,
                proxies=server,
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
            if retry < self.count_retry:
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
            if count > self.count_retry:
                return False

            cookie_jar = CookieJar()
            session = requests.Session()
            session.cookies = cookie_jar
            headers = random_mobile_header()
            if added_headers is not None:
                headers.update(added_headers)

            proxies = self.proxies(count)
            server = proxies["server"]
            is_crt = proxies["is_crt"]
            number_retry = proxies["count"]
            if is_crt:
                cert_ssl_path = self.cert_ssl_path()
            else:
                cert_ssl_path = None

            while number_retry > 0:
                headers.update({"user-agent": generate_user_agent()})
                number_retry = number_retry - 1
                print("number_retry", number_retry)
                print("count", count)
                response = session.get(
                    url,
                    headers=headers,
                    timeout=5,
                    proxies=server,
                    verify=cert_ssl_path,
                )
                info = response.content
                file_html = open("demo.html", "w", encoding="utf-8")
                file_html.write(info.decode("utf-8"))
                file_html.close()
                break

                html = BeautifulSoup(info, "html.parser")
                ld_json = html.find("script", {"type": "application/ld+json"})
                if ld_json is None:
                    continue
                break

            # if ld_json is None:
            #     count = count + 1
            #     return self.get_page_html(url, count, added_headers)
            # return {"html": html, "url": response.url, "headers": headers}
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            count = count + 1
            return self.get_page_html(url, count, added_headers)
