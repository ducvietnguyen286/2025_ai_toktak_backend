import json
import re
import traceback
from app.lib.logger import logger
from urllib.parse import urlparse
from app.lib.json_repair import loads


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
    name = html.find("span", {"id": "productTitle"})
    description = html.find("div", {"id": "feature-bullets"})
    image = html.find("img", {"id": "landingImage"})
    amazon_thumbnails = extract_amazon_images(html)

    thumbnails = amazon_thumbnails.get("main_images", [])
    images = amazon_thumbnails.get("large_images", [])

    domain = get_domain(base_url)

    core_price = html.find("div", {"id": "corePrice_feature_div"})
    if core_price:
        price = core_price.find("span", {"class": "a-offscreen"})
    else:
        core_desktop = html.find("div", {"id": "corePriceDisplay_desktop_feature_div"})
        if core_desktop:
            symbol = core_desktop.find("span", {"class": "a-price-symbol"})
            price = core_desktop.find("span", {"class": "a-price-whole"})
            price_fraction = core_desktop.find("span", {"class": "a-price-fraction"})
            price = f"{symbol.text.strip()}{price.text.strip()}{price_fraction.text.strip()}"
        else:
            price = ""

    text = html.find("div", {"id": "productDescription"})
    gifs = []
    iframes = []

    return {
        "name": name.text.strip() if name else "",
        "description": description.text.strip() if description else "",
        "stock": 1,
        "domain": domain,
        "brand": "",
        "image": image["src"],
        "thumbnails": thumbnails,
        "price": price.text.strip() if price else "",
        "url": domain,
        "base_url": base_url,
        "store_name": "",
        "url_crawl": base_url,
        "show_free_shipping": 0,
        "images": images,
        "text": text.text.strip() if text else "",
        "iframes": iframes,
        "gifs": gifs,
    }


def extract_amazon_images(html_content):
    """
    Trích xuất danh sách ảnh sản phẩm từ trang chi tiết Amazon.
    Bao gồm cả thumbnail và ảnh lớn.

    :param html_content: Nội dung HTML của trang Amazon (string hoặc bytes)
    :return: Dictionary chứa danh sách ảnh thumbnail và ảnh lớn
    """
    try:

        scripts = html_content.find_all("script", text=re.compile(r"colorImages"))
        json_str = None

        for script in scripts:
            script_text = script.text.strip()
            if "ImageBlockATF" in script_text:
                pattern = r"var data = ({.*?});"
                match = re.search(pattern, script_text, re.DOTALL)
                if match:
                    json_str = match.group(1)

        if not json_str:
            return {"thumbnails": [], "large_images": [], "main_images": []}

        try:
            data = loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON data: {str(e)}")
            return {"thumbnails": [], "large_images": [], "main_images": []}

        if "colorImages" not in data or "initial" not in data["colorImages"]:
            logger.warning("No colorImages.initial found in data")
            return {"thumbnails": [], "large_images": [], "main_images": []}

        images = data["colorImages"]["initial"]

        thumbnails = []
        large_images = []
        main_images = []

        for img in images:
            if isinstance(img, dict):
                if "hiRes" in img:
                    large_images.append(img["hiRes"])

                if "thumb" in img:
                    thumbnails.append(img["thumb"])

                if "main" in img and isinstance(img["main"], dict):
                    main_images.extend(list(img["main"].keys()))

        # Loại bỏ URL trùng lặp
        return {
            "thumbnails": list(set(thumbnails)),
            "large_images": list(set(large_images)),
            "main_images": list(set(main_images)),
        }

    except Exception as e:
        logger.error(
            f"Error extracting Amazon images: {str(e)}\n{traceback.format_exc()}"
        )
        return {"thumbnails": [], "large_images": [], "main_images": []}


class Parser:
    def __init__(self, html):
        self.html = html

    def parse(self, url):
        response = parse_response(self.html, url)
        return response
