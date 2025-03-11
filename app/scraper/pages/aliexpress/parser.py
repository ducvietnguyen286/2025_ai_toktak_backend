import json
import logging
import re
import traceback
from urllib.parse import urlparse

from app.lib.logger import logger


def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


def format_currency(amount):
    amount = float(amount)
    return "{:,.0f}".format(amount)


def parse_response(html, real_url):
    try:
        script = html.find("script", text=lambda t: t and "_d_c_.DCData" in t)
        if script:
            json_text = (
                script.string.split("_d_c_.DCData = ", 1)[1].rsplit("};", 1)[0] + "}"
            )
            dc_data = json.loads(json_text)

        name = html.find("meta", {"property": "og:title"})["content"]
        description = html.find("meta", {"property": "og:description"})["content"]
        images = dc_data.get("imagePathList")
        image_url = images[0] if images else ""
        domain = get_domain(real_url)
        price_show = ""
        store_name = ""
        in_stock = 0
        video_url = ""
        meta_url = html.find("meta", {"property": "og:url"})

        ld_json = html.find("script", {"type": "application/ld+json"})
        if ld_json:
            ld_data = json.loads(ld_json.text)
            product = None
            videoObject = None
            for item in ld_data:
                if item.get("@type") == "Product":
                    product = item
                if item.get("@type") == "VideoObject":
                    videoObject = item
            name = product.get("name") if product else name
            description = product.get("description") if product else description
            offers = product.get("offers") if product else None
            if offers:
                price = offers.get("price")
                price_currency = offers.get("priceCurrency")
                price_formated = format_currency(price) if price != "" else ""
                price_show = f"{price_currency} {price_formated}"
                availability = offers.get("availability")
                in_stock = 1 if availability == "http://schema.org/InStock" else 0
            video_url = videoObject.get("contentUrl") if videoObject else ""

        return {
            "name": name,
            "description": description,
            "stock": in_stock,
            "domain": domain,
            "brand": "",
            "image": image_url,
            "thumbnails": images,
            "price": price_show,
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
