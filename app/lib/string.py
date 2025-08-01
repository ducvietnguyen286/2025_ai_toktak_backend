import json
import random
import re

import hashlib
import base64
import string
from app.lib.header import generate_desktop_user_agent
import const
import uuid
from app.lib.logger import logger
from urllib.parse import urljoin

from datetime import datetime


def is_json(data):
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False


def split_text_by_sentences(text, num_captions):
    sentences = [text]

    if len(sentences) < num_captions:
        sentences += [""] * (num_captions - len(sentences))
        return sentences[:num_captions]

    group_size = len(sentences) / num_captions
    captions = []
    for i in range(num_captions):
        start_index = int(round(i * group_size))
        end_index = int(round((i + 1) * group_size))
        caption = " ".join((sentences[start_index:end_index]) or "")
        # Thêm "\n" sau dấu chấm nếu không phải là dấu chấm cuối cùng (cho phép có khoảng trắng sau dấu chấm)
        modified_text = re.sub(r"\.(?!\s*$)", ".\n", caption)
        captions.append(modified_text)
    return captions


def get_level_images(level):
    """
    Trả về danh sách ảnh theo cấp độ với một ảnh ngẫu nhiên được đánh dấu active.
    """
    base_url = "/img/level/"
    images = []

    if level == 0:
        images = [
            {"url": f"{base_url}level_0.png", "active": ""},
            {"url": f"{base_url}level_0_next.png", "active": ""},
        ]
    elif level == 1:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_1_next.png", "active": "active"},
        ]
    elif level == 2:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_2_next.png", "active": "active"},
        ]
    elif level == 3:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_3_next.png", "active": "active"},
        ]
    elif level == 4:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_4.png", "active": ""},
            {"url": f"{base_url}level_4_next.png", "active": "active"},
        ]
    elif level == 5:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_4.png", "active": ""},
            {"url": f"{base_url}level_5.png", "active": ""},
            {"url": f"{base_url}level_5_next.png", "active": "active"},
        ]
    elif level == 6:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_4.png", "active": ""},
            {"url": f"{base_url}level_5.png", "active": ""},
            {"url": f"{base_url}level_6.png", "active": ""},
            {"url": f"{base_url}level_6_next.png", "active": "active"},
        ]
    elif level == 7:
        images = [
            {"url": f"{base_url}level_1.png", "active": ""},
            {"url": f"{base_url}level_2.png", "active": ""},
            {"url": f"{base_url}level_3.png", "active": ""},
            {"url": f"{base_url}level_4.png", "active": ""},
            {"url": f"{base_url}level_5.png", "active": ""},
            {"url": f"{base_url}level_6.png", "active": ""},
            {"url": f"{base_url}level_7.png", "active": "active"},
        ]

    return images


def generate_short_code(url):
    """Tạo mã rút gọn bằng Base62 từ hash của URL"""
    hash_value = hashlib.md5(url.encode()).digest()
    short_code = base64.urlsafe_b64encode(hash_value)[:6].decode("utf-8")
    return short_code


def generate_shortcode(length=6):
    characters = string.ascii_letters + string.digits
    shortcode = "".join(random.choice(characters) for _ in range(length))
    return shortcode


def should_replace_shortlink(url):
    excluded_domains = [
        "https://link.coupang.com",
        "https://s.click.aliexpress.com",
        "https://a.aliexpress.com",
    ]

    return not any(url.startswith(domain) for domain in excluded_domains)


def update_ads_content(url, content):

    if "https://link.coupang.com/" in url:
        replace_str = get_ads_content(url)
        content = content.replace(
            "<h2>ADS_CONTENT_TOKTAK</h2>",
            f"<h2>{replace_str}</h2>",
        )
        # content = f"<h2>이 포스팅은 쿠팡 파트너스 수익 활동의 일환으로, 이에 따른 일정액의 수수료를 제공 받습니다.</h2>\n\n\n\n{content}"
    elif "https://s.click.aliexpress.com" in url or "https://a.aliexpress.com" in url:
        replace_str = get_ads_content(url)
        content = content.replace(
            "<h2>ADS_CONTENT_TOKTAK</h2>",
            f"<h2>{replace_str}</h2>",
        )
    else:
        content = content.replace("<h2>ADS_CONTENT_TOKTAK</h2>", "")
    return content


