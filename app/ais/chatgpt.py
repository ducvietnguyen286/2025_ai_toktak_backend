from hashlib import sha1
import json
import time
from openai import OpenAI, OpenAIError
from app.lib.link import get_item_id, get_link_type, get_vendor_id
from app.services.chatgpt_result import ChatGPTResultService
from app.services.request_log import RequestLogService
import os
import re
from app.lib.logger import logger

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def save_to_database(type, data, response):
    try:
        name = ""
        name_hash = ""
        link = ""
        link_type = ""
        item_id = ""
        vendor_id = ""
        if list(data.keys()) == ["name"]:
            name = data["name"]
            name_hash = sha1(data["name"].encode("utf-8")).hexdigest()
        else:
            item_id = get_item_id(data)
            vendor_id = get_vendor_id(data)
            link = (
                data.get("url_crawl", "")
                if "url_crawl" in data
                else data.get("base_url", "")
            )
            link_type = get_link_type(link)
        ChatGPTResultService.create_chatgpt_result(
            type=type,
            response=json.dumps(response),
            link_type=link_type,
            link=link,
            item_id=item_id,
            vendor_id=vendor_id,
            name_hash=name_hash,
            name=name,
        )
    except Exception as e:
        logger.error(f"Error saving to database: {str(e)}")


def get_from_database(type, data):
    try:
        if list(data.keys()) == ["name"]:
            name_hash = sha1(data["name"].encode("utf-8")).hexdigest()
            chatgpt_result = ChatGPTResultService.find_one_chatgpt_result_by_filter(
                type=type,
                name_hash=name_hash,
            )
        else:
            item_id = get_item_id(data)
            vendor_id = get_vendor_id(data)
            link = (
                data.get("url_crawl", "")
                if "url_crawl" in data
                else data.get("base_url", "")
            )
            link_type = get_link_type(link)
            if link_type == "COUPANG":
                chatgpt_result = ChatGPTResultService.find_one_chatgpt_result_by_filter(
                    type=type,
                    link_type=link_type,
                    item_id=item_id,
                    vendor_id=vendor_id,
                )
            else:
                chatgpt_result = ChatGPTResultService.find_one_chatgpt_result_by_filter(
                    type=type,
                    link_type=link_type,
                    item_id=item_id,
                )
        if chatgpt_result:
            return json.loads(chatgpt_result.response)
        else:
            return None
    except Exception as e:
        logger.error(f"Error retrieving from database: {str(e)}")
        return None


