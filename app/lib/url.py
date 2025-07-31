from http.cookiejar import CookieJar
import re
from urllib.parse import parse_qs, urljoin, urlparse
import urllib.parse

import requests

from app.lib.logger import logger
from app.lib.header import generate_desktop_user_agent


def un_shotend_url(url):
    """
    Lấy URL gốc từ URL rút gọn.
    Kiểm tra và theo dõi tất cả các redirect cho đến khi tìm được URL cuối cùng.

    :param url: URL rút gọn cần kiểm tra
    :return: URL gốc sau khi đã theo dõi tất cả redirect
    """
    try:
        cookie_jar = CookieJar()
        session = requests.Session()
        session.cookies = cookie_jar
        user_agent = generate_desktop_user_agent()
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en",
            "priority": "u=0, i",
            "referer": "",
            "upgrade-insecure-requests": "1",
            "user-agent": user_agent,
        }
        response = session.get(url, headers=headers, allow_redirects=False)

        while response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get("Location")
            if not redirect_url:
                break

            if not redirect_url.startswith(("http://", "https://")):
                redirect_url = urljoin(url, redirect_url)

            response = session.get(redirect_url, headers=headers, allow_redirects=False)

            if redirect_url.startswith("https://star.aliexpress.com"):
                redirect_url_from_script = extract_redirect_url_from_script(
                    response.text
                )
                if redirect_url_from_script:
                    return redirect_url_from_script
                return urllib.parse.unquote(redirect_url)

            url = redirect_url

        return urllib.parse.unquote(url)

    except Exception as e:
        logger.error(f"Error unshortening URL {url}: {str(e)}")
        return url


def extract_redirect_url_from_script(html_content):
    """
    Trích xuất giá trị window.runParams.redirectUrl từ nội dung script trong HTML

    :param html_content: Nội dung HTML của trang web
    :return: URL redirect nếu tìm thấy, None nếu không tìm thấy
    """
    try:
        script_pattern = r"<script[^>]*>(.*?)</script>"
        scripts = re.findall(script_pattern, html_content, re.DOTALL)

        for script in scripts:
            redirect_pattern = (
                r'window\.runParams\.redirectUrl\s*=\s*[\'"]([^\'"]+)[\'"]'
            )
            match = re.search(redirect_pattern, script)
            if match:
                redirect_url = match.group(1)
                return urllib.parse.unquote(redirect_url)

        return None

    except Exception as e:
        logger.error(f"Error extracting redirect URL from script: {str(e)}")
        return None


def get_coupang_real_url(real_url, parsed_url):
    if "link.coupang.com" in parsed_url.netloc:
        logger.info(f"real_url: {real_url}")
        real_url = un_shotend_url(real_url)
        parsed_url = urlparse(real_url)

    path = parsed_url.path

    query_params = parsed_url.query
    query_params_dict = parse_qs(query_params)

    item_id = query_params_dict.get("itemId")
    vendor_item_id = query_params_dict.get("vendorItemId")

    path = path.replace("/vp/", "/vm/")
    target_item_id = item_id[0] if item_id else ""
    target_vendor_item_id = vendor_item_id[0] if vendor_item_id else ""

    path_mobile = path
    query_params = ""
    if target_item_id != "":
        query_params = query_params + "&itemId=" + target_item_id
    if target_vendor_item_id != "":
        query_params = query_params + "&vendorItemId=" + target_vendor_item_id
    query_params = query_params[1:]
    real_url = "https://m.coupang.com" + path_mobile + "?" + query_params
    return real_url


def get_domeggook_real_url(real_url, parsed_url):
    path = parsed_url.path
    if not path.strip("/").isdigit():
        real_url = un_shotend_url(real_url)
        parsed_url = urlparse(real_url)
    else:
        real_url = real_url

    if "mobile." in real_url:
        real_url = real_url.replace("mobile.", "")

    real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    return real_url


def get_aliexpress_real_url(real_url, parsed_url):
    if (
        "https://s.click.aliexpress.com/" in real_url
        or "https://a.aliexpress.com/" in real_url
    ):
        real_url = un_shotend_url(real_url)
        parsed_url = urlparse(real_url)
    else:
        real_url = real_url

    real_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    return real_url


def get_real_url(url):
    logger.info(f"url: {url}")
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc
    if "coupang." in netloc:
        return get_coupang_real_url(url, parsed_url)
    elif "domeggook." in netloc:
        return get_domeggook_real_url(url, parsed_url)
    elif "aliexpress." in netloc:
        return get_aliexpress_real_url(url, parsed_url)
    return url


def get_site_by_url(url):
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc
    if "coupang." in netloc:
        return "COUPANG"
    elif "domeggook." in netloc:
        return "DOMEGGOOK"
    elif "aliexpress." in netloc:
        return "ALIEXPRESS"
    elif "amazon." in netloc or "amzn." in netloc:
        return "AMAZON"
    elif "ebay." in netloc:
        return "EBAY"
    elif "walmart." in netloc:
        return "WALMART"
    elif "shopee." in netloc:
        return "SHOPEE"
    return "UNKNOWN"
