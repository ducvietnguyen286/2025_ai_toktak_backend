import json
from openai import OpenAI
from app.services.request_log import RequestLogService
import os

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def call_chatgpt_create_caption(images=[], data={}):

    prompt = """업로드된 이미지들을 참고하여, 제품의 다음 세부 정보를 반영한 동영상에 어울리는 **제목(title)**과 **캡션(caption)**을 만들어주세요.
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
"""
    prompt = replace_prompt_with_data(prompt, data)

    print("prompt", prompt)

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
                            "type": "string",
                            "description": "A caption or description related to the response.",
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

    return call_chatgpt(content, response_schema)


def call_chatgpt_create_blog(images=[], data={}):
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

    return call_chatgpt(content, response_schema)


def call_chatgpt_create_social(images=[], data={}):
    prompt = """업로드된 이미지들을 참고하여, 제품의 다음 세부 정보를 반영한 **소셜 미디어 콘텐츠**를 작성해 주세요.
제품 관련 정보:
- 제품명: {name}
- 가격: {price}
- 제품 설명: {description}
- 판매처: {store_name}
- 제품 링크: {base_url}

조건:
- **Facebook**: 사람들의 관심을 끌고 참여를 유도하는 글을 작성해 주세요 (최소 300자 이상).
- **Instagram**: 짧고 강렬한 메시지와 해시태그를 포함한 글을 작성해 주세요 (최소 300자 이상).
- 각 소셜 미디어 게시글에 적절한 해시태그를 추가해 주세요.
- 작성된 내용은 반드시 한국어로 작성되어야 하며, 결과는 순수한 문자열로만 반환되어야 합니다.
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
                        "post": {
                            "type": "string",
                            "description": "The content of the post.",
                        },
                        "hashtag": {
                            "type": "string",
                            "description": "The associated hashtag.",
                        },
                    },
                    "required": ["post", "hashtag"],
                    "additionalProperties": False,
                }
            },
            "required": ["response"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    return call_chatgpt(content, response_schema)


def replace_prompt_with_data(prompt, data):
    prompt = prompt.format(**data)
    return prompt


def call_chatgpt(content, response_schema):
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
            ai_type="chatgpt", request=request_log, response=response_log, status=0
        )
        return None