def call_chatgpt_create_caption(images=[], data={}, post_id=""):
    # response_database = get_from_database("video", data)
    # if response_database:
    #     return response_database
    prompt = """[역할]
당신은 SNS 숏폼 콘텐츠 전문가입니다.
사용자의 Pain Point(불편함, 고민, 불만 등)를 중심으로 문제를 제시하고,
해결책으로 제품을 자연스럽게 연결하는 방식으로 영상 콘텐츠를 제작합니다.
hooking, title, description은 클릭 유도와 SEO 최적화 목적에 맞춰 작성해야 하며,
caption은 논리적 흐름을 갖춘 4단 구성으로 작성합니다.
모든 문장은 완전한 문장으로 구성되어야 하며, 국어적으로 어색한 표현 없이 자연스러워야 합니다.
감탄사, 이모티콘, 밈 표현은 사용하지 않습니다.

[입력 정보]
제품명: {name}
가격: {price}
제품 설명: {description}
판매처: {store_name}
제품 링크: {base_url}
이미지 개수: {image_count}
제품 소개: {text}

[작성 조건]

hooking:
- 총 4개 문장
- 각 문장 20자 이내
- 제품명 언급 없이 호기심, 클릭 유도, 한정성, 특가 강조 중심
- 예시:
  - 지금만 뜨는 특가, 안 보면 후회해요
  - 몰랐으면 손해일 뻔했죠
  - 링크 타고 들어가면 숨겨진 혜택 있어요
  - 요즘 인기템, 여기서만 싸게 팔아요

title:
- 제품 카테고리 중심 키워드 포함 (SEO 목적)
- 필요 시 상품명을 부제처럼 자연스럽게 삽입
- 예시:
  - 속눈썹 세럼 고민 중이라면 이 제품 보세요
  - 기내용 캐리어, 디자인이 진짜 다릅니다

description:
- 총 3줄 구성  
  1줄: Pain Killer 형식 – 고민 공감 + 제품 제안 (구어체, 단정적이지 않게)  
     예: "속눈썹 때문에 눈화장 망친 적 있다면, 이거 써보세요"  
  2줄: [지금 클릭하면 숨겨진 할인 공개] {base_url}  
  3줄: {name}  
- 이모티콘, 특수문자 사용 금지  

caption:
- 총 4개 단락으로 구성된 하나의 텍스트
- 각 단락은 줄바꿈(\\n)으로 명확히 구분
- 모든 문장은 구어체로 자연스럽게 작성하며, 완전한 종결 문장으로 마무리
- 각 단락 구성 기준:

1. 문제 제기 및 공감 (최소 250자, 최소 4문장)
   - 자주 겪는 스트레스, 반복된 실망, 생활 속 불편함 표현
   - 공감 가능한 사례형 묘사

2. 제품 기능 및 사용 변화 설명 (최소 500자, 최소 6문장)
   - 개선 방식, 효과 지속 시간, 사용법, 편의성, 주요 기능
   - 구체적인 장점 나열, 변화 전후 비교 포함

3. 사용자 후기 또는 사회적 증거 (선택 사항)
   - 재구매율, 후기 수, 평균 평점, 후기 인용 등
   - 생략 가능 (생략 시 2번을 자연스럽게 연장)

4. 마무리 제안 또는 전환 유도 (선택 사항, 최소 1문장, 100자 이상)
   - 문제 재상기 + 긍정적 제안
   - 생략 가능 (랜덤하게)

hashtag:
- 총 10~15개
- {name} 포함
- 기능 강조 키워드(추천, 효과 등)는 사용 금지
- 실사용자가 검색할 법한 단어 위주
- 밈, 문장형, 과도하게 긴 해시태그 금지

[출력 형식 예시]
{
  "response": {
    "hooking": [
      "몰랐으면 손해였죠",
      "여기서만 할인가예요",
      "지금 안 보면 늦어요",
      "클릭 한 번이면 끝납니다"
    ],
    "caption": "속눈썹이 하루가 다르게 빠지는 느낌, 한 번쯤 경험해보셨을 거예요. 아침마다 거울을 보면 빈약한 속눈썹 때문에 눈매가 또렷해 보이지 않고, 뷰러로 올려도 금방 처져버려 메이크업 만족도도 떨어졌죠. 속눈썹 숱이 적으면 마스카라로도 채워지지 않으니까요. 그래서 눈화장 할 때마다 점점 스트레스가 쌓이더라고요.\\n그런 고민을 해결해준 게 바로 이 속눈썹 세럼이에요. 저녁마다 자기 전에 한 번만 발라주는 루틴인데, 며칠 지나면서 속눈썹 뿌리 쪽이 덜 빠지는 게 확실히 느껴졌어요. 2주쯤 지나자 숱이 늘고 컬도 더 오래 유지돼서 메이크업할 때 정말 편했죠. 성분도 순해서 눈에 자극이 없고, 끈적임도 없어서 매일 사용하기 부담 없었어요. 지금은 오히려 안 바르면 허전할 정도예요.\\n리뷰만 수백 개 넘게 달린 제품이고, ‘마스카라보다 낫다’는 말이 많을 만큼 만족도가 높아요. 블로거나 유튜버들도 실제 후기를 많이 올렸더라고요. 이런 점들이 신뢰감을 주는 것 같아요.\\n속눈썹 때문에 매일 고민하셨던 분이라면, 이 제품으로 시작해보는 건 어떨까요? 눈에 띄는 변화가 생각보다 빨리 시작될 수 있어요.",
    "title": "속눈썹 세럼, 풍성한 눈매를 위한 시작",
    "description": "속눈썹 자꾸 빠지거나 숱이 부족하다면, 이 세럼 써보세요\n[지금 클릭하면 숨겨진 할인 공개] https://example.com\n베이글에스 속눈썹영양제 아이래쉬 퍼펙트세럼",
    "hashtag": "#베이글에스 #속눈썹영양제 #아이래쉬세럼 #속눈썹관리 #속눈썹케어 #뷰티템 #눈매보강 #속눈썹강화 #데일리뷰티 #속눈썹성장 #속눈썹세럼 #속눈썹개선 #자기관리 #속눈썹라인"
  }
}
"""
    prompt = replace_prompt_with_data(prompt, data)

    prompt = prompt.replace("CAPTION_COUNT", str(len(images)))

    content = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": image}})

    response_schema = {
        "name": "response_schema",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "object",
                    "properties": {
                        "hooking": {
                            "type": "array",
                            "description": "hooking message",
                            "items": {"type": "string"},
                        },
                        "caption": {
                            "type": "string",
                            "description": "caption for making video.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the response.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description text displayed separately from the image on platforms like YouTube, Instagram, and TikTok.",
                        },
                        "hashtag": {
                            "type": "string",
                            "description": "Hashtag associated with the response.",
                        },
                    },
                    "required": [
                        "hooking",
                        "caption",
                        "title",
                        "description",
                        "hashtag",
                    ],
                    "additionalProperties": False,
                }
            },
            "required": ["response"],
            "additionalProperties": False,
        },
    }

    response = call_chatgpt(content, response_schema, post_id)
    # if response:
    #     if "error" in response:
    #         return response
    #     save_to_database("video", data, response)

    return response


