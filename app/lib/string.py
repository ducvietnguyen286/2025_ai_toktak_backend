import json
import random
import re

import hashlib
import base64
import string


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
    excluded_domains = ["https://link.coupang.com", "https://s.click.aliexpress.com"]

    return not any(url.startswith(domain) for domain in excluded_domains)


def update_ads_content(url, content):
    if "https://link.coupang.com/" in url:
        content = content.replace("<h2>ADS_CONTENT_TOKTAK</h2>", "<h2>이 포스팅은 쿠팡 파트너스 수익 활동의 일환으로, 이에 따른 일정액의 수수료를 제공 받습니다.</h2>")
        # content = f"<h2>이 포스팅은 쿠팡 파트너스 수익 활동의 일환으로, 이에 따른 일정액의 수수료를 제공 받습니다.</h2>\n\n\n\n{content}"
    elif "https://s.click.aliexpress.com" in url:
        content = content.replace("<h2>ADS_CONTENT_TOKTAK</h2>", "<h2>이 포스팅은 알리 어필리에이트 수익 활동의 일환으로, 이에 따른 일정액의 수수료를 제공 받습니다.</h2>")
        # content = f"<h2>이 포스팅은 알리 어필리에이트 수익 활동의 일환으로, 이에 따른 일정액의 수수료를 제공 받습니다.</h2>\n\n\n\n{content}"
    else :
        content = content.replace("<h2>ADS_CONTENT_TOKTAK</h2>", "")
    return content


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
        "I scream. You scream. We all scream... for us to fix this page. We’ll stop making jokes and get things up and running soon.": "당신도, 나도, 우리 모두... 이 페이지를 고치기 위해 소리 지르고 있어요. 농담은 그만하고 곧 정상화하겠습니다.",
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
        "I scream. You scream. We all scream... for us to fix this page. We’ll stop making jokes and get things up and running soon.": "당신도, 나도, 우리 모두... 이 페이지를 고치기 위해 소리 지르고 있어요. 농담은 그만하고 곧 정상화하겠습니다.",
        "This page is down": "이 페이지는 현재 작동하지 않습니다.",
    }

    pattern = re.compile("|".join(map(re.escape, phrase_mapping.keys())))
    return pattern.sub(lambda m: phrase_mapping[m.group(0)], text)
