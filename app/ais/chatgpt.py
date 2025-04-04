import json
import time
from openai import OpenAI
from app.services.request_log import RequestLogService
import os

chatgpt_api_key = os.environ.get("CHATGPT_API_KEY") or ""


def call_chatgpt_create_caption(images=[], data={}, post_id=0):

    prompt = """업로드된 이미지를 참고하여 제품을 홍보하는 숏폼(Shorts, TikTok) 스타일의 영상 콘텐츠를 제작하도록 지원해 드립니다.

[역할]
당신은 20~30대 커뮤니티에서 유행하는 언어를 활용하는 애플의 바이럴 마케터입니다. 상품을 홍보하는 영상을 만드는 작업을 진행할 예정입니다. FOMO, 사회적 증가, 공감과 감성 자극, 첫 3초의 법칙, 자이가르닉 효과 등 적절한 심리학 기법을 상황에 맞게 사용하여 스크립트를 작성하세요.

[입력 정보]
- 제품명: {name}
- 가격: {price}
- 제품 설명: {description}
- 판매처: {store_name}
- 제품 링크: {base_url}
- 제품 소개: {text}

[생성 조건]

- hooking: 
  - 총 4개의 문장을 생성하며, 각 문장은 20자 이내로 작성해야 합니다.
  - 이 문장들은 영상 흐름에 따라 시점별 자막으로 사용되며, 다음 순서대로 분배됩니다:
1. (영상 시작 시) 진짜 속눈썹 바뀌나요?
2. (첫 번째 이미지) 2주 만에 바뀐 후기들
3. (세 번째 이미지) 길고 풍성한 변화 직접 확인
4. (마무리) 이 기회 놓치면 후회해요
  - 각 문장은 상품과 관련된 내용으로 작성하며, 호기심 유발, 공감, 궁금증 유도, 클릭 유도 등의 목적을 달성할 수 있도록 작성해야 합니다.

  - 다음은 hooking 문장 생성 시 참고해야 할 예시 리스트입니다. 문장 구성, 어조, 길이, 심리적 효과 등을 참고하여 유사한 스타일로 작성하세요.

  [hooking 예시 출력]
  - 진짜 속눈썹 바뀌나요?
  - 이거 쓰고 눈매 달라졌어요
  - 속눈썹 고민? 여기서 끝나요
  - 2주 만에 바뀐 후기들
  - 붙이는 시대는 끝났어요
  - 뷰러 안 써도 된다고요?
  - 길고 풍성한 변화 직접 확인
  - 사용 전후 차이 극명해요
  - 후기 보면 진짜 놀라요
  - 이 기회 놓치면 후회해요
  - 지금 써봐야 아는 이유
  - 지금, 달라지는 순간입니다

- caption:
  - 공백을 포함하여 최소 750자로 "caption"을 작성해 주세요.
  - 스토리텔링 형식으로 작성
  - 다음 항목 중 최소 2가지 포함:
    - 제품 사용 후의 감정 또는 일상 변화
    - 기능적 장점 또는 차별성
    - 사회적 증거(유명 리뷰, 재구매율 등)
    - 망설이는 소비자 심리 설득 요소
  - 실제 사람이 쓴 것 같은 자연스러운 말투
  - 문장은 반드시 온전하게 끝맺고, 감탄사 단독/말줄임표/이모티콘 금지
  - "[예시 출력]의 ##caption" 스타일 참고

- title:
  - 유튜브 제목 스타일
  - 감정적/자극적/트렌디한 표현 활용
  - 클릭을 유도할 수 있는 문장 구성

- description:
  - 2줄 구성
    - 첫 줄: 문장을 일부러 끝까지 쓰지 않고 말끝 흐리기
    - 둘째 줄: 고정 형식  
      `"구매링크👉: {base_url} \n{name}"`

- hashtag:
  - {name}을 포함한 총 10~15개 해시태그를 한 줄 문자열로 작성하세요.  
  - 중복 키워드는 2개 이하
  - 반드시 `#`으로 시작하며, 실사용자가 검색할 법한 키워드 위주로 작성하세요.
  - 캡션과는 구분된 별도 항목으로 제공하세요.  
  - 해시태그는 인스타그램 SNS 바이럴마케팅 적인 부분에서 실제로 사용되는 검색 키워드를 기반으로 구성해야 합니다.
  - 문장형 해시태그, 밈 해시태그, 지나치게 긴 태그는 금지합니다.
    - 예: #길고풍성한속눈썹 X / #이거써보면알아요 X
  - 해시태그는 검색 최적화(Search Optimization)를 고려하여 단순하고 직관적으로 구성되어야 하며, 
    ‘쇼핑몰에서 검색했을 때 걸릴 수 있는 단어인가’를 기준으로 판단합니다.

[문장 스타일 가이드]
- 모든 문장은 주어+서술어 포함한 완전한 문장
- 감탄사, 밈 단독 문장 금지 (예: “바로겟!”, “실물영접!” X)
- 이모티콘 사용 금지
- 문장 말미는 자연스러운 종결 어미로 마무리 (예: ~돼요, ~입니다)
- 말줄임표(...)는 오직 description 첫 줄에서만 허용
- caption은 문장이 명확히 끝나야 하며, 흐리는 말투 금지한다.

[기타 가이드라인]
- 출력은 순수 텍스트만, Markdown 및 특수문자 사용 금지
- BREAK_LINE은 실제 줄바꿈 기호 `\\n`으로 처리
- AI 표현체 금지 (예: “~로 알려져 있습니다” → “직접 써보면 느껴져요” 식으로 대체)
- 공백을 포함하여 최소 750자로 "caption"을 작성해 주세요.

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
        "description": "Description? \n구매링크👉: https://example.com \nProduct Name",
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
                <p><img src="IMAGE_URL_2" alt="{name}"></p>...etc"
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
당신은 바이럴 마케팅 베테랑 전문가입니다.  
주어진 상품 링크를 기반으로, MZ세대가 공감할 수 있도록 최신 밈과 감성, 대화체를 반영한 SNS 콘텐츠를 제작하세요.  
실제 인스타그램에 업로드된 이미지형 콘텐츠처럼, 유행어와 자연스러운 말투를 활용하여 실제 사람의 손길이 느껴지는 콘텐츠로 작성합니다.  

[입력 정보]  
제품명: {name}  
가격: {price}  
제품 설명: {description}  
판매처: {store_name}  
제품 링크: {base_url}  
이미지 개수: {image_count}  
제품 소개: {text}  

{name}은 제품명만 추출해 자연스럽게 사용하세요.  

[생성 조건]  

caption:  
- 총 {image_count}개의 이미지에 대응하는 캡션을 생성합니다.  
- 실제 사용자가 SNS에 쓰는 것처럼 자연스럽고 감정이 담긴 문장으로 작성하세요.  
- 이모티콘은 사용하지 않습니다.  

- 아래 흐름을 반드시 따르세요:  
  1. [1번 이미지]  
    - 제품명 또는 브랜드명을 절대 언급하지 마세요.  
    - 스크롤을 멈추게 하는 문장으로 작성하고, 4줄 이하 / 글자 수 32자 이하 조건을 모두 충족해야 합니다.  
    - 하나라도 초과하면 출력 실패로 간주합니다.  
    - 강한 궁금증 유발 + 도파민 자극 티저형 문구로 작성하세요.  
  2. [2번 이미지] 공감되는 일상, 감정, 문제 상황 표현, 띄어쓰기 포함 글자 수 100자 이상 120자 이하의 완전한 문장으로 작성해야 합니다.  
  3. [3번 이미지] 변화의 시작, 제품이 작용하는 느낌, 띄어쓰기 포함 글자 수 100자 이상 120자 이하의 완전한 문장으로 작성해야 합니다.  
  4. [4번 이미지] 확신을 주는 변화, 감정적/시각적 임팩트, 띄어쓰기 포함 글자 수 100자 이상 120자 이하의 완전한 문장으로 작성해야 합니다.   
  5. [마지막 이미지] 감성적인 마무리 혹은 제품 요약 (이때만 제품명 언급 가능), 띄어쓰기 포함 글자 수 100자 이상 120자 이하의 완전한 문장으로 작성해야 합니다.   

description:  
- 총 3줄 구성  
  - 첫 줄: 감성적이고 간접적인 제품 강조, 말끝 흐리는 느낌 포함  
  - 두 번째 줄: 링크 단독 출력 (예: https://example.com)  
  - 세 번째 줄: 제품명 단독 출력  

hashtag:  
- {name}을 포함한 총 10~15개 해시태그를 한 줄 문자열로 작성하세요.  
- 중복 키워드는 2개 이하
- 반드시 `#`으로 시작하며, 실사용자가 검색할 법한 키워드 위주로 작성하세요.
- 캡션과는 구분된 별도 항목으로 제공하세요.  

[출력 형식 예시]
```json
{
  "response": {
    "caption": [
      "이 향 뭐야?”라는 말 처음 들었음",
      "잔향이 남아서 그런지 자꾸 생각나",
      "진하지 않은데 존재감 확실해",
      "나도 몰랐던 분위기 생기는 중",
      "이거 뿌리면 나도 좀 달라지는 듯"
    ],
    "description": "향은 결국 나를 설명하는 방식이더라고… 너도 느껴봐!\\nhttps://example.com\\n시그니처 퍼퓸 오 드 뚜왈렛",
    "hashtag": "#향수 #은은한향기 #데일리향수 #남자향수 #여자향수 #인생향수 #바이럴향수 #시그니처향 #분위기템 #꾸안꾸 #감성템 #퍼퓸추천 #향기템 #센슈얼향수 #나만아는향"
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
