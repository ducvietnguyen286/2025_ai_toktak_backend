from http.cookiejar import CookieJar
import json
import traceback
from app.lib.header import generate_user_agent
from app.lib.logger import logger
from app.scraper.pages.coupang.headers import random_mobile_header
from app.scraper.pages.coupang.parser import Parser
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import requests


class CoupangScraper:
    def __init__(self, params):
        self.url = params["url"]

    def run(self):
        try:
            base_url = self.url
            real_url = self.url

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

            added_headers = {
                "referer": real_url,
            }
            coupang_data = self.get_page_html(real_url, 0, added_headers)

            logger.info("Get Page HTML: {0}".format(coupang_data))

            if not coupang_data:
                return {}
            html = coupang_data["html"]
            url = coupang_data["url"]
            headers = coupang_data["headers"]
            response = Parser(html, url).parse(base_url)

            if response:
                meta_url = response.get("meta_url")
                logger.info("meta_url: {0}".format(meta_url))
                coupang_btf_content = self.get_coupang_btf_content(meta_url, headers)
                response.update(coupang_btf_content)
            return response
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            return {}

    def get_coupang_btf_content(self, meta_url, headers):
        try:
            parsed_url = urlparse(meta_url)
            path = parsed_url.path
            query_params = parsed_url.query
            query_params_dict = parse_qs(query_params)
            item_id = query_params_dict.get("itemId")
            vendor_item_id = query_params_dict.get("vendorItemId")
            product_id = path.split("/")[-1]

            btf_url = "https://m.coupang.com/vm/sdp/v3/mweb/products/{0}/items/{1}/vendor-items/{2}/btf?invalid=false&isFashion=true&freshProduct=false&memberEligible=true&src=&spec=&lptag=&ctag=&addtag=".format(
                product_id, item_id[0], vendor_item_id[0]
            )

            session = requests.Session()
            response = session.get(btf_url, headers=headers, timeout=5)
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
            images = []
            text = ""
            for widget in widget_list:
                if "data" not in widget:
                    continue
                data = widget.get("data")
                if "vendorItemContent" not in data:
                    continue
                vendor_item_contents = data.get("vendorItemContent")
                if vendor_item_contents is None:
                    continue

                vendor_item_content_descriptions = []
                for vendor_item_content in vendor_item_contents:
                    if (
                        "contentType" in vendor_item_content
                        and vendor_item_content["contentType"] == "HTML"
                    ):
                        vendor_item_content_descriptions = vendor_item_content.get(
                            "vendorItemContentDescriptions"
                        )
                        break

                vendor_item_content_description = vendor_item_content_descriptions[0]

                contents = vendor_item_content_description.get("contents")

                data = self.extract_images_and_text(contents)
                images.extend(data[0])
                text += data[1]
            return {"images": images, "text": text}
        except Exception as e:
            logger.error("Exception: {0}".format(str(e)))
            traceback.print_exc()
            return {}

    def extract_images_and_text(self, html):
        soup = BeautifulSoup(html, "html.parser")

        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(src)

        text = soup.get_text(separator=" ", strip=True)

        return images, text

    def get_page_html(self, url, count=0, added_headers=None):
        try:
            if count > 10:
                return False

            cookie_jar = CookieJar()
            session = requests.Session()
            session.cookies = cookie_jar
            headers = random_mobile_header()
            if added_headers is not None:
                headers.update(added_headers)
            mobile_user_agent = generate_user_agent()
            headers.update({"user-agent": mobile_user_agent})

            response = session.get(url, headers=headers, timeout=5)
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
