import json
import re


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
