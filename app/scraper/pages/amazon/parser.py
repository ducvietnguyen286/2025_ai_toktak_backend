from app.lib.logger import logger
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
    name = html.find("h1", {"id": "productTitle"})
    description = html.find("meta", {"property": "og:description"})
    image = html.find("meta", {"property": "og:image"})
    url = html.find("meta", {"property": "og:url"})
    url_content = url["content"] if url else ""
    domain = get_domain(url_content)
    single_price = html.find("div", {"class": "lItemPrice"})
    price = ""
    if single_price:
        price = single_price.text
    else:
        multiple_price = html.find(id="lAmtSectionTbl")
        if multiple_price:
            price = multiple_price.find("td", {"data-idx": 1}).text + "원"
        else:
            price = ""

    if price == "":
        lGGookDealAmt = html.find("div", {"class": "lGGookDealAmt"})
        if lGGookDealAmt:
            html_string = lGGookDealAmt.find("b")
            if html_string:
                clean_text = html_string.get_text(strip=True)
                logger.error(clean_text)
                price = clean_text

    info_view_contents = html.find("div", {"id": "lInfoViewItemContents"})

    images, gifs, iframes, text = extract_images_and_text(info_view_contents)

    return {
        "name": name.text.strip() if name else "",
        "description": description["content"],
        "stock": 1,
        "domain": domain,
        "brand": "",
        "image": image["content"],
        "thumbnails": [image["content"]],
        "price": price,
        "url": url_content,
        "base_url": base_url,
        "store_name": "",
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