def update_ads_content_txt(url, content):

    if "https://link.coupang.com/" in url:
        content = get_ads_content(url)
        # content = f"이 포스팅은 쿠팡 파트너스 수익 활동의 일환으로, 이에 따른 일정액의 수수료를 제공 받습니다.\n\n\n\n{content}"
    elif "https://s.click.aliexpress.com" in url or "https://a.aliexpress.com" in url:
        content = get_ads_content(url)
    else:
        content = ""
    return content


def get_ads_content(url):
    if "https://link.coupang.com/" in url:
        return "이 포스팅은 쿠팡 파트너스 수익 활동의 일환으로, 이에 따른 일정액의 수수료를 제공 받습니다."
    elif "https://s.click.aliexpress.com" in url or "https://a.aliexpress.com" in url:
        return "이 포스팅은 알리 어필리에이트 수익 활동의 일환으로, 이에 따른 일정액의 수수료를 제공 받습니다."
    else:
        return ""


def merge_by_key(array1, array2, key_merge="title"):
    """
    Gộp 2 mảng dict theo title.
    Nếu title trùng nhau thì phần tử ở array2 sẽ ghi đè vào array1.
    """
    merged = {item[key_merge]: item for item in array1}
    for item in array2:
        merged[item[key_merge]] = item  # Ghi đè nếu title trùng
    return list(merged.values())


def generate_random_nick_name(email):
    prefix = email.split("@")[0] if email else ""
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{random_suffix}"


def replace_phrases_in_text(text, phrase_mapping):
    """
    Thay thế nhiều cụm từ trong văn bản theo một bảng ánh xạ.

    :param text: Văn bản gốc
    :param phrase_mapping: Dict chứa các cụm từ gốc và bản thay thế
    :return: Văn bản sau khi thay thế
    """

    error_translation_map = {
        "Error occurred while uploading media": "미디어 업로드 중 오류가 발생했습니다.",
        "Error validating access token: The session has been invalidated because the user changed their password or Facebook has changed the session for security reasons.": "액세스 토큰 검증 오류: 사용자가 비밀번호를 변경했거나 Facebook이 보안상의 이유로 세션을 변경하여 세션이 무효화되었습니다.",
        "Application request limit reached": "애플리케이션 요청 한도에 도달했습니다.",
        "Can't get page token": "페이지 토큰을 가져올 수 없습니다.",
        "SEND POST VIDEO - UPLOAD CHUNK": "영상 게시 - 청크 업로드",
        '<HttpError 400 when requesting None returned "The user has exceeded the number of videos they may upload."': "<HttpError 400> 사용자 업로드 가능한 동영상 수를 초과했습니다.",
        "Unsupported post type. The post has too little or too many attachments to qualify as a carousel": "지원되지 않는 게시물 유형입니다. 캐러셀로 등록되기에는 첨부 파일 수가 너무 적거나 너무 많습니다.",
        "An unknown error occurred": "알 수 없는 오류가 발생했습니다.",
        "User access is restricted": "사용자 접근이 제한되어 있습니다.",
        "error_subcode": "오류 하위 코드",
        "Object with ID '18122979379443354' does not exist, cannot be loaded due to missing permissions, or does not support this operation": "ID '18122979379443354' 객체는 존재하지 않거나, 권한 부족으로 로드할 수 없거나, 이 작업을 지원하지 않습니다.",
        "Server responded with Response code 502 (Bad Gateway)": "서버가 502 오류 코드(Bad Gateway)로 응답했습니다.",
        "Access token invalid": "액세스 토큰이 유효하지 않습니다.",
        "The parameter video_url is required": "video_url 파라미터는 필수입니다.",
        "You are not permitted to perform this action.": "이 작업을 수행할 권한이 없습니다.",
        "I scream. You scream. We all scream... for us to fix this page. We'll stop making jokes and get things up and running soon.": "당신도, 나도, 우리 모두... 이 페이지를 고치기 위해 소리 지르고 있어요. 농담은 그만하고 곧 정상화하겠습니다.",
        "This page is down": "이 페이지는 현재 작동하지 않습니다.",
    }

    pattern = re.compile("|".join(map(re.escape, phrase_mapping.keys())))

    def replace_match(match):
        return phrase_mapping[match.group(0)]

    return pattern.sub(replace_match, text)


