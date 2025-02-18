import json
import logging
import traceback
from urllib.parse import urlparse
from urllib.parse import urljoin

from app.lib.logger import logger


def out_of_stock(html):
    quantity_mask = html.find("div", {"class": "prod-buy-quantity-and-footer__mask"})
    return 0 if "style" in quantity_mask.attrs else 1


def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


def format_currency(amount):
    amount = int(amount)
    return "{:,.0f}".format(amount)


def parse_mobile_response(html, url):
    try:
        ld_json = html.find("script", {"type": "application/ld+json"})
        if ld_json is None:
            return {}
        data = json.loads(ld_json.text)
        name = data.get("name")
        images = data.get("image")
        image_url = images[0] if images else ""
        domain = get_domain(url)
        offers = data.get("offers")
        price = offers.get("price") if offers else ""
        price_show = format_currency(price) if price != "" else ""
        availability = offers.get("availability") if offers else ""
        brand = data.get("brand")
        store_name = brand.get("name") if brand else ""
        in_stock = 1 if "InStock" in availability else 0
        meta_url = html.find("meta", {"property": "og:url"})

        return {
            "name": name,
            "stock": in_stock,
            "domain": domain,
            "brand": "",
            "image": image_url,
            "price": "{0}원".format(price_show) if price_show != "" else 0,
            "url": url,
            "url_crawl": url,
            "store_name": store_name,
            "show_free_shipping": 0,
            "meta_url": meta_url["content"] if meta_url else "",
        }
    except Exception as e:
        logger.log(logging.ERROR, "Exception: {0}".format(str(e)))
        traceback.print_exc()
        return {}


def extract_images_and_text(soup, base_url):

    images = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            full_url = urljoin(base_url, src)
            images.append(full_url)

    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)

    return images, text


class Parser:
    def __init__(self, html, url):
        self.html = html
        self.url = url

    def parse(self):
        response = parse_mobile_response(self.html, self.url)
        return response
