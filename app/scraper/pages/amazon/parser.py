import json
import re
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
    description = html.find("div", {"id": "feature-bullets"})
    image = html.find("img", {"id": "landingImage"})
    amazon_thumbnails = extract_amazon_images(html)

    print("--------------------------------")
    print(amazon_thumbnails)
    print("--------------------------------")

    domain = get_domain(base_url)

    core_price = html.find("div", {"id": "corePrice_feature_div"})
    price = core_price.find("span", {"class": "a-offscreen"})

    text = html.find("div", {"id": "productDescription"})
    images = []
    gifs = []
    iframes = []

    return {
        "name": name.text.strip() if name else "",
        "description": description.text.strip() if description else "",
        "stock": 1,
        "domain": domain,
        "brand": "",
        "image": image["src"],
        "thumbnails": [image["src"]],
        "price": price,
        "url": domain,
        "base_url": base_url,
        "store_name": "",
        "url_crawl": base_url,
        "show_free_shipping": 0,
        "images": images,
        "text": text,
        "iframes": iframes,
        "gifs": gifs,
    }


def extract_amazon_images(html_content):
    """
    Trích xuất danh sách ảnh sản phẩm từ trang chi tiết Amazon.
    Bao gồm cả thumbnail và ảnh lớn.

    :param html_content: Nội dung HTML của trang Amazon
    :return: Dictionary chứa danh sách ảnh thumbnail và ảnh lớn
    """
    try:
        # Tìm tất cả các script chứa dữ liệu ảnh
        script_pattern = r"<script[^>]*>(.*?)</script>"
        scripts = re.findall(script_pattern, html_content, re.DOTALL)

        # Pattern để tìm dữ liệu ảnh trong script
        image_data_pattern = r"ImageBlockATF.*?colorImages.*?initial\s*:\s*(\[.*?\])"
        image_data_pattern_alt = (
            r"ImageGalleryATF.*?colorImages.*?initial\s*:\s*(\[.*?\])"
        )

        # Tìm dữ liệu ảnh trong các script
        image_data = None
        for script in scripts:
            match = re.search(image_data_pattern, script, re.DOTALL)
            if not match:
                match = re.search(image_data_pattern_alt, script, re.DOTALL)
            if match:
                image_data = match.group(1)
                break

        if not image_data:
            return {"thumbnails": [], "large_images": []}

        # Parse JSON data
        try:
            images = json.loads(image_data)
        except json.JSONDecodeError:
            # Nếu không parse được JSON, thử tìm ảnh trực tiếp từ HTML
            return extract_amazon_images_from_html(html_content)

        # Trích xuất URL ảnh
        thumbnails = []
        large_images = []

        for img in images:
            if isinstance(img, dict):
                # Lấy URL ảnh lớn
                if "hiRes" in img:
                    large_images.append(img["hiRes"])
                elif "large" in img:
                    large_images.append(img["large"])

                # Lấy URL thumbnail
                if "thumb" in img:
                    thumbnails.append(img["thumb"])
                elif "small" in img:
                    thumbnails.append(img["small"])

        return {
            "thumbnails": list(set(thumbnails)),  # Loại bỏ URL trùng lặp
            "large_images": list(set(large_images)),
        }

    except Exception as e:
        logger.error(f"Error extracting Amazon images: {str(e)}")
        return {"thumbnails": [], "large_images": []}


def extract_amazon_images_from_html(html_content):
    """
    Trích xuất ảnh trực tiếp từ HTML khi không tìm thấy dữ liệu trong script
    """
    try:
        # Pattern để tìm ảnh trong HTML
        image_pattern = r'data-old-hires="([^"]+)"'
        images = re.findall(image_pattern, html_content)

        # Nếu không tìm thấy ảnh với pattern trên, thử pattern khác
        if not images:
            image_pattern = r'data-a-dynamic-image="([^"]+)"'
            matches = re.findall(image_pattern, html_content)
            if matches:
                try:
                    # Parse JSON string chứa thông tin ảnh
                    image_data = json.loads(matches[0])
                    images = list(image_data.keys())
                except:
                    pass

        # Loại bỏ URL trùng lặp và trả về
        unique_images = list(set(images))
        return {"thumbnails": unique_images, "large_images": unique_images}

    except Exception as e:
        logger.error(f"Error extracting Amazon images from HTML: {str(e)}")
        return {"thumbnails": [], "large_images": []}


class Parser:
    def __init__(self, html):
        self.html = html

    def parse(self, url):
        response = parse_response(self.html, url)
        return response
