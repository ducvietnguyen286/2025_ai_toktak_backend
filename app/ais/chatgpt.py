import json
from openai import OpenAI
from app.services.request_log import RequestLogService
import os

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def call_chatgpt_create_caption(images=[], data={}, post_id=0):

    prompt = """업로드된 이미지들을 참고하여, 제품의 다음 세부 정보를 반영한 동영상에 어울리는 **제목(title)**과 **CAPTION_COUNT개의 캡션 목록**을 만들어주세요.
제품 관련 정보:
- 제품명: {name}
- 가격: {price}
- 제품 설명: {description}
- 판매처: {store_name}
- 제품 링크: {base_url}

조건:
- 제목은 동영상의 핵심 메시지를 전달할 수 있도록 강렬하고 매력적으로 작성해 주세요.
- 캡션은 동영상 내에서 30초 동안 자연스럽게 진행될 수 있도록 흐름을 고려하여 작성해 주세요.
- TikTok과 Shorts 스타일에 맞게 경쾌하고 흥미로운 문구를 사용하고, 시청자들의 관심을 끌 수 있도록 해 주세요.
- 캡션에는 적절한 해시태그를 추가해 주세요.
- 반드시 결과는 순수한 문자열로만 반환되어야 하며, Markdown 형식은 사용하지 말아 주세요.
- 제목과 캡션의 내용은 반드시 한국어로 작성되어야 합니다.
- **생성할 캡션의 수는 제가 제공한 숫자(CAPTION_COUNT)와 정확히 일치해야 합니다.**
"""
    prompt = replace_prompt_with_data(prompt, data)

    prompt = prompt.replace("CAPTION_COUNT", str(len(images)))

    content = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": image}})

    response_schema = {
        "name": "response_schema",
        "schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the response.",
                        },
                        "caption": {
                            "type": "array",
                            "description": "A list of captions associated with the response.",
                            "items": {
                                "type": "string",
                                "description": "A caption string.",
                            },
                        },
                        "hashtag": {
                            "type": "string",
                            "description": "A hashtag associated with the response.",
                        },
                    },
                    "required": ["title", "caption", "hashtag"],
                    "additionalProperties": False,
                }
            },
            "required": ["response"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    return call_chatgpt(content, response_schema, post_id)


def call_chatgpt_create_blog(images=[], data={}, post_id=0):
    prompt = """업로드된 이미지들을 참고하여, 제품의 다음 세부 정보를 반영한 **블로그 게시글**을 작성해 주세요.
제품 관련 정보:
- 제품명: {name}
- 가격: {price}
- 제품 설명: {description}
- 판매처: {store_name}
- 제품 링크: {base_url}

조건:
- 게시글은 약 1200자 정도로 작성해 주세요.
- 제품에 대한 자세한 설명, 장점, 사용 방법 등을 포함하여 독자가 관심을 가질 수 있도록 친근하고 설득력 있게 작성해 주세요.
- 블로그 게시글은 **HTML 형식**으로 작성해 주세요.
- 제품의 이미지는 업로드된 이미지에서 선택하여 적절한 위치에 삽입해 주세요.
- 각 이미지의 `src`는 `IMAGE_URL_index` 형태로 작성되어야 하며, `index`는 각 이미지의 인덱스 번호로 대체되어야 합니다.
- 게시글 내용과 함께, 본문 내용을 요약한 **요약문**도 생성해 주세요.
- 게시글의 내용은 반드시 한국어로 작성되어야 하며, 결과는 순수한 문자열로만 반환되어야 합니다.
"""
    prompt = replace_prompt_with_data(prompt, data)

    content = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": image}})

    response_schema = {
        "name": "response_schema",
        "schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the response.",
                        },
                        "summarize": {
                            "type": "string",
                            "description": "A summary or brief overview of the content.",
                        },
                        "content": {
                            "type": "string",
                            "description": "The main content of the response.",
                        },
                    },
                    "required": ["title", "summarize", "content"],
                    "additionalProperties": False,
                }
            },
            "required": ["response"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    return call_chatgpt(content, response_schema, post_id)


def call_chatgpt_create_social(images=[], data={}, post_id=0):
    prompt = """[역할]
당신은 20~30대 커뮤니티에서 유행하는 언어를 활용하는 바이럴 마케터입니다. 제품을 직접 설명하지 않고 자연스럽게 관심을 유도하는 방식으로 SNS 콘텐츠를 생성하세요. 특히 "DC인사이드" 커뮤니티의 말투를 반영하여 작성하세요.

[입력 정보]

제품명: {name}
가격: {price}
제품 설명: {description}
판매처: {store_name}
제품 링크: {base_url}
이미지 개수: {image_count}
[요구 사항]

SNS 게시글 작성
Facebook: 사람들이 관심을 가지게 하고, 댓글과 공유를 유도하는 전체 게시글을 작성 (최소 160자).
Instagram: 짧고 강렬한 메시지와 해시태그를 포함한 전체 게시글을 작성 (최소 160자).
이미지별 캡션 작성
첫 번째 이미지: 제품을 직접 언급하지 않고, 궁금증을 유발하는 한 줄짜리 바이럴 문구 작성.
두 번째부터 {image_count}번째 이미지:
유행하는 커뮤니티 말투를 활용하여, 가상의 상황을 설정한 후 제품의 매력을 자연스럽게 연결하는 트렌디한 내용을 작성.
직설적인 광고 문구를 배제하고, 구매 욕구를 자극하는 공감형 콘텐츠로 구성.
해시태그:
각 소셜 미디어 게시글과 이미지 캡션에 SNS에서 유행하는 해시태그를 적절히 추가.
[출력 형식]

전체 게시글 내용: Facebook 및 Instagram용 게시글을 각각 별도로 작성 (각각 순수한 텍스트로 반환).
이미지별 캡션:
첫 번째 이미지: 호기심을 유발하는 한 줄짜리 바이럴 문구.
두 번째부터 {image_count}번째 이미지: 가상의 상황을 바탕으로 한 바이럴 스타일의 설명.
결과는 순수한 텍스트로만 반환 (코드나 별도의 포맷 없음).
[예시 출력]

■ Social Network 게시글:
"요즘 이거 없으면 허전하다! 친구들이 다 사용한다고 하는 꿀템, 나도 써보고 완전 반했어. 자세한 정보는 여기에서 확인해봐~ {base_url} (Only post. No hashtag)

■ Hashtags:
#핫템 #요즘대세 #추천템"

■ 이미지별 캡션:
[첫 번째 이미지 - 바이럴 문구]:
"이거 없으면 다리 길이 -5cm 효과임"

[두 번째 이미지 - 바이럴 설명]:
"친구가 이거 쓰고 다니길래 뭔지 물어봤더니, 써보니까 ㄹㅇ 인정. 요즘 대세임 ㅇㅇ"

[세 번째 이미지 - 바이럴 설명]:
"처음에는 그냥 호기심으로 시작했는데, 한 번 써보고 나니 인생템 확정"

[네 번째 이미지 - 바이럴 설명]:
"DC인사이드 갤러리에서도 벌써 입소문난 꿀템, 사놓고 후회 없는 선택!"

[다섯 번째 이미지 - 바이럴 설명]:
"나만 알고 싶었던 비밀템, 이젠 모두가 알아야 할 꿀조합…"

[노트]

전체 게시글과 이미지 캡션은 별개로 작성되어야 합니다.
제품 직접 설명을 피하고, 자연스러운 스토리텔링과 공감을 유도하는 내용으로 작성하세요.
20~30대 커뮤니티에서 유행하는 언어와 스타일을 적극 활용하세요."""

    data["image_count"] = len(images)

    prompt = replace_prompt_with_data(prompt, data)

    content = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": image}})

    response_schema = {
        "name": "response_schema",
        "schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "object",
                    "properties": {
                        "post": {
                            "type": "string",
                            "description": "The content of the post.",
                        },
                        "captions": {
                            "type": "array",
                            "description": "A list of captions associated with the response.",
                            "items": {
                                "type": "string",
                                "description": "A caption string.",
                            },
                        },
                        "hashtag": {
                            "type": "string",
                            "description": "The associated hashtag.",
                        },
                    },
                    "required": ["post", "captions", "hashtag"],
                    "additionalProperties": False,
                }
            },
            "required": ["response"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    return call_chatgpt(content, response_schema, post_id)


def replace_prompt_with_data(prompt, data):
    prompt = prompt.format(**data)
    return prompt


def call_chatgpt(content, response_schema, post_id=0):
    client = OpenAI(api_key=chatgpt_api_key)
    model = "gpt-4o-mini"

    request_log = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "response_format": {
                "type": "json_schema",
                "json_schema": response_schema,
            },
            "max_tokens": 3000,
            "temperature": 0.9,
        }
    )

    try:
        response = client.chat.completions.create(
            model=model,
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
            max_tokens=5000,
            temperature=0.9,
        )
        response_log = json.dumps(response.to_dict())

        if response:
            content = response.choices[0].message.content or None
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            prompt_cache_tokens = usage.prompt_tokens_details.cached_tokens
            prompt_audio_tokens = usage.prompt_tokens_details.audio_tokens
            completion_reasoning_tokens = (
                usage.completion_tokens_details.reasoning_tokens
            )
            completion_audio_tokens = usage.completion_tokens_details.audio_tokens
            completion_accepted_prediction_tokens = (
                usage.completion_tokens_details.accepted_prediction_tokens
            )
            completion_rejected_prediction_tokens = (
                usage.completion_tokens_details.rejected_prediction_tokens
            )
            total_tokens = usage.total_tokens

            status = 1
            if not content:
                status = 0
            RequestLogService.create_request_log(
                post_id=post_id,
                ai_type="chatgpt",
                request=request_log,
                response=response_log,
                prompt_tokens=prompt_tokens,
                prompt_cache_tokens=prompt_cache_tokens,
                prompt_audio_tokens=prompt_audio_tokens,
                completion_tokens=completion_tokens,
                completion_reasoning_tokens=completion_reasoning_tokens,
                completion_audio_tokens=completion_audio_tokens,
                completion_accepted_prediction_tokens=completion_accepted_prediction_tokens,
                completion_rejected_prediction_tokens=completion_rejected_prediction_tokens,
                total_tokens=total_tokens,
                status=status,
            )
            return content
        return None
    except Exception as e:
        response_log = json.dumps({"error": str(e)})
        RequestLogService.create_request_log(
            post_id=post_id,
            ai_type="chatgpt",
            request=request_log,
            response=response_log,
            status=0,
        )
        return None
