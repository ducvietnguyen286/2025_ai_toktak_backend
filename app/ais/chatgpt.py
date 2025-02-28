import json
from openai import OpenAI
from app.services.request_log import RequestLogService
import os

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def call_chatgpt_create_caption(images=[], data={}, post_id=0):

    prompt = """업로드된 이미지를 참고하여 제품을 홍보하는 숏폼(Shorts, TikTok) 스타일의 영상 콘텐츠를 제작하도록 지원해 드립니다.

[역할]
당신은 20~30대 커뮤니티에서 유행하는 언어를 활용하는 애플의 바이럴 마케터입니다. 상품을 홍보하는 영상을 만드는 작업을 진행할 예정입니다. FOMO, 사회적 증가, 공감과 감성 자극, 첫 3초의 법칙, 자이가르닉효과 등 적절한 심리학 기법을 상황에 맞게 사용하여 스크립트를 작성하세요. 어떤 기법이 적절한지 고려한 후, 이를 바탕으로 정확한 실행을 계획합니다.

[입력 정보]
- 제품명: {name}
- 가격: {price}
- 제품 설명: {description}
- 판매처: {store_name}
- 제품 링크: {base_url}
- 제품 소개: {text}

- 순수 텍스트 형식으로 반환
- 특수 문자 및 Markdown 사용 금지

[생성 조건]
- **Comment**: 
  - 짧고, 강렬하게, 영상 스타일에 맞는 톤 & 텐션 유지 
  - 클릭을 유도하는 흥미로운 표현 포함
  - 줄바꿈 후 "구매링크👉: {base_url}" 이 문장 무조건 표시 

- **Title**: 
  - Comment의 짧은 버전. 더 짧게 한줄로 요약.
  - 줄바꿈 후 "구매링크👉: {base_url}" 이 문장 무조건 표시 

- **Hashtag list**: 
  - 제품군과 관련된 해시태그 선정, 캡션과 분리된 개별 목록으로 제공
  - 제품 및 타겟 고객층에 맞는 인기 해시태그 선정
  - 개별 해시태그로 제공하며, 캡션과 분리하여 작성합니다.

- **Caption**: 
  - 총 CAPTION_COUNT개의 문장을 각각 5초 분량으로 재생 가능하게 작성
  - 각 caption은 gTTS를 통해 생성되는 오디오가 약 5초 동안 재생될 수 있도록 구성
  - 스토리텔링 형식으로 상품에 대해서 소개하는 caption 작성
  - 반드시 "[예시 출력]의 ##Caption"을 참고해서 작성할 것.
  - 한 문장을 끝까지 온전하게 작성할 것.
  - 유머 코드와 밈(meme) 반영
  - 커뮤니티 특유의 자연스러운 표현 사용
  - 트렌디한 문장으로 시청자의 관심을 끌고, 마지막에 행동 유도를 위한 Call-to-Action(CTA)을 포함

[요구 사항]
- **전체적인 형식**: 
  - FOMO, 사회적 증가 등의 심리학 기법을 상황에 맞게 활용하여 스크립트를 제작합니다. 
  - 각 요소가 어떻게 심리적 효과를 주는지 이해하고, 이를 어떻게 활용할 것인지 설명한 후 스크립트를 작성합니다.
  - 유머러스하고 도발적인 문체 사용 및 커뮤니티 특유의 밈(meme)과 유행어 활용
  - 댓글 반응을 유도할 수 있도록 구성합니다.

[예시 출력]
## title:
'지금 애엄마들 사이에서 난리라는 거...(줄 바꿈)링크에서 확인👉: {base_url}'

## content:
'한번 써보면 다시는 못돌아 간다는 맘카페 전설의 제품(줄 바꿈)링크에서 확인👉: {base_url}'

## Hashtag List:
'#패션스타그램 #운동복추천 #ootd #일상룩 #스포티룩 #여자옷 #스타일링 #쇼핑'

## Caption:
'안녕하세요! 오늘은 언더아머 여성 맨투맨을 소개해드릴게요.
이 맨투맨은 심플하면서도 세련된 디자인으로, 다양한 스타일에 매치하기 좋아요. 앞면에는 언더아머 로고가 깔끔하게 들어가 있어 브랜드의 아이덴티티를 잘 나타내고 있습니다.
폴리에스테르 65%, 면 29%, 엘라스틴 6% 혼방 소재로 제작되어 부드럽고 편안한 착용감을 제공해요. 또한, 내구성이 뛰어나 세탁 후에도 변형이 적어 오랫동안 함께할 수 있죠.
앞면의 언더아머 로고가 포인트로 들어가 있어 브랜드의 아이덴티티를 살려주며, 깔끔한 인상을 줍니다.
지금 바로 언더아머 여성 맨투맨으로 스타일과 편안함을 동시에 느껴보세요!
더 자세한 정보와 구매는 아래 링크를 확인해주세요.'
'안녕하세요! 오늘은 애플의 최신 노트북 맥북 프로 16 M4를 소개해드릴게요.
16인치 나노 텍스처 디스플레이는 눈부심을 최소화하여 어떤 환경에서도 선명한 화면을 제공해요. 카페나 야외에서도 편안하게 작업할 수 있습니다.
최신 M4 시리즈 칩을 탑재하여 이전 모델보다 최대 3.5배 향상된 성능을 자랑해요. 영상 편집, 그래픽 디자인 등 고사양 작업도 부드럽게 처리할 수 있어요.
새로운 썬더볼트 5 포트는 최대 120Gb/s의 전송 속도를 제공합니다. 대용량 파일 전송도 빠르게 완료되어 작업 효율이 높아집니다.
macOS Sequoia 15.1을 통해 AI 기반 도구와 향상된 시리를 만나보세요. 아이폰 미러링, 개인화된 공간 음향 등 다양한 기능이 작업과 일상을 더욱 편리하게 만들어줘요.
더 자세한 정보와 구매는 아래 링크를 확인해주세요.'
'안녕하세요! 오늘은 집에서 카페 감성을 느낄 수 있는 네스카페 돌체구스토 지니오 S를 소개해드릴게요.
간편한 터치로 원하는 커피를 손쉽게 추출할 수 있어요. 아침에 바쁠 때도 빠르게 한 잔 완성!
최대 15바의 고압 추출로 풍부한 아로마와 부드러운 크레마를 가진 커피를 즐겨보세요.
진한 커피가 필요할 땐 에스프레소 부스트 모드로 더욱 깊은 맛을 느껴보세요.
여름엔 시원한 아이스 커피, 겨울엔 따뜻한 라떼까지! 4단계 온도 조절로 사계절 내내 완벽한 커피 타임을 즐길 수 있어요.
1분 동안 사용하지 않으면 자동으로 전원이 꺼지는 에코 모드로 에너지 절약까지 챙겨보세요!
네스카페 돌체구스토 지니오 S와 함께라면 집에서도 카페 부럽지 않아요. 지금 바로 경험해보세요!'
'요즘 잠자리가 불편하다면? 매트리스 바꿔야 할 때!
에이스침대 하이브리드 테크 라임은 양면 사용 가능!
한쪽은 하드, 한쪽은 슈퍼 하드! 내 취향대로 선택하면 돼요.
허리를 탄탄하게 받쳐주는 이 느낌! 한 번 누우면 못 일어난다는 후기, 인정합니다.
흔들림 걱정 없이 꿀잠 가능! 같이 자는 사람이 뒤척여도 방해 없이 편안해요.
꿀잠 보장! 편안한 숙면을 원한다면, 지금 바로 확인해보세요.
더 자세한 정보와 구매는 아래 링크에서 확인하세요.'
'거울 볼 때마다 건조하고 푸석한 피부 때문에 고민인 사람 집중!
그럴 땐 화이트 트러플로 피부 재부팅! 이건 진. 짜. 달라요.
가벼운 사용감에 흡수력 갑! 끈적임 없이 보습은 꽉 잡아줘요.
7중 히알루론산이 피부 깊숙이 스며들어 피부 속부터 촉촉!
주름 걱정은 이제 그만! 펩타이드 성분으로 꾸준히 관리해 보세요
예민한 피부도 안심하고 쓸 수 있는 저자극 포뮬러, 비건 인증!
딱 2통만 꾸준히 사용해 보세요! 피부 상태가 확 달라지는 걸 느낄 수 있을 거에요!
탄력, 광채, 보습까지 챙기는 달바 화이트 트러플 세럼!
저 한 번 믿고 시작해보세요!'

[Notes]
- 예시 출력을 참고할 것.
- 총 CAPTION_COUNT개의 문장을 각각 5초 분량으로 재생 가능하게 작성
- 20대, 30대 커뮤니티 문화를 깊이 이해하고 이를 반영합니다.
- 트렌디한 요소들을 정확히 파악하고 적용하는 데 중점을 둡니다.

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
