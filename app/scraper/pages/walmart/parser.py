import json
from app.lib.logger import logger
from urllib.parse import urlparse
import re


def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


def extract_images_and_text(html):
    images = []
    gifs = []
    iframes = []
    for img in html.find_all("img"):
        src = img.get("src")
        if src:
            if src.endswith(".gif"):
                gifs.append(src)
            else:
                images.append(src)

    for iframe in html.find_all("iframe"):
        src = iframe.get("src")
        if src:
            iframes.append(src)

    text = html.get_text(separator=" ", strip=True)

    return images, gifs, iframes, text


def parse_response(html, base_url):
    ld_jsons = html.find_all("script", {"type": "application/ld+json"})
    if ld_jsons is None:
        return {}

    data = {}
    for ld_json in ld_jsons:
        text = ld_json.text.strip()
        if text:
            data = json.loads(text)
            if data.get("@type") == "Product":
                break

    if not data:
        return {}

    desc_ifr = html.find("iframe", {"id": "desc_ifr"})
    desc_ifr_url = ""
    if desc_ifr:
        desc_ifr_url = desc_ifr.get("src")

    name = data.get("name", "")
    image = data.get("image", "")
    domain = get_domain(base_url)
    offers = data.get("offers", {})
    price = offers.get("price", "")
    show_price = f"${price}"

    return {
        "name": name if name else "",
        "description": "",
        "stock": 1,
        "domain": domain,
        "brand": "",
        "image": image[0] if image else "",
        "thumbnails": image,
        "price": show_price,
        "url": base_url,
        "base_url": base_url,
        "store_name": "",
        "url_crawl": base_url,
        "show_free_shipping": 0,
        "images": [],
        "text": [],
        "iframes": [],
        "gifs": [],
        "desc_ifr_url": desc_ifr_url,
    }


class Parser:
    def __init__(self, html):
        self.html = html

    def parse(self, url):
        response = parse_response(self.html, url)
        return response