def call_chatgpt_create_blog(images=[], data={}, post_id=0):
    # response_database = get_from_database("blog", data)
    # if response_database:
    #     return response_database

    prompt = """업로드된 이미지들을 참고하여, 제품의 다음 세부 정보를 반영한 블로그 게시글을 작성해 주세요.

[역할]  
당신은 한국의 블로그 포스트 전문가입니다.  
상품에 따라 관심이 주목될 만한 연령대를 찾아서 최적의 블로그 포스트를 만들어주세요.  
유행어와 밈, 감성을 자극하여 해당 블로그의 포스트를 흥미롭게 볼 수 있도록 실제 후기처럼 자연스럽고 공감되는 톤으로 작성해 주세요.

[생성 조건]  

caption: 이 블로그 글이 전달해야 할 분위기, 핵심 메시지, 중심 감성을 각 항목별로 200~300자로 요약해 주세요.  
당신은 이 캡션을 바탕으로 전체 글의 톤을 설정하고, 제목과 첫 문단에도 해당 감성을 반영합니다.

제품 관련 정보:  
- 제품명: {name}  
- 가격: {price}  
- 제품 설명: {description}  
- 판매처: {store_name}  
- 제품 링크: {base_url}  
  - 링크는 반드시 "https://..." 형태의 링크 주소 그 자체가 텍스트로 출력되도록 하세요.  
  - 다른 문장이나 제품명 등으로 대체된 하이퍼링크 형식은 금지합니다.  
  - 예시 출력: https://s.toktak.ai/B0ei2u  
- 제품 소개: {text}

[가이드라인]:  
- 게시글은 약 2400자 분량으로 작성해 주세요.
- 제품의 특징, 장점, 사용 방법 등을 친근하고 진솔한 어조로 전달해 주세요.
- 아래 두 가지 형식으로 결과를 출력해 주세요:
  1. `docx_content`: 텍스트와 "IMAGE_URL_0" 같은 이미지 인덱스를 포함한 배열
  2. `content`: HTML 형식의 본문 (`<img src="IMAGE_URL_0">` 형식 사용)  
- 글의 시작에는 독자의 시선을 끌 수 있는 매력적인 제목(title)을 포함해 주세요.  
- 제목 바로 아래에는 광고 영역 또는 안내 문구를 삽입하기 위해 <h2>ADS_CONTENT_TOKTAK</h2> 태그를 반드시 포함해 주세요.
  3. 타이틀 작성 지침:  
  - 제목에는 링크주소의 상품명을 직접적으로 포함해서 작성하지 마세요. 반드시 예시와 같이 준수하도록 합니다.
  - 상품의 카테고리, 특징, 사용자 상황 등을 기반으로 자연스러운 블로그 타이틀로 예시를 참고하여 작성해주세요.  
  - 예시:  
    - 스위스밀리터리 기내용 캐리어 → "인생 캐리어 추천! 여행이 달라졌어요"  
    - 베이글에스 속눈썹 세럼 → "나만의 속눈썹 루틴, 진짜 효과 봤어요!"  
    - 블루마틴 우디 블랙 향수 → "남자 향수 고민 중이라면? 이 향 추천드려요"  

- 이미지는 업로드된 목록 중 적절한 것들을 선택하여 자연스럽게 삽입해 주세요.  

[요약문 및 해시태그 지침]  
- summarize는 실제 사용자의 1인칭 후기 스타일로 작성해 주세요.  
  - 예: "이 캐리어 하나 바꾸고 여행 준비가 훨씬 쉬워졌어요. 공항에서 끌고 다닐 때마다 너무 만족해요~"  

[블로그 포스트다운 구성 포인트]  
- 스토리텔링 도입부: 개인적인 경험이나 고민으로 시작해 공감대를 형성하세요.  
- 사용 계기 + 첫인상: 제품을 알게 된 계기와 사용해 본 첫 느낌을 자연스럽게 전달하세요.  
- 사용법 + 실사용 후기: 제품 사용 중의 경험을 감각적으로 표현하고, 장점을 구체적으로 설명하세요.  
- 감정의 흐름 표현: ‘처음엔 반신반의 → 써보니 만족’ 같은 심리 변화가 드러나야 합니다.  
- 자연스러운 마무리: ‘저처럼 고민 중인 분들께 도움이 될지도 몰라요 :)’ 같은 간접 추천 형식으로 마무리하세요.
- 마무리 후 hashtag 노출: {name}을 포함한 총 10~15개 해시태그를 한 줄 문자열로 작성하세요.(출력 예시: #기내용캐리어, #여행가방추천, #스위스밀리터리, #공항패션, #여행가방, #트래블필수품, #20대여행템, #소형캐리어추천, #수납력좋은캐리어, #여행아이템)

**docx_content 작성 지침 (필수 출력 형식)**

- `docx_content`는 블로그 글의 본문을 **문단 단위로 배열로 구성**합니다.  
- 각 항목은 **텍스트** 또는 `"IMAGE_URL_0"` 형식의 이미지 인덱스입니다.

    1. 공감가는 도입부 (1인칭 경험담 시작)  
    2. 제품을 알게 된 계기와 첫인상  
    3. 사용 방법 설명  
    4. 실사용 후기 및 장점  
    5. 심리 변화 묘사 (의심 → 만족)  
    6. 간접 추천으로 마무리  
    7. 적절한 위치에 이미지 인덱스 삽입 (총 3~5장)  
    8. **제품 구매 링크 (base_url)** – `https://...` 형식의 주소를 **텍스트 그대로** 출력  
    9. 마무리 후 hashtag 노출: {name}을 포함한 총 10~15개 해시태그를 한 줄 문자열로 작성하세요.(출력 예시: #기내용캐리어, #여행가방추천, #스위스밀리터리, #공항패션, #여행가방, #트래블필수품, #20대여행템, #소형캐리어추천, #수납력좋은캐리어, #여행아이템)

[표현 스타일 지침 – 실제 블로거 후기처럼 보이도록]  
- 반드시 1인칭 관점으로 작성하며, 마치 블로거가 자신의 경험을 이야기하듯 자연스럽게 말하듯 풀어주세요.  
- 감탄, 반전, 유머, 공감 포인트를 적극적으로 사용해 주세요.  
- 정보 나열이 아니라, 체험 속에 제품 정보를 자연스럽게 녹여서 보여주세요.  
- “추천합니다”, “최고의 선택” 같은 광고 표현은 사용하지 마세요.

### **🔹 Output Format (JSON)**
```json
{
    "title": "블로그 게시글 제목",
    "summarize": "요약된 내용",
    "docx_content": [
        "ADS_CONTENT_TOKTAK",
        "제품의 특징 및 장점에 대해 설명하는 첫 번째 단락",
        "IMAGE_URL_0",
        "제품 사용 방법에 대한 설명이 포함된 두 번째 단락",
        ...,
        "IMAGE_URL_{image_index}",
        "제품을 구매하는 방법과 판매처 정보",
        "{base_url}",
        "#hashtag1 #hashtag2 #hashtag3"
    ],
    "content": "<h1>블로그 게시글 제목</h1>
                <h2>ADS_CONTENT_TOKTAK</h2>
                <p>제품의 특징 및 장점에 대해 설명하는 첫 번째 단락 </p>
                <p><img src="IMAGE_URL_0" alt="{name}"></p>
                <p>제품 사용 방법에 대한 설명이 포함된 두 번째 단락</p>
                ...etc
                <p><img src="IMAGE_URL_{image_index}" alt="{name}"></p>
                <p>제품을 구매하는 방법과 판매처 정보</p>
                <p>{base_url}</p>
                <p>#hashtag1 #hashtag2 #hashtag3</p>
}

Note: 

- 이 글에는 {count_image}장의 사진만 등장합니다.
"""
    count_image = len(images)
    image_index = count_image - 1
    data["image_index"] = image_index
    data["count_image"] = image_index

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
                        "docx_content": {
                            "type": "array",
                            "description": "The content will be written to the docx file.",
                            "items": {"type": "string"},
                        },
                        "content": {
                            "type": "string",
                            "description": "The main content of the response.",
                        },
                    },
                    "required": ["title", "summarize", "docx_content", "content"],
                    "additionalProperties": False,
                }
            },
            "required": ["response"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    response = call_chatgpt(content, response_schema, post_id)
    # if response:
    #     if "error" in response:
    #         return response
    #     save_to_database("blog", data, response)

    return response


def call_chatgpt_create_social(images=[], data={}, post_id=0):
    # response_database = get_from_database("image", data)
    # if response_database:
    #     return response_database

    prompt = """[역할]  
당신은 SNS 바이럴 콘텐츠 제작 전문가입니다.  
사용자의 Pain Point(불편함, 아쉬움, 고민 등)를 중심으로 문제를 제시하고,  
제품을 통해 자연스럽게 해결해나가는 구조로 콘텐츠를 만듭니다.  
caption과 description은 논리적으로 연결되고, 말투와 분위기가 일관되어야 하며,  
모든 문장은 실제 사용자가 말하는 듯한 자연스러운 구어체로 작성되어야 합니다.

[입력 정보]  
제품명: {name}  
가격: {price}  
제품 설명: {description}  
판매처: {store_name}  
제품 링크: {base_url}  
이미지 개수: {image_count}  
제품 소개: {text}  

[작성 조건]  
caption  
- 총 5문장  
- 각 문장 100자 이내, 줄 수 2줄 이하  
- 전체 흐름 구조:  
  1. caption1: 제품과 관련된 대표적인 Pain Point 제시  
     - 단정적으로 끝내지 말고, 의문형, 감탄형, 탄식형 등으로 마무리  
     - 예: “속눈썹 자꾸 빠지는 거 은근 스트레스죠?”  
  2. caption2~4: 제품 사용 후 변화, 장점, 기능을 구체적으로 설명  
     - 문장 간 흐름은 매끄럽게 이어질 것  
  3. caption5: caption1과 연결되는 수미상관형 구조  
     - 제품의 기능적 가치를 담아 자연스럽고 설득력 있게 마무리  

description  
- 총 3줄 구성  
  1줄: Pain Killer 형식 – 고민 공감 + 제품 제안 (구어체, 단정적이지 않게)  
     예: "속눈썹 때문에 눈화장 망친 적 있다면, 이거 써보세요"  
  2줄: [지금 클릭하면 숨겨진 할인 공개] {base_url}  
  3줄: {name}  
- 이모티콘, 특수문자 사용 금지
- 각 줄은 "\n" 문자로 구분됩니다  

hashtag  
- 총 10~15개  
- 반드시 #으로 시작  
- {name} 포함  
- 기능 강조형 키워드(예: 추천, 효과 등)는 제외  
- 실제 사용자가 검색할 만한 키워드 위주로 구성  
- caption 및 description과 별도로 출력

[출력 형식 예시]
{
  "response": {
    "caption": [
      "부팅만 3분 걸리는 노트북, 진짜 너무 답답하지 않나요?",
      "SSD로 바꾸고 체감 속도가 완전히 달라졌어요.",
      "작업하다 멈추는 일 없이 쾌적하게 쓸 수 있었고요.",
      "오래된 노트북이 이렇게 다시 살아날 줄 몰랐어요.",
      "부팅 때문에 스트레스였던 분들, 이건 꽤 만족하실 거예요."
    ],
    "description": "부팅만 3분 넘게 기다리셨다면, SSD 탑재된 이 노트북 써보세요\n[지금 클릭하면 숨겨진 할인 공개] https://example.com\n삼성 노트북 i5 4세대 8G SSD 240 NT370E5J",
    "hashtag": "#삼성노트북 #SSD노트북 #부팅빠른 #사무용노트북 #중고노트북 #문서작업 #가성비노트북 #업무용PC #i5노트북 #윈도우노트북 #노트북추천 #속도업 #중고PC"
  }
}
"""

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
                        "caption": {
                            "type": "array",
                            "description": "caption for making video.",
                            "items": {"type": "string"},
                        },
                        "description": {
                            "type": "string",
                            "description": "The description of the post.",
                        },
                        "hashtag": {
                            "type": "string",
                            "description": "The associated hashtag.",
                        },
                    },
                    "required": ["caption", "description", "hashtag"],
                    "additionalProperties": False,
                }
            },
            "required": ["response"],
            "additionalProperties": False,
        },
        "strict": True,
    }

    response = call_chatgpt(content, response_schema, post_id)
    # if response:
    #     if "error" in response:
    #         return response
    #     save_to_database("image", data, response)

    return response


