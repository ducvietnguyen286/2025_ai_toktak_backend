from openai import OpenAI
import os

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""
chatgpt_assistant_id = os.environ.get("CHATGPT_ASSISTANT_ID") or ""

client = OpenAI(api_key=chatgpt_api_key)


def call_chatgpt_create_caption(images=[]):
    client = OpenAI(api_key=chatgpt_api_key)

    prompt = "업로드된 이미지들을 참고하여, 해당 이미지들을 활용해 제작된 동영상에 어울리는 캡션 4개를 만들어주세요. 이 캡션들은 광고 및 시청자 유입을 목적으로 하며, TikTok과 Shorts 스타일에 맞게 경쾌하고 매력적인 문구로 작성되어야 합니다. 각 캡션은 동영상 상에서 7.5초 길이로 표시될 수 있도록 적절한 분량으로 작성되어야 합니다. 각 이미지가 전달하는 감성과 특징을 잘 살려, 독창적이고 창의적인 표현을 사용해 주세요. 반드시 캡션은 순수한 문자열로만 반환되어야 하며, Markdown 형식은 사용하지 말아 주세요. 또한, 캡션의 내용은 반드시 한국어로 작성되어야 합니다."

    content = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": image}})

    response_schema = {
        "name": "response_schema",
        "schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "array",
                    "description": "An array of response items.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the response item.",
                            },
                            "caption": {
                                "type": "string",
                                "description": "A caption or description for the response item.",
                            },
                        },
                        "required": ["title", "caption"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["response"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": content,
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": response_schema,
        },
        max_tokens=1200,
        temperature=0.7,
    )
    if response:
        return response.choices[0].message.content
    return None
