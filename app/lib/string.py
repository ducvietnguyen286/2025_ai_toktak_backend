import json
import kss


def is_json(data):
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False


def split_text_by_sentences(text, num_captions):
    sentences = kss.split_sentences(text)

    if len(sentences) < num_captions:
        sentences += [""] * (num_captions - len(sentences))
        return sentences[:num_captions]

    group_size = len(sentences) / num_captions
    captions = []
    for i in range(num_captions):
        start_index = int(round(i * group_size))
        end_index = int(round((i + 1) * group_size))
        caption = " ".join(sentences[start_index:end_index])
        captions.append(caption)
    return captions