def call_chatgpt_clear_product_name(name):
    response_database = get_from_database("product_name", {"name": name})
    if response_database:
        return response_database.get("name", name)

    client = OpenAI(api_key=chatgpt_api_key)
    assistant_id = "asst_EK0uKR3AbhB2Js9cESzqRIxa"
    empty_thread = client.beta.threads.create()
    client.beta.threads.messages.create(
        empty_thread.id,
        role="user",
        content=[{"type": "text", "text": name}],
    )
    run = client.beta.threads.runs.create(
        thread_id=empty_thread.id, assistant_id=assistant_id
    )
    while True:
        run = client.beta.threads.runs.retrieve(
            run_id=run.id, thread_id=empty_thread.id
        )
        if run.status == "completed":
            break

    thread_messages = client.beta.threads.messages.list(empty_thread.id)

    response_name = name
    for message in thread_messages:
        if message.role == "assistant":
            response_name = message.content[0].text.value

    if response_name != name:
        save_to_database("product_name", {"name": name}, {"name": response_name})

    return response_name


def call_chatgpt_get_main_text_and_color_for_image(
    input_text, requested_fields, post_id=0
):
    prompt = """당신은 색상 디자인 전문가입니다. 다음 요구 사항을 충족하는 색상 팔레트를 만들어 주세요.

1. **주요 텍스트 색상 (`main_text_color`)**: 밝고 눈길을 끄는 색상이며, 열대적인 느낌이 나는 색상을 선택하세요.  
2. **보조 텍스트 색상**: 항상 흰색으로 설정합니다.  
3. **배경 색상 (`background`)**: 주요 텍스트 색상 및 보조 텍스트(흰색)와 좋은 대비를 이루는 밝은 색상을 선택하세요.  
4. **배경 색상이 너무 단조롭거나 흰색과 비슷하지 않도록 주의하세요. "연한 분홍", "연한 노랑" 등의 색상이 적절합니다.**  

또한, 아래의 문장을 제공합니다. 이 문장에서 핵심 내용을 찾아 `main_text` 값으로 사용하세요.  

"{input_text}"  

제가 원하는 데이터 필드는 `{requested_fields}` 입니다.  

**다음 JSON 형식으로 결과를 반환하세요 (요청한 필드만 포함)**:
```json
{
    "main_text": "문장의 핵심 내용",
    "main_text_color": "", // 예: "#FF5733"
    "background": "" // 예: "#FFF9C4"
}

"""
    prompt = replace_prompt_with_data(
        prompt, {"input_text": input_text, "requested_fields": requested_fields}
    )

    response_schema = {
        "name": "response_schema",
        "schema": {
            "type": "object",
            "properties": {
                "main_text": {
                    "type": "string",
                    "description": "Main Text",
                },
                "main_text_color": {
                    "type": "string",
                    "description": "Main Text Color",
                },
                "background_color": {
                    "type": "string",
                    "description": "Background Color",
                },
            },
            "required": ["main_text", "main_text_color", "background_color"],
            "additionalProperties": False,
        },
        "strict": True,
    }
    return call_chatgpt(prompt, response_schema, post_id)