def replace_phrases_in_text(text):
    """
    Thay thế các thông báo lỗi tiếng Anh trong văn bản bằng bản dịch tiếng Hàn tương ứng.

    :param text: Văn bản đầu vào chứa thông báo lỗi tiếng Anh
    :return: Văn bản đã thay thế bằng tiếng Hàn
    """
    phrase_mapping = {
        "Error occurred while uploading media": "미디어 업로드 중 오류가 발생했습니다.",
        "Error validating access token: The session has been invalidated because the user changed their password or Facebook has changed the session for security reasons.": "액세스 토큰 검증 오류: 사용자가 비밀번호를 변경했거나 Facebook이 보안상의 이유로 세션을 변경하여 세션이 무효화되었습니다.",
        "Application request limit reached": "애플리케이션 요청 한도에 도달했습니다.",
        "Can't get page token": "페이지 토큰을 가져올 수 없습니다.",
        "SEND POST VIDEO - UPLOAD CHUNK": "영상 게시 - 청크 업로드",
        '<HttpError 400 when requesting None returned "The user has exceeded the number of videos they may upload."': "<HttpError 400> 사용자 업로드 가능한 동영상 수를 초과했습니다.",
        "Unsupported post type. The post has too little or too many attachments to qualify as a carousel": "지원되지 않는 게시물 유형입니다. 캐러셀로 등록되기에는 첨부 파일 수가 너무 적거나 너무 많습니다.",
        "An unknown error occurred": "알 수 없는 오류가 발생했습니다.",
        "User access is restricted": "사용자 접근이 제한되어 있습니다.",
        "error_subcode": "오류 하위 코드",
        "Object with ID '18122979379443354' does not exist, cannot be loaded due to missing permissions, or does not support this operation": "ID '18122979379443354' 객체는 존재하지 않거나, 권한 부족으로 로드할 수 없거나, 이 작업을 지원하지 않습니다.",
        "Server responded with Response code 502 (Bad Gateway)": "서버가 502 오류 코드(Bad Gateway)로 응답했습니다.",
        "Access token invalid": "액세스 토큰이 유효하지 않습니다.",
        "The parameter video_url is required": "video_url 파라미터는 필수입니다.",
        "You are not permitted to perform this action.": "이 작업을 수행할 권한이 없습니다.",
        "I scream. You scream. We all scream... for us to fix this page. We'll stop making jokes and get things up and running soon.": "당신도, 나도, 우리 모두... 이 페이지를 고치기 위해 소리 지르고 있어요. 농담은 그만하고 곧 정상화하겠습니다.",
        "This page is down": "이 페이지는 현재 작동하지 않습니다.",
    }

    pattern = re.compile("|".join(map(re.escape, phrase_mapping.keys())))
    return pattern.sub(lambda m: phrase_mapping[m.group(0)], text)


def allowed_image(filename):
    allowed_extens = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extens


def split_line_with_url(line):
    # Tìm URL
    url_pattern = re.compile(r"(https?://\S+)")
    match = url_pattern.search(line)

    if not match:
        return [line]  # Không có URL → trả về nguyên dòng

    start, end = match.span()
    url = match.group()

    before = line[:start].strip()
    after = line[end:].strip()

    result = []
    if before:
        result.append(before)
    result.append(url)
    if after:
        result.append(after)

    return result


def split_toktak_url(line):
    # Mẫu regex để khớp các URL có dạng s.toktak.ai, link.coupang.com, s.click
    pattern = re.compile(r"(https://(?:s\.toktak\.ai|link\.coupang\.com|s\.click)\S*)")
    match = pattern.search(line)

    if not match:
        return [line]

    start, end = match.span()
    url = match.group()

    before = line[:start].strip()
    after = line[end:].strip()

    result = []
    if before:
        result.append(before)
    result.append(url)
    if after:
        result.append(after)

    return result


def format_price_show(price_text):
    try:
        if price_text:
            price_show_no_comma = price_text.replace(",", "")
            if not price_show_no_comma.isdigit():
                return price_text

            if len(price_show_no_comma) > 2:
                price_text = price_show_no_comma[:2] + "," + price_show_no_comma[2:]

            if not price_text.startswith("₩"):
                price_text = f"₩{price_text}"
    except Exception as e:
        return ""

    return price_text


def convert_video_path(path: str, domain: str):
    try:
        path = path or ""
        return path.replace("static/", f"{domain}/").replace(
            "/mnt/", f"{domain}/voice/"
        )
    except Exception as e:
        logger.error(f"[convert_video_path] Failed for path: {path} — Error: {e}")
        return ""


