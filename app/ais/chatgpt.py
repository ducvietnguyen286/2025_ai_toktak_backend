import json
import time
from openai import OpenAI, OpenAIError
from app.services.request_log import RequestLogService
import os
import re
from app.lib.logger import logger

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def call_chatgpt_create_caption(images=[], data={}, post_id=0):

    prompt = """[역할]  
당신은 SNS 숏폼 콘텐츠 전문가입니다.  
사용자의 Pain Point(불편함, 고민, 불만 등)를 중심으로 문제를 제시하고,  
해결책으로 제품을 자연스럽게 연결하는 방식으로 영상 콘텐츠를 제작합니다.  
hooking, title, description은 클릭 유도와 SEO 최적화 목적에 맞춰 작성해야 합니다.  
모든 문장은 완전한 구문이어야 하며, 이모티콘과 감탄사, 밈 표현은 사용하지 않습니다.

[입력 정보]  
- 제품명: {name}  
- 가격: {price}  
- 제품 설명: {description}  
- 판매처: {store_name}  
- 제품 링크: {base_url}  
- 제품 소개: {text}  

[작성 조건]

hooking:  
- 총 4개 문장  
- 각 문장 20자 이내  
- 제품명 언급 없이 호기심, 클릭 유도, 한정성, 특가 강조 등으로 구성  
- 예시:  
  - 지금만 뜨는 특가, 안 보면 후회해요  
  - 몰랐으면 손해일 뻔했죠  
  - 링크 타고 들어가면 숨겨진 혜택 있어요  
  - 요즘 인기템, 여기서만 싸게 팔아요  

title:  
- 상품명보다 **제품 카테고리 중심 키워드** 포함 (SEO 목적)  
- 필요 시 상품명은 부제처럼 자연스럽게 삽입  
- 예시:  
  - 속눈썹 세럼 고민 중이라면 이 제품 보세요  
  - 기내용 캐리어, 디자인이 진짜 다릅니다  

description:  
- 총 3줄 구성  
  1줄: pain 강조 + 해결 제안 (예: 속눈썹 숱 적고 자꾸 빠진다면, 이 세럼 써보세요)  
  1줄: 둘째 줄: 고정 형식  
      `"[지금 클릭하면 숨겨진 할인 공개] {base_url} \n"`
  3줄: {name}  

caption:  
- 공백 포함 750자 이상  
- 스토리텔링 구조  
- 최소 2가지 요소 포함  
  - 제품 사용 후의 변화  
  - 기능적 장점  
  - 사회적 증거(후기, 재구매 등)  
  - 소비자 망설임 설득 요소  
- 구어체 문장, 말줄임표/감탄사/이모티콘 사용 금지  
- 문장은 반드시 끝맺기  

hashtag:  
- 총 10~15개  
- {name} 포함  
- 기능 강조 키워드(추천, 효과 등) 제외  
- 실제 사용자가 검색할 법한 키워드 위주  
- 문장형/밈/지나치게 긴 해시태그는 금지  

[출력 형식 예시]
```json
{
    "response": {
        "hooking": [
            "hooking 1",
            "hooking 2",
            ...
        ],
        "caption": "최근 몇 년간, 많은 사람들이 자신의 외모를 개선하기 위해 다양한 제품과 서비스를 시도하고 있습니다. 특히, 속눈썹은 얼굴의 중요한 부분 중 하나로, 많은 여성들이 이를 강조하기 위해 속눈썹 세럼이나 속눈썹 영양제를 사용하고 있습니다. 이러한 제품들은 속눈썹의 성장을 촉진하고, 건강한 상태를 유지하는 데 도움을 줍니다.
속눈썹 세럼은 주로 비타민과 미네랄이 풍부한 성분으로 구성되어 있으며, 이는 속눈썹의 건강을 증진시키고, 자연스럽게 길고 풍성하게 만드는 데 효과적입니다. 또한, 이러한 제품들은 사용이 간편하여, 매일 밤 잠자리에 들기 전에 간단히 바르기만 하면 됩니다.
많은 사용자들이 속눈썹 세럼을 사용한 후, 눈에 띄는 변화를 경험했습니다. 예를 들어, 속눈썹이 더 길고 두꺼워졌으며, 전체적인 외모가 더 매력적으로 변했다는 후기가 많습니다. 이러한 변화는 자신감을 높여주고, 일상생활에서 더 자신 있게 생활할 수 있도록 도와줍니다.
또한, 속눈썹 세럼은 사회적 증거로도 뒷받침되고 있습니다. 많은 유명 인플루언서와 블로거들이 이러한 제품을 사용한 후, 긍정적인 리뷰를 남기고 있으며, 이는 제품의 신뢰성을 높여줍니다. 또한, 재구매율이 높다는 점도 제품의 효과를 입증하는 중요한 요소입니다.
따라서, 속눈썹을 개선하고자 하는 사람들에게 속눈썹 세럼은 매우 추천할 만한 제품입니다. 이 제품은 사용이 간편하고, 효과가 뛰어나며, 많은 사용자들이 긍정적인 경험을 하고 있다는 점에서 큰 장점을 가지고 있습니다. 만약 당신이 더 매력적인 외모를 원한다면, 속눈썹 세럼을 시도해 보는 것은 좋은 선택이 될 것입니다.",
        "title": "",
        "description": "Description? \n[지금 클릭하면 숨겨진 할인 공개] https://example.com \nProduct Name",
        "hashtag": #속눈썹세럼 #속눈썹영양제 #쿠팡추천 #눈썹케어 #변신 #속눈썹성장 #속눈썹관리 #아이래쉬세럼 #속눈썹케어 #관리비결 #내맘속1등 #인생꿀템 #자기관리 #관리하는여자
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

    return call_chatgpt(content, response_schema, post_id)


def call_chatgpt_create_blog(images=[], data={}, post_id=0):

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

    return call_chatgpt(content, response_schema, post_id)


def call_chatgpt_create_social(images=[], data={}, post_id=0):
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

    return call_chatgpt(content, response_schema, post_id)


def call_chatgpt_clear_product_name(name):
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
    for message in thread_messages:
        if message.role == "assistant":
            return message.content[0].text.value
    return name


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
        print(f"chatgpt_api_key{chatgpt_api_key}")
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
