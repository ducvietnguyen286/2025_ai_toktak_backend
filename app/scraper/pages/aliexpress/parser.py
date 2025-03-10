import json
import logging
import re
import traceback
from urllib.parse import urlparse

from app.lib.logger import logger


def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


def parse_response(html, real_url):
    try:
        script = html.find("script", text=lambda t: t and "_d_c_.DCData" in t)
        if script:
            json_text = (
                script.string.split("_d_c_.DCData = ", 1)[1].rsplit("};", 1)[0] + "}"
            )
            dc_data = json.loads(json_text)

        name = html.find("meta", {"property": "og:title"})
        description = html.find("meta", {"property": "og:description"})
        images = dc_data.get("imagePathList")
        image_url = images[0] if images else ""
        domain = get_domain(real_url)
        price_show = ""
        price_currency = ""
        store_name = ""
        in_stock = 0
        video_url = ""
        meta_url = html.find("meta", {"property": "og:url"})

        return {
            "name": name["content"] if name else "",
            "description": description["content"] if description else "",
            "stock": in_stock,
            "domain": domain,
            "brand": "",
            "image": image_url,
            "thumbnails": images,
            "price": f"{price_show}{price_currency}",
            "url": real_url,
            "url_crawl": real_url,
            "base_url": real_url,
            "store_name": store_name,
            "show_free_shipping": 0,
            "meta_url": meta_url["content"] if meta_url else "",
            "images": images,
            "text": "",
            "iframes": [video_url] if video_url else [],
        }

    except Exception as e:
        logger.log(logging.ERROR, "Exception: {0}".format(str(e)))
        traceback.print_exc()
        print("Error: ", e)
        return {}


class Parser:
    def __init__(self, html):
        self.html = html

    def parse(self, real_url):
        response = parse_response(self.html, real_url)
        return response
