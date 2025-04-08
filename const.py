# Pagination Defaults
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100

DRAFT_STATUS = 99
UPLOADED = 1
ADMIN = 1
USER = 0
DATE_EXPIRED = 30
TYPE_NORMAL = 1
TYPE_PRO = 2

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
    "FREE": 20,
    "STANDARD": 30,
    "PRO": 300,
    "BUSINESS": 1000,
    "ENTERPRISE": 10000,
}
