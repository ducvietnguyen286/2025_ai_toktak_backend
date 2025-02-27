import json
import logging
import traceback
from urllib.parse import parse_qs, urlparse
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


def parse_mobile_response(html, url, base_url):
    try:
        ld_json = html.find("script", {"type": "application/ld+json"})
        if ld_json is None:
            return {}
        data = json.loads(ld_json.text)

        name = data.get("name")
        description = data.get("description")
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

        meta_url_tag = html.find("meta", {"property": "og:url"})
        meta_url = meta_url_tag["content"] if meta_url_tag else ""

        parsed_url = urlparse(meta_url)
        meta_base_url = "{0}://{1}".format(parsed_url.scheme, parsed_url.netloc)
        query_params = parsed_url.query
        query_params_dict = parse_qs(query_params)
        item_id = query_params_dict.get("itemId")
        vendor_item_id = query_params_dict.get("vendorItemId")

        if (
            not item_id
            or not vendor_item_id
            or len(item_id) == 0
            or len(vendor_item_id) == 0
        ):
            next_data_json = html.find("script", {"id": "__NEXT_DATA__"})
            if next_data_json:
                next_data = json.loads(next_data_json.text)
                props = next_data.get("props")
                page_props = props.get("pageProps")
                properties = page_props.get("properties")
                item_detail = properties.get("itemDetail")
                item_id = item_detail.get("itemId")
                vendor_item_id = item_detail.get("vendorItemId")

                meta_url = "{0}?itemId={1}&vendorItemId={2}".format(
                    meta_base_url, item_id, vendor_item_id
                )

        return {
            "name": name,
            "description": description,
            "stock": in_stock,
            "domain": domain,
            "brand": "",
            "image": image_url,
            "thumbnails": images,
            "price": "{0}원".format(price_show) if price_show != "" else "0",
            "url": url,
            "url_crawl": url,
            "base_url": base_url,
            "store_name": store_name,
            "show_free_shipping": 0,
            "meta_url": meta_url if meta_url else "",
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

    def parse(self, base_url):
        response = parse_mobile_response(self.html, self.url, base_url)
        return response