def replace_prompt_with_data(prompt, data):
    for key, value in data.items():
        prompt = prompt.replace("{" + key + "}", str(value))
    return prompt


def call_chatgpt(
    content, response_schema, post_id=0, base_prompt=None, temperature=0.9, retry=0
):
    client = OpenAI(api_key=chatgpt_api_key)
    model = "gpt-4o-mini"

    messages = []
    if base_prompt:
        messages.append({"role": "system", "content": base_prompt})
    messages.append({"role": "user", "content": content})

    request_log = json.dumps(
        {
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": response_schema,
            },
            "max_tokens": 16384,
            "temperature": temperature,
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
            max_tokens=16384,
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
            if not status:
                if retry < 2:
                    return call_chatgpt(
                        content, response_schema, post_id, base_prompt, retry=retry + 1
                    )
            return content
        return None
    except Exception as e:
        logger.error(f"[ChatGPT API Error] {e}")
        response_log = json.dumps({"error": str(e)})
        RequestLogService.create_request_log(
            post_id=post_id,
            ai_type="chatgpt",
            request=request_log,
            response=response_log,
            status=0,
        )
        return None


def translate_notifications_batch(notifications_batch):
    try:
        client = OpenAI(api_key=chatgpt_api_key)

        assistant_id = "asst_rBXxdDDCdHuv3UxNDTiHrxVv"

        # Format input cho GPT: ID + nội dung
        prompt = "Bạn hãy dịch các thông báo sau sang tiếng Hàn Quốc . Giữ nguyên ID và đúng thứ tự:\n"
        for n in notifications_batch:
            prompt += f"ID {n['id']}: {n['text']}\n"

        # Tạo thread
        thread = client.beta.threads.create()

        # Gửi tin nhắn vào thread
        client.beta.threads.messages.create(
            thread.id,
            role="user",
            content=[{"type": "text", "text": prompt}],
        )

        # Tạo run
        run = client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=assistant_id
        )

        # Chờ phản hồi (timeout: 30s)
        timeout_seconds = 30
        start_time = time.time()
        while True:
            run = client.beta.threads.runs.retrieve(run.id, thread_id=thread.id)
            if run.status == "completed":
                break
            elif run.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Run status error: {run.status}")
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError("GPT processing timeout.")
            time.sleep(1)

        # Lấy phản hồi
        messages = client.beta.threads.messages.list(thread.id)
        for message in messages:
            if message.role == "assistant" and message.content:
                # Trích xuất nội dung văn bản phản hồi
                translated_text = message.content[0].text.value
                return parse_translations(translated_text)

        return {}

    except OpenAIError as e:
        logger.error(f"[OpenAI API Error xxxxxxxxxx] {e}")
        print(f"[OpenAI API Error] {e}")
    except TimeoutError as e:
        logger.error(f"[Timeout Error] {e}")
        print(f"[Timeout Error] {e}")
    except Exception as e:
        logger.error(f"[Unhandled  Error] {e}")
        print(f"[Unhandled Error] {e}")

    # Nếu lỗi, trả về dict rỗng
    return {}


def parse_translations(response_text):
    """
    Phân tích phản hồi từ GPT để lấy lại ID và bản dịch.
    Ví dụ đầu vào:
    ID 101: Có bản cập nhật mới cho thiết bị của bạn.
    ID 102: Pin yếu.
    """
    translations = {}
    lines = response_text.strip().split("\n")
    for line in lines:
        match = re.match(r"ID\s*(\d+):\s*(.+)", line)
        if match:
            notif_id = int(match.group(1))
            translated_text = match.group(2).strip()
            translations[notif_id] = translated_text
    return translations
