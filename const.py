# Pagination Defaults
from app.enums.voices import Voices


DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100

DRAFT_STATUS = 99
UPLOADED = 1
UPLOADED_FALSE = 2
ADMIN = 1
USER = 0
DATE_EXPIRED = 30
TYPE_NORMAL = 1
TYPE_PRO = 2
NOTIFICATION_FALSE = 0
NOTIFICATION_SUCCESS = 1
NAVER_LINK_BLOG = 7
MAX_SNS = 7

REDIS_EXPIRE_TIME = 60 * 60 * 2

EFFECTS_CONST = [
    "zoomIn",
    "zoomOut",
    "slideLeft",
    "slideRight",
    "slideUp",
    "slideDown",
]

KOREAN_VOICES = [
    {
        "index": 1,
        "type": "Standard",
        "name": "ko-KR-Standard-C",
        "ssmlGender": "MALE",
    },
    {
        "index": 2,
        "type": "Standard",
        "name": "ko-KR-Standard-D",
        "ssmlGender": "MALE",
    },
    {
        "index": 3,
        "type": "Standard",
        "name": "ko-KR-Standard-A",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 4,
        "type": "Standard",
        "name": "ko-KR-Standard-B",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 5,
        "type": "Premium",
        "name": "ko-KR-Chirp3-HD-Aoede",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 6,
        "type": "Premium",
        "name": "ko-KR-Chirp3-HD-Charon",
        "ssmlGender": "MALE",
    },
    {
        "index": 7,
        "type": "Premium",
        "name": "ko-KR-Chirp3-HD-Fenrir",
        "ssmlGender": "MALE",
    },
    {
        "index": 8,
        "type": "Premium",
        "name": "ko-KR-Chirp3-HD-Kore",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 9,
        "type": "Premium",
        "name": "ko-KR-Chirp3-HD-Leda",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 10,
        "type": "Premium",
        "name": "ko-KR-Chirp3-HD-Orus",
        "ssmlGender": "MALE",
    },
    {
        "index": 11,
        "type": "Premium",
        "name": "ko-KR-Chirp3-HD-Puck",
        "ssmlGender": "MALE",
    },
    {
        "index": 12,
        "type": "Premium",
        "name": "ko-KR-Chirp3-HD-Zephyr",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 13,
        "type": "Premium",
        "name": "ko-KR-Neural2-A",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 14,
        "type": "Premium",
        "name": "ko-KR-Neural2-B",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 15,
        "type": "Premium",
        "name": "ko-KR-Neural2-C",
        "ssmlGender": "MALE",
    },
    {
        "index": 16,
        "type": "Premium",
        "name": "ko-KR-Wavenet-A",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 17,
        "type": "Premium",
        "name": "ko-KR-Wavenet-B",
        "ssmlGender": "FEMALE",
    },
    {
        "index": 18,
        "type": "Premium",
        "name": "ko-KR-Wavenet-C",
        "ssmlGender": "MALE",
    },
    {
        "index": 19,
        "type": "Premium",
        "name": "ko-KR-Wavenet-D",
        "ssmlGender": "MALE",
    },
]

LIMIT_BATCH = {
    "FREE": 10,
    "BASIC": 30,
    "STANDARD": 30,
    "PRO": 300,
    "BUSINESS": 1000,
    "ENTERPRISE": 10000,
}


ALLOWED_IPS = {"218.154.54.97"}

BASIC_DURATION_DAYS = 30
MAX_ADDON_PER_BASIC = 2
PACKAGE_CONFIG = {
    "BASIC": {
        "pack_name": "베이직 플랜",
        "pack_description": "SNS 홍보를 처음 시작하는 분",
        "order_index": 1,
        "total_create": 30,
        "price_origin": 29900,
        "price": 5900,
        "total_link": 1,
        "batch_total": 30,
        "batch_remain": 30,
        "batch_sns_total": 1,
        "total_link_active": 1,
        "addon": {
            "EXTRA_CHANNEL": {
                "price": 2500,
                "name": "채널 추가 Addon",
                "max_per_basic": 2,
            },
        },
    },
    "INVITE_BASIC": {
        "pack_name": "초대하기 보상",
        "pack_description": "SNS 홍보를 처음 시작하는 분",
        "order_index": 1,
        "total_create": 30,
        "price_origin": 29900,
        "price": 5900,
        "total_link": 1,
        "batch_total": 7,
        "batch_remain": 7,
        "batch_sns_total": 1,
        "total_link_active": 1,
    },
    "STANDARD": {
        "pack_name": "스탠다드 플랜",
        "pack_description": "SNS를 더 빠르게 성장시키고 싶은 분",
        "order_index": 2,
        "total_create": 60,
        "price_origin": 89000,
        "price": 29900,
        "total_link": 7,
        "batch_total": 60,
        "batch_remain": 60,
        "batch_sns_total": 7,
        "total_link_active": 7,
    },
    "BUSINESS": {
        "pack_name": "기업형 스탠다드 플랜",
        "pack_description": "브랜드, 플랫폼, 에이전시 고객을 위한 플랜",
        "order_index": 3,
        "total_create": 30,
        "price": 899000,
        "price_origin": 899000,
        "total_link": 7,
        "batch_total": 30,
        "batch_remain": 30,
        "batch_sns_total": 7,
        "total_link_active": 7,
    },
}


PACKAGE_DURATION_DAYS = 30

MAX_REFERRAL_USAGE = 13


POST_PROCESSING_STATUS = {
    "PENDING": "PENDING",
    "PROCESSING": "PROCESSING",
    "COMPLETED": "COMPLETED",
    "FAILED": "FAILED",
}


SETUP_VOICES = [
    {
        "id": "3",
        "name": "친절한 상담원",
        "name_en": "Standard-A",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Standard-A.wav",
        "gender": Voices.FEMALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "4",
        "name": "다큐 내레이션 성우",
        "name_en": "Standard-B",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Standard-B.wav",
        "gender": Voices.FEMALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "13",
        "name": "AI 비서",
        "name_en": "Neural2-A",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Neural2-A.wav",
        "gender": Voices.FEMALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "14",
        "name": "광고 내레이션 성우",
        "name_en": "Neural2-B",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Neural2-B.wav",
        "gender": Voices.FEMALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "16",
        "name": "유치원 선생님",
        "name_en": "Wavenet-A",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Wavenet-A.wav",
        "gender": Voices.FEMALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "17",
        "name": "뉴스 앵커",
        "name_en": "Wavenet-B",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Wavenet-B.wav",
        "gender": Voices.FEMALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "1",
        "name": "금융 크리에이터",
        "name_en": "Standard-C",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Standard-C.wav",
        "gender": Voices.MALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "2",
        "name": "라디오 DJ",
        "name_en": "Standard-D",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Standard-D.wav",
        "gender": Voices.MALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "15",
        "name": "비즈니스 발표자",
        "name_en": "Neural2-C",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Neural2-C.wav",
        "gender": Voices.MALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "18",
        "name": "전문 강사",
        "name_en": "Wavenet-C",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Wavenet-C.wav",
        "gender": Voices.MALE.value,
        "type": Voices.GOOGLE.value,
    },
    {
        "id": "19",
        "name": "경제 크리에이터",
        "name_en": "Wavenet-D",
        "audio_url": "http://apitoktak.voda-play.com/voice/audio/music/ko-KR-Wavenet-D.wav",
        "gender": Voices.MALE.value,
        "type": Voices.GOOGLE.value,
    },
]
