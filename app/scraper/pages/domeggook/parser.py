import logging
from urllib.parse import urlparse


def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


def parse_response(html):
    name = html.find("h1", {"id": "lInfoItemTitle"})
    description = html.find("meta", {"property": "og:description"})
    image = html.find("meta", {"property": "og:image"})
    url = html.find("meta", {"property": "og:url"})
    url_content = url["content"]
    domain = get_domain(url_content)
    single_price = html.find("div", {"class": "lItemPrice"})
    if single_price:
        price = single_price.text
    else:
        multiple_price = html.find(id="lAmtSectionTbl")
        if multiple_price:
            price = multiple_price.find("td", {"data-idx": 1}).text + "원"
        else:
            price = ""
    info_view_contents = html.find("div", {"id": "lInfoViewItemContents"})
    images = info_view_contents.find_all("img")
    src_images = [image["src"] for image in images]
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
        "url_crawl": url_content,
        "show_free_shipping": 0,
        "images": src_images,
        "text": "",
        "iframes": [],
    }


class Parser:
    def __init__(self, html):
        self.html = html

    def parse(self):
        response = parse_response(self.html)
        return response
