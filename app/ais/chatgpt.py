import json
import time
from openai import OpenAI
from app.services.request_log import RequestLogService
import os

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def call_chatgpt_create_caption(images=[], data={}, post_id=0):

    prompt = """업로드된 이미지를 참고하여 제품을 홍보하는 숏폼(Shorts, TikTok) 스타일의 영상 콘텐츠를 제작하도록 지원해 드립니다.

[역할]
당신은 20~30대 커뮤니티에서 유행하는 언어를 활용하는 애플의 바이럴 마케터입니다. 상품을 홍보하는 영상을 만드는 작업을 진행할 예정입니다. FOMO, 사회적 증가, 공감과 감성 자극, 첫 3초의 법칙, 자이가르닉효과 등 적절한 심리학 기법을 상황에 맞게 사용하여 스크립트를 작성하세요. 어떤 기법이 적절한지 고려한 후, 이를 바탕으로 정확한 실행을 계획합니다.

[요구 사항]
- **전체적인 형식**: 
  - FOMO, 사회적 증가 등의 심리학 기법을 상황에 맞게 활용하여 스크립트를 제작합니다. 
  - 각 요소가 어떻게 심리적 효과를 주는지 이해하고, 이를 어떻게 활용할 것인지 설명한 후 스크립트를 작성합니다.
  - 유머러스하고 도발적인 문체 사용 및 커뮤니티 특유의 밈(meme)과 유행어 활용
  - 댓글 반응을 유도할 수 있도록 구성합니다.

[입력 정보]
- 제품명: {name}
- 가격: {price}
- 제품 설명: {description}
- 판매처: {store_name}
- 제품 링크: {base_url}
- 제품 소개: {text}

- 순수 텍스트 형식으로 반환
- 특수 문자 및 Markdown 사용 금지
- caption에서 이모티콘 사용 금지

[생성 조건]
- **hooking**: 
  - 총 4개의 문장을 각각 20자 이내의 텍스트로 작성 

- **caption**: 
  - 약 450글자로 caption을 생성할 것, 이모티콘 사용 절대 금지. 
  - 이모티콘 사용 금지
  - 스토리텔링 형식으로 상품에 대해서 소개하는 caption 작성
  - 반드시 "[예시 출력]의 ##caption"을 참고해서 작성할 것.
  - 한 문장을 끝까지 온전하게 작성할 것.
  - 유머 코드와 밈(meme) 반영
  - 커뮤니티 특유의 자연스러운 표현 사용

- **title**: 
  - title은 유튜브 제목으로 들어갈 내용
  - 유튜브에서 클릭을 유도할 수 있는 흥미로운 표현 포함

- **description**: 
  - 문장 최대 2줄로 작성
  - 줄바꿈 후 "구매링크👉: {base_url}" 이 문장 무조건 표시 
  - 구매링크 다음에 줄바꿈 후 "{name}" 무조건 포함
  - 문장을 정확하게 끝내지 말고, 말 끝을 흐릴 것 

- **hashtag**: 
  - {name} 무조건 포함 
  - 제품군과 관련된 해시태그 선정, 캡션과 분리된 개별 목록으로 제공
  - 제품 및 타겟 고객층에 맞는 인기 해시태그 선정
  - 개별 해시태그로 제공하며, 캡션과 분리하여 작성합니다.

[예시 출력]
## hooking:
1. 영상 시작 시 
- 이 기능 몰랐다면 손해!
- 이거 없으면 불편함 폭발!
- 알고 보면 인생템! 끝까지 보세요.
- 이 제품, 왜 난리 난 걸까?
- 이거 보면 무조건 갖고 싶어집니다!
- 처음 보면 궁금한데, 쓰면 못 끊어요.
- 지금 스크롤하면 후회할 수도 있어요!
- 사람들이 열광하는 이유? 마지막에 공개!
- 한 번 보면 계속 찾게 됩니다.
- 왜 이걸 이제야 알았을까?
- 이거 하나면 해결 끝!
- 유튜버들이 극찬한 바로 그 제품!

2. 첫 번째 이미지 시작 시 (2초간 표시)
- 수많은 사용자가 선택한 인기템! 이유가 뭘까요?
- 리뷰 평점 ★★★★★, 실사용자가 전하는 찬사!
- 사용자들이 극찬하는 혁신, 직접 경험해보세요.
- 한 번 쓰면 멈출 수 없는 놀라운 기능!
- 사용자들이 재구매하는 그 제품!
- 유명 유튜버들이 추천하는 아이템!
- 전 세계 사용자들이 선택한 베스트셀러, 그 이유는?
- 온라인 인기 순위 1위! 지금 확인하세요.
- 이 가격에 이 성능, 믿기 어려울 정도입니다!

3. 세 번째 이미지 시작 시 (2초간 표시)
- 이거 없었으면 아직도 불편했을 걸?
- 이 제품 하나로 고민 끝! 사용법도 초간단
- 일상이 편해지는 마법, 한 번 써보세요!
- 이제 더 이상 불편함 NO! 완벽한 해결책
- 매일 쓰는 물건, 더 편하게 바꿔보세요!
- 돈 아끼는 법? 이 제품이 답입니다!
- 한 번 써보면 다른 건 못 씁니다.
- 이거 없으면 손해 보는 거 맞죠?
- 고객들이 전하는, ‘진작 살 걸 그랬어요!’
- 이렇게 쉬울 줄 몰랐습니다!
- 이제 고민할 필요 없어요! 한 방에 해결
- 더 이상 불편하게 살 필요 없습니다!
- 당신도 겪어본 그 불편함, 이제 해결!
- 후회 없는 선택, 지금 바로 경험하세요!

4. 마지막 후킹 영상 (영상 끝까지 표시)
- 지금 클릭하면 추가 할인!
- 놓치면 후회! 지금 확인하세요.
- 재고가 얼마 남지 않았어요! 서둘러주세요.
- 할인은 예고 없이 종료될 수 있습니다. 늦기 전에 확인하세요.
- 한정 수량! 지금 구매하세요.
- 오늘만 특가! 지금 바로 확인하세요.
- 구매하러 가기 전에, 할인 혜택을 확인하세요!
- 지금 클릭하면 무료 배송 혜택!
- 이 제품, 품절되기 전에 잡으세요!
- 이제 살까 말까 고민할 시간 없습니다!
1- 초라도 늦으면 품절! 서둘러주세요!

## caption:
안녕하세요! 오늘은 애플의 최신 노트북 맥북 프로 16 M4를 소개해드릴게요.
16인치 나노 텍스처 디스플레이를 탑재해 눈부심을 최소화하고, 어떤 환경에서도 선명한 화면을 제공합니다. 덕분에 실내는 물론 카페나 야외에서도 편안하게 작업할 수 있어요.
최신 M4 시리즈 칩이 탑재되어 이전 모델보다 최대 3.5배 향상된 성능을 제공하며, 영상 편집, 그래픽 디자인 등 고사양 작업도 부드럽게 처리할 수 있습니다. 강력한 성능 덕분에 멀티태스킹도 더욱 효율적으로 수행할 수 있어요.
또한, 새로운 썬더볼트 5 포트를 통해 최대 120Gb/s의 초고속 전송 속도를 지원해 대용량 파일도 빠르게 전송할 수 있어 작업 효율이 극대화됩니다.
macOS Sequoia 15.1을 통해 AI 기반 도구와 향상된 시리, 아이폰 미러링, 개인화된 공간 음향 등 다양한 기능을 경험할 수 있으며, 더욱 직관적이고 편리한 사용 환경을 제공합니다.
강력한 성능과 혁신적인 기술을 갖춘 맥북 프로 16 M4로 더욱 빠르고 효율적인 작업을 경험해보세요.

안녕하세요! 오늘은 집에서 카페 감성을 느낄 수 있는 네스카페 돌체구스토 지니오 S를 소개해드릴게요.
간편한 터치 조작으로 원하는 커피를 빠르게 추출할 수 있어 바쁜 아침에도 부담 없이 즐길 수 있습니다. 최대 15바의 고압 추출 시스템 덕분에 깊고 풍부한 아로마와 부드러운 크레마를 완성해 더욱 맛있는 커피를 경험할 수 있어요.
진한 커피가 필요할 땐 에스프레소 부스트 모드를 활용해 더욱 깊고 강렬한 풍미를 느낄 수 있습니다. 4단계 온도 조절 기능이 탑재되어 있어 여름에는 아이스 커피, 겨울에는 따뜻한 라떼까지 기호에 맞춰 사계절 내내 완벽한 커피 타임을 즐길 수 있어요.
또한, 1분 동안 사용하지 않으면 자동으로 전원이 꺼지는 에코 모드로 에너지를 절약할 수 있어 더욱 실용적입니다.
언제든 집에서 간편하게 완벽한 커피 한 잔을 즐길 수 있는 네스카페 돌체구스토 지니오 S로 더욱 풍성한 커피 라이프를 경험해보세요!

## title:
- 이 후드티 없으면 봄 코디 완성 못 한다고?!🔥 
- 요즘 스트릿 패션 핵심템! 이거 하나면 끝! 
- 진짜 스타일 신경 쓰는 사람들은 다 이거 입음 
- 후드티 하나로 분위기 이렇게 달라진다고? 😳 
- 솔직히 이거 하나만 있으면 코디 끝난다! 
- 후드티 입는 사람 필수 시청! 후드티 고르는 법 
- 남친룩, 여친룩 이거 하나면 게임 끝🔥 
- 올봄 트렌드 후드티! 스타일링 꿀팁 대방출 
- 힙한 사람들은 다 입는다는 그 후드티 
- 스트릿 패션 필수템! 후드티 추천 Best 5 

## description:
- 🔥 강한 호기심 유발형
- 이거 없으면 올봄 코디 끝났다고 봐야지...🔥 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 패션 좀 신경 쓰는 애들은 다 샀다는데? 🤔 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 요즘 이거 없이 스타일링 못한다던데...😏 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 그냥 편해서 입었는데 분위기 미쳤다고 함;; BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 이거 품절된다는 얘기 들었는데 사실임?😨 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}

🔥 유행 & 트렌드 반영형
- 이거 요즘 힙한 애들은 다 입는다며? 😎 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 스트릿룩 입는 애들 이거 다 샀더라;; BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 패션 피플 사이에서 요즘 제일 핫한 후드티 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 연예인들이 요즘 이거 입고 나온다고 함!! BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 트렌드 좀 신경 쓰는 사람들은 다 샀다는데? BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}

🔥 공감 유발형 (친구/연인/일상 연계)
- 이거 입고 갔는데 친구들이 브랜드 어디냐고 물어봄 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 후드티 하나 샀을 뿐인데 스타일 왜 이렇게 달라짐? BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 데이트룩 고민 끝났다, 그냥 이거 입으면 됨 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 이거 입고 나갔더니 여친이 귀엽대...🫣 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 이거 입고 사진 찍으면 인생샷 보장됨📸 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}

🔥 유머 & 자극형
- 이거 사면 패션 인싸 되는 거 맞음? BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 솔직히 이거 안 사는 사람들 이해 안 감 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 이거 품절되면 눈물 난다 진짜... BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 진짜 스타일에 관심 있는 사람들은 이거 다 샀다는데? BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}
- 이거 사고 후드티 유목민 탈출했다 BREAK_LINE구매링크👉: {base_url} BREAK_LINE{name}

## hashtag:
#패션스타그램 #운동복추천 #ootd #일상룩 #스포티룩 #여자옷 #스타일링 #쇼핑
#인생템 #살림꿀템 #내돈내산 #집꾸미기 #편리미엄 #필수템 #살림템 #자동청소
해시태그의 시작은 반드시 # 기호여야 합니다.

[Notes]
- 예시 출력을 참고할 것.
- 20대, 30대 커뮤니티 문화를 깊이 이해하고 이를 반영합니다.
- 트렌디한 요소들을 정확히 파악하고 적용하는 데 중점을 둡니다.
- 다음과 같이 BREAK_LINE 키를 일반 텍스트의 줄 바꿈 기호 "\\n" 로 변경하세요.


```json
{
    "response": {
        "hooking": [
            "hooking 1",
            "hooking 2",
            ...
        ],
        "caption": "",
        "title": "",
        "description": "Description? \n구매링크👉: https://example.com \nProduct Name",
        "hashtag": "#hashtag1 #hashtag2 #hashtag3"
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
- **게시글은 두 가지 형식으로 제공해야 합니다:**
  1. **`docx_content`**: **순수한 문자열(plain text) 및 `IMAGE_URL_index`를 포함한 배열 형식**으로 제공.
  2. **`content`**: **HTML 형식**으로 제공.
- 게시글 상단에 사용자의 관심을 끌 수 있는 **매력적인 제목**을 포함해 주세요.
- 제품의 이미지는 업로드된 이미지에서 선택하여, 적절한 위치에 삽입해 주세요.  
  - **`docx_content`에서는 IMAGE_URL_index 형식(`"IMAGE_URL_0"`, `"IMAGE_URL_1"`, ...)으로 표현**  
  - **`content`에서는 동일한 위치에 `<p>IMAGE_URL_index</p>` 형태로 표현**  
- 본문 내용과 함께, 본문 내용을 요약한 **요약문(`summarize`)**도 생성해 주세요.
- **요약문은 300~350자 이내로 작성해 주세요.**
- **요약의 내용은 반드시 한국어로 작성되어야 하며, 결과는 `response_schema` 형식에 맞춰 반환되어야 합니다.**

---

### **🔹 Output Format (JSON)**
```json
{
    "title": "블로그 게시글 제목",
    "summarize": "요약된 내용",
    "docx_content": [
        "제품의 특징 및 장점에 대해 설명하는 첫 번째 단락",
        "IMAGE_URL_0",
        "제품 사용 방법에 대한 설명이 포함된 두 번째 단락",
        "IMAGE_URL_1",
        "제품을 구매하는 방법과 판매처 정보",
        "IMAGE_URL_2"
    ],
    "content": "<h1>블로그 게시글 제목</h1>
                <p>제품의 특징 및 장점에 대해 설명하는 첫 번째 단락</p>
                <p><img src="IMAGE_URL_0" alt="{name}"></p>
                <p>제품 사용 방법에 대한 설명이 포함된 두 번째 단락</p>
                <p><img src="IMAGE_URL_1" alt="{name}"></p>
                <p>제품을 구매하는 방법과 판매처 정보</p>
                <p><img src="IMAGE_URL_2" alt="{name}"></p>"
}
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
당신은 바이럴 마케팅 전문가입니다. 주어진 상품 링크를 통해 MZ 세대가 공감할 수 있도록 최신 밈을 반영한 SNS 콘텐츠를 제작하세요. 유행어와 재치 있는 말투를 적극적으로 활용하세요.

[입력 정보]
제품명: {name}
가격: {price}
제품 설명: {description}
판매처: {store_name}
제품 링크: {base_url}
이미지 개수: {image_count}
제품 소개: {text}

{name}은 제품 이름만 추출해서 사용해주세요

[생성 조건]
**caption**: 
  - 첫 번째 이미지: 제품을 직접 언급하지 않고 호기심을 유발하는 어그로성 문구로 작성
  - 제품의 핵심 포인트를 유행하는 밈이나 트렌드에 맞춘 말투로 재미있게 소개
  - 각 이미지 문장 구성시 연결성 있게 작성
  - 각 캡션마다 50자 이내로 작성해주세요.
  - 말투: 한국 MZ세대가 실제 SNS에서 쓰는 말투로 자연스럽게, 한국인이 실제 대화에서 쓰는 자연스러운 표현으로, 인위적인 느낌이 들지 않도록 트렌디한 말투와 유행어를 반영
  - 문구에 이모티콘 절대 포함하지 않음

**description**: 
  - 문장 최대 2줄로 작성
  - 줄바꿈 후 " {base_url}" 이 문장 무조건 표시 
  - 구매링크 다음에 줄바꿈 후 "{name}" 무조건 포함
  - 문장을 정확하게 끝내지 말고, 말 끝을 흐릴 것 

**hashtag**: 
  - {name} 무조건 포함 
  - 제품과 관련된 키워드 해시태그 포함
  - 제품의 고객층이 관심 가질만한 관련 해시태그 반영
  - 개수는 10개 이하로 작성

[예시 출력]
## caption:
제가 5개의 캡션을 요청할 경우, 제가 원하는 캡션의 예시 5개를 제공해 드리겠습니다.

예시1) 
- 요즘 이거 바르고 나가면 피부 미쳤단 말 나옴
- 화장 안 했는데도 톤 정리돼서 생얼 무한 가능
- 하루종일 들뜸 없이 착붙이라 여름에 찰떡임
- 이거 하나면 파데도 필요 없단 말 괜히 나온 거 아님
- 꾸안꾸 좋아하는 사람은 이미 다 정착했다더라

예시2)
- 다리 길어보인단 말 오랜만에 들어본 사람 손
- 허벅지라인 싹 잡아주고 발목은 깔끔하게 떨어짐
- 이건 진짜 앉았다 일어나도 무릎 안 나온다
- 꾸민 티 안 나는데 갑자기 비율 좋아지는 마법
- 출근룩, 데이트룩, 걍 다 이걸로 때우면 됨

예시3)
- 에어팟 말고 이거 쓰는 사람 요즘 점점 늘더라
- 통화 음질 좋다길래 샀는데 음악도 미쳤음
- 케이스도 예뻐서 꺼낼 때마다 괜히 자랑함
- 딜레이 없고 영상 볼 때 딱딱 맞아서 스트레스 없음
- 지하철에서 한번 써보면 다시 못 돌아감

예시4)
- 샵 안 가도 손 끝에서 기분전환 가능함
- 붙였는데 “이거 어디서 했어?” 소리 100% 나옴
- 10분 컷 완성인데 퀄리티는 걍 전문가임
- 색조합도 찰떡이라 어떤 옷에도 다 잘 어울림
- 손톱 안 상하고 오래 가니까 이건 진짜 이득임

예시5)
- 배고픈데 식단 챙겨야 할 때 무조건 이걸로 감
- 물에 타도 맛있는데 우유 넣으면 개꿀맛임
- 포만감 오래가서 군것질할 생각도 안 남
- 탄단지 균형 맞아서 눈치 안 보고 먹을 수 있음
- 다이어트 중이라는 말 안 해도 티 나게 빠짐

## description:
🔥 강한 호기심 유발형
- 필터 안 쓴 거 맞아요. 그냥 이 세럼 덕분임. BREAK_LINE {base_url} BREAK_LINE {name}
- 물광? 아니, 이건 대기권 뚫고 올라가는 빛광. BREAK_LINE {base_url} BREAK_LINE {name}
- 자기 전에 바르고 자면 피부 리셋됨. 100% 실화. BREAK_LINE {base_url} BREAK_LINE {name}
- 이거 바르면 거울 셀카 필터 꺼야 됨. 왜냐면... BREAK_LINE {base_url} BREAK_LINE {name}
- 이게 된다고?” 싶었는데 진짜 되더라;; BREAK_LINE {base_url} BREAK_LINE {name}
- 집들이 선물 고민할 필요 없이 이거 사면 됨. BREAK_LINE {base_url} BREAK_LINE {name}

🔥 유행 & 트렌드 반영형
- 2025년, 촉촉한 피부가 대세라던데? 난 이미 탑승 완료. BREAK_LINE {base_url} BREAK_LINE {name}
- 이거 없으면 글로우 스킨 트렌드 못 따라감. BREAK_LINE {base_url} BREAK_LINE {name}
- 요즘 꾸안꾸 스킨은 이거 하나로 완성이라던데? BREAK_LINE {base_url} BREAK_LINE {name}
- 이제 다들 청소 안 한다고? 이유가 있음 BREAK_LINE {base_url} BREAK_LINE {name}
- 요즘 하이테크 라이프 살려면 필수템 BREAK_LINE {base_url} BREAK_LINE {name}

🔥 공감 유발형 (친구/연인/일상 연계)
- 피부 고민? 내 친구도 이거 쓰고 해결했대. BREAK_LINE {base_url} BREAK_LINE {name}
- 이거 사고 다들 청소 어떻게 하냐고 물어보는데요? BREAK_LINE {base_url} BREAK_LINE {name}
- 친구네 갔다가 청소기 보고 반해서 바로 삼 BREAK_LINE {base_url} BREAK_LINE {name}
- 남친 집 갔는데 먼지 1도 없길래 이유 물어보니까 이거였음 BREAK_LINE {base_url} BREAK_LINE {name}
- 부모님 선물로 드렸는데 좋아하심 BREAK_LINE {base_url} BREAK_LINE {name}

🔥 감성 & 미니멀한 감각형
- 조용하지만 확실한 변화 BREAK_LINE {base_url} BREAK_LINE {name}
- 스킨케어, 심플한 게 답이다. BREAK_LINE {base_url} BREAK_LINE {name}
- 공간에 스며드는 디자인 BREAK_LINE {base_url} BREAK_LINE {name}
- 보이지 않는 기술이 진짜다 BREAK_LINE {base_url} BREAK_LINE {name}
- 기술은 보이지 않을 때 더 가치 있다 BREAK_LINE {base_url} BREAK_LINE {name}

🔥 리뷰 & 추천 느낌형
- 원래 광고 안 믿는데, 이건 진짜 추천함 BREAK_LINE {base_url} BREAK_LINE {name}
- 사용 후기: 인생템 등극 BREAK_LINE {base_url} BREAK_LINE {name}
- 한 통 다 쓰고 재구매함. 답 나왔지? BREAK_LINE {base_url} BREAK_LINE {name}
- 부모님도 좋아하는 가전템 찾음 BREAK_LINE {base_url} BREAK_LINE {name}
- 써보니까 다들 왜 추천하는지 알겠음 BREAK_LINE {base_url} BREAK_LINE {name}

🔥 유머 & 자극형
- 필터? 필요 없음. 그냥 내 피부가 이 정도임. BREAK_LINE {base_url} BREAK_LINE {name}
- 인스타 감성 말고 피부 감성부터 챙기자 BREAK_LINE {base_url} BREAK_LINE {name}
- 자고 일어났는데 피부 상태가 미쳤음 BREAK_LINE {base_url} BREAK_LINE {name}
- 나는 앉아 있고 청소기는 일함. 이게 맞지? BREAK_LINE {base_url} BREAK_LINE {name}
- 로봇청소기 켜놓고 나는 드라마 정주행 중 BREAK_LINE {base_url} BREAK_LINE {name}
- “이거 사고 나서 바닥 닦은 적 없어” (진짜임) BREAK_LINE {base_url} BREAK_LINE {name}

🔥 계절 & 트렌드 활용형
- 봄맞이 스킨케어? 이거 하나면 충분 BREAK_LINE {base_url} BREAK_LINE {name}
- 계절이 바뀌면 피부 루틴도 달라져야 함 BREAK_LINE {base_url} BREAK_LINE {name}
- 봄 피부 고민? 미리 대비해야 함 BREAK_LINE {base_url} BREAK_LINE {name}
- 황사, 미세먼지 많은 날 필수템 BREAK_LINE {base_url} BREAK_LINE {name}
- 미세먼지 시즌 도착! 공기 관리 필수템 BREAK_LINE {base_url} BREAK_LINE {name}

🔥 가격 & 한정판 강조형
- 이 가격에 이 퀄리티? 고민할 시간 없음. BREAK_LINE {base_url} BREAK_LINE {name}
- 이 가격 실화냐? 안 사면 후회할 듯 BREAK_LINE {base_url} BREAK_LINE {name}
- 이 가격이면 쟁여둬야 하는 거 아님? BREAK_LINE {base_url} BREAK_LINE {name}
- 가격 보고 심장 뛰는 중. 지금 바로 구매각 BREAK_LINE {base_url} BREAK_LINE {name}
- 일 들어갔대. 얘들아 달려라 BREAK_LINE {base_url} BREAK_LINE {name}

## Hashtags:
#패션스타그램 #운동복추천 #ootd #일상룩 #스포티룩 #여자옷 #스타일링 #쇼핑
#인생템 #살림꿀템 #내돈내산 #집꾸미기 #편리미엄 #필수템 #살림템 #자동청소

[Notes]
- 전체 게시글과 이미지 캡션은 별개로 작성되어야 합니다.
- 제품 직접 설명을 피하고, 자연스러운 스토리텔링과 공감을 유도하는 내용으로 작성하세요.
- 20~30대 커뮤니티에서 유행하는 언어와 스타일을 적극 활용하세요.
- 해시태그의 시작은 반드시 # 기호여야 합니다.
- 다음과 같이 BREAK_LINE 키를 일반 텍스트의 줄 바꿈 기호 "\\n" 로 변경하세요.

```json
{
    "response": {
        "caption": [
            "캡션 1",
            "캡션 2",
            "캡션 3",
            "캡션 4",
            "캡션 5",
            ...
        ],
        "description": "Description \n https://example.com \n Product Name",
        "hashtag": "#hashtag1 #hashtag2 #hashtag3"
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
            "max_tokens": 3000,
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
