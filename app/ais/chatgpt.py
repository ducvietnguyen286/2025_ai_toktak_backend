from openai import OpenAI
import os

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def call_chatgpt_create_caption(images=[]):
    client = OpenAI(api_key=chatgpt_api_key)

    prompt = """업로드된 이미지들을 참고하여, 해당 이미지들을 활용해 제작된 동영상에 어울리는 캡션 4개를 만들어주세요. 이 캡션들은 광고 및 시청자 유입을 목적으로 하며, TikTok과 Shorts 스타일에 맞게 경쾌하고 매력적인 문구로 작성되어야 합니다. 각 캡션은 동영상 상에서 7.5초 길이로 표시될 수 있도록 적절한 분량으로 작성되어야 합니다. 각 이미지가 전달하는 감성과 특징을 잘 살려, 독창적이고 창의적인 표현을 사용해 주세요. 반드시 캡션은 순수한 문자열로만 반환되어야 하며, Markdown 형식은 사용하지 말아 주세요. 또한, 캡션의 내용은 반드시 한국어로 작성되어야 합니다.

추가로, 이 이미지와 관련된 **소셜 미디어 콘텐츠**도 작성해 주세요. 다음 플랫폼에 맞는 매력적인 콘텐츠를 작성해 주세요:
- **Facebook**: 사람들의 관심을 끌고 참여를 유도하는 글 (최소 150자 이상)
- **Instagram**: 짧고 강렬한 메시지, 해시태그 포함하여 게시할 수 있는 글 (최소 150자 이상)

마지막으로, 해당 제품에 대한 **블로그 게시글**을 작성해 주세요. 길이는 약 1200자 정도로, 제품에 대한 자세한 설명과 장점, 사용 방법 등을 포함하여 독자가 관심을 가질 수 있도록 친근하고 설득력 있게 작성해 주세요. 블로그 게시글은 **HTML 형식**으로 작성해 주세요. 제품의 이미지는 **업로드된 이미지**에서 선택하여 적절한 위치에 삽입하고, 제품을 강조할 수 있도록 `img` 태그를 사용하여 이미지를 삽입해 주세요. 각 이미지의 `src`는 `IMAGE_URL_{index}` 형태로 작성되어야 하며, `{index}`는 각 이미지의 인덱스 번호로 바뀌어야 합니다.
"""

    content = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": image}})

    response_schema = {
        "name": "blog_response",
        "schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "object",
                    "properties": {
                        "captions": {
                            "type": "array",
                            "description": "A collection of captions for the blog.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "The title of the caption.",
                                    },
                                    "caption": {
                                        "type": "string",
                                        "description": "Each individual caption text.",
                                    },
                                },
                                "required": ["title", "caption"],
                                "additionalProperties": False,
                            },
                        },
                        "social_content": {
                            "type": "string",
                            "description": "The content of the social post.",
                        },
                        "blog_content": {
                            "type": "string",
                            "description": "Additional content for the blog.",
                        },
                    },
                    "required": ["captions", "social_content", "blog_content"],
                    "additionalProperties": False,
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
        max_tokens=3000,
        temperature=0.9,
    )
    if response:
        return response.choices[0].message.content
    return None