def get_video_path_or_url(post_json, current_domain):
    video_url = post_json.get("video_url", "")
    video_path = post_json.get("video_path", "")
    # Nếu video_url chứa https://toktaks3 thì ưu tiên trả về video_url
    if "https://toktaks3" in video_url:
        return video_url
    # Nếu không thì convert video_path
    return convert_video_path(video_path, current_domain)

def insert_hashtags_to_string(tag_string, index=6):
    new_hashtags = ["#톡탁", "#toktak"]
    tag_list = tag_string.strip().split()
    tag_list = tag_list[:index] + new_hashtags + tag_list[index:]
    return " ".join(tag_list)


def change_advance_hashtags(original_str, new_hashtag, max_count=10):
    original_list = original_str.strip().split()

    cleaned_new = [f"#{tag.lstrip('#')}" for tag in new_hashtag]

    combined = cleaned_new + original_list

    trimmed = combined[:max_count]
    return " ".join(trimmed)


def mask_string_with_x(name, created_at):
    masked_name = ""
    if name:
        masked_name = "X" * len(name)
    return f"{created_at} {masked_name}님이 초대를 수락했어요"

def generate_order_id(tag="order"):
    raw_id = f"{tag}_{uuid.uuid4().hex[:16]}"
    return re.sub(r"[^a-zA-Z0-9_-]", "", raw_id)


def format_price_won(price):
    return "{:,.0f}₩".format(price)


def cutting_text_when_exceed_450(text):
    """
    Cắt văn bản khi vượt quá 450 ký tự.
    Sử dụng hàm split_text_by_words để tách văn bản.

    :param text: Văn bản cần cắt
    :return: Danh sách các đoạn văn bản
    """
    return split_text_by_words(text, max_length=450)


def split_text_by_words(text, max_length=450):
    """
    Tách văn bản thành các đoạn, mỗi đoạn tối đa max_length ký tự.
    Đảm bảo không cắt giữa từ, chỉ cắt tại khoảng trắng giữa các từ.

    :param text: Văn bản cần tách
    :param max_length: Độ dài tối đa của mỗi đoạn (mặc định 450)
    :return: Danh sách các đoạn văn bản
    """
    if not text:
        return []

    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word) + (1 if current_chunk else 0)

        if current_length + word_length > max_length:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0

            if len(word) > max_length:
                chunks.append(word[:max_length])
                word = word[max_length:]
                while word:
                    chunks.append(word[:max_length])
                    word = word[max_length:]
            else:
                current_chunk = [word]
                current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += word_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def parse_date(date_str):
    """
    Parse date string to datetime object.
    Hỗ trợ nhiều format ngày tháng khác nhau.

    :param date_str: Chuỗi ngày tháng cần parse
    :return: datetime object hoặc None nếu không parse được
    """
    if not date_str:
        return None

    # Danh sách các format có thể có
    date_formats = [
        "%Y-%m-%d %H:%M:%S",  # 2024-03-21 14:30:00
        "%Y-%m-%d %H:%M",  # 2024-03-21 14:30
        "%Y-%m-%d",  # 2024-03-21
        "%d/%m/%Y %H:%M:%S",  # 21/03/2024 14:30:00
        "%d/%m/%Y %H:%M",  # 21/03/2024 14:30
        "%d/%m/%Y",  # 21/03/2024
        "%m/%d/%Y %H:%M:%S",  # 03/21/2024 14:30:00
        "%m/%d/%Y %H:%M",  # 03/21/2024 14:30
        "%m/%d/%Y",  # 03/21/2024
        "%Y/%m/%d %H:%M:%S",  # 2024/03/21 14:30:00
        "%Y/%m/%d %H:%M",  # 2024/03/21 14:30
        "%Y/%m/%d",  # 2024/03/21
        "%Y-%m-%dT%H:%M:%SZ",  # 2024-03-21T14:30:00Z
        "%Y-%m-%dT%H:%M:%S%z",  # 2024-03-21T14:30:00+0900
        "%Y-%m-%dT%H:%M:%S.%f%z",  # 2024-03-21T14:30:00.123+0900
    ]

    # Thử parse với từng format
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            continue

    # Nếu không parse được với format nào, thử parse với dateutil
    try:
        from dateutil import parser

        return parser.parse(date_str)
    except:
        logger.error(f"Could not parse date string: {date_str}")
        return None
