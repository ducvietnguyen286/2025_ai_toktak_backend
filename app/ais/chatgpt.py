import json
from openai import OpenAI
from app.services.request_log import RequestLogService
import os

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def call_chatgpt_create_caption(images=[], data={}, post_id=0):

    prompt = """📌 요청 사항: 업로드된 이미지를 참고하여 제품을 홍보하는 숏폼(Shorts, TikTok) 스타일의 영상 콘텐츠를 제작할 수 있도록 아래 요소들을 생성해 주세요.

제목 (Title): 짧고 강렬하며 제품의 핵심 가치를 강조하는 문구
클릭을 유도하는 흥미로운 표현 포함

캡션 목록 (CAPTION_COUNT개): 각 캡션은 gTTS를 통해 생성된 오디오가 약 5초 동안 재생될 수 있도록 구성
임팩트 있는 문장으로 시청자의 관심을 끌어야 함
마지막에는 행동 유도를 위한 Call-to-Action(CTA) 포함

해시태그 목록: 제품 및 타겟 고객층에 맞는 인기 해시태그 선정
개별 해시태그로 제공하며, 캡션과 분리할 것

DC인사이드 스타일 게시글 (200자 이내): 유머러스하고 도발적인 문체 사용
커뮤니티 특유의 밈(meme)과 유행어 활용
댓글 반응을 유도할 수 있도록 구성

📌 제품 정보: 제품명: {name}
가격: {price}
제품 설명: {description}
판매처: {store_name}
제품 링크: {base_url}
제품 소개: {text}

📌 생성 조건: ✅ 제목: 짧고 강렬하게! (예: “이걸 안 사면 후회각!”)
영상 스타일에 맞는 톤 & 텐션 유지

✅ 캡션: 총 CAPTION_COUNT개의 문장을 gTTS 오디오가 각각 5초 분량으로 재생될 수 있도록 작성
트렌디한 표현, 감탄사, 감성적인 요소 포함
마지막에 강력한 CTA 포함 (예: “지금 구매하러 가기!”)

✅ 해시태그: 제품군과 관련된 해시태그 선정
캡션과 분리된 개별 목록으로 제공

✅ DC인사이드 스타일 게시글: 250자 이내, 핵심 메시지가 바로 전달되도록 작성
강한 어조, 밈(meme) 요소, 유머 코드 반영
마치 커뮤니티에서 실제로 작성된 글처럼 자연스럽게 구성

📌 출력 형식: ❌ Markdown 사용 금지 (순수 텍스트만 반환)
❌ 기타 특수 문자 사용 금지

이 프롬프트를 활용하면 더욱 강렬하고 효과적인 SNS 콘텐츠를 제작할 수 있습니다! 🚀
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
                        "content": {
                            "type": "string",
                            "description": "The content of the response.",
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
                            "description": "A hashtag associated with the response.",
                        },
                    },
                    "required": ["title", "content", "captions", "hashtag"],
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
- 제품 소개: {text}

조건:
- 게시글은 약 1200자 정도로 작성해 주세요.
- 제품에 대한 자세한 설명, 장점, 사용 방법 등을 포함하여 독자가 관심을 가질 수 있도록 친근하고 설득력 있게 작성해 주세요.
- 블로그 게시글은 **HTML 형식**으로 작성해 주세요.
- 게시글 상단에 사용자의 관심을 끌 수 있는 **매력적인 제목**을 작성해 주세요.
- 제품의 이미지는 업로드된 이미지에서 선택하여 적절한 위치에 삽입해 주세요.
- 각 이미지의 `src`는 `IMAGE_URL_index` 형태로 작성되어야 하며, `index`는 `0`부터 COUNT_IMAGE 까지의 숫자로 대체되어야 합니다.
- 게시글 내용과 함께, 본문 내용을 요약한 **요약문**도 생성해 주세요.
- **요약문은 300~350자 이내로 작성해 주세요. (참고: 글자 수 제한은 요약문에만 적용되며, 본문은 약 1200자 가이드라인에 따릅니다.)**
- 요약의 내용은 반드시 한국어로 작성되어야 하며, 결과는 순수한 문자열로만 반환되어야 합니다
"""
    prompt = prompt.replace("COUNT_IMAGE", str(len(images)))

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
제품 소개: {text}
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
"요즘 이거 없으면 허전하다! 친구들이 다 사용한다고 하는 꿀템, 나도 써보고 완전 반했어. 자세한 정보는 여기에서 확인해봐~ {base_url}"

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
