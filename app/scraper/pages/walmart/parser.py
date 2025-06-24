import json

from bs4 import BeautifulSoup
from urllib.parse import urlparse


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
    ld_json = html.find("script", {"id": "__NEXT_DATA__"})
    if ld_json is None:
        return {}

    data = json.loads(ld_json.text.strip())

    if not data:
        return {}

    initial_data = data.get("props", {}).get("pageProps", {}).get("initialData", {})
    if not initial_data:
        return {}

    product_data = initial_data.get("data", {}).get("product", {})
    if not product_data:
        return {}

    idml = initial_data.get("data", {}).get("idml", {})

    name = product_data.get("name", "")
    description = product_data.get("shortDescription", "")
    if description:
        # Parse HTML description and extract text
        description_html = BeautifulSoup(description, "html.parser")
        description = description_html.get_text(separator=" ", strip=True)
        description = description.replace("\n", " ")

    image_info = product_data.get("imageInfo", {})
    all_images = image_info.get("allImages", [])
    image = image_info.get("thumbnailUrl", "")
    thumbnails = [img.get("url") for img in all_images]

    price_info = product_data.get("priceInfo", {})
    current_price = price_info.get("currentPrice", {})
    show_price = current_price.get("priceString", "")

    seller_name = product_data.get("sellerDisplayName", "")
    brand = product_data.get("brand", "")

    domain = get_domain(base_url)

    images = []
    gifs = []
    iframes = []
    text = ""

    if idml:
        long_description = idml.get("longDescription", "")
        html_long_description = BeautifulSoup(long_description, "html.parser")
        images, gifs, iframes, text = extract_images_and_text(html_long_description)

    return {
        "name": name,
        "description": description,
        "stock": 1,
        "domain": domain,
        "brand": brand,
        "image": image,
        "thumbnails": thumbnails,
        "price": show_price,
        "url": base_url,
        "base_url": base_url,
        "store_name": seller_name,
        "url_crawl": base_url,
        "show_free_shipping": 0,
        "images": images,
        "text": text,
        "iframes": iframes,
        "gifs": gifs,
    }


class Parser:
    def __init__(self, html):
        self.html = html

    def parse(self, url):
        response = parse_response(self.html, url)
        return response
