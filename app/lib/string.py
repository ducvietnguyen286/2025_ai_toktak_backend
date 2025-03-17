import json
import re

import hashlib
import base64


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
    base_url = "https://admin.lang.canvasee.com/img/level/"
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


def should_replace_shortlink(url):
    excluded_domains = ["https://link.coupang.com", "https://s.click.aliexpress.com"]

    return not any(url.startswith(domain) for domain in excluded_domains)
