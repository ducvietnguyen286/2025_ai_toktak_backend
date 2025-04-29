from enum import Enum


class MessageSuccess(Enum):
    CREATE_BATCH = "제품 정보를 성공적으로 가져왔습니다."
    CREATE_POST_VIDEO = "비디오 생성이 성공적으로 완료되었습니다."
    CREATE_POST_IMAGE = "🖼 이미지 생성이 완료되었습니다."
    CREATE_POST_BLOG = "✍️ 블로그 콘텐츠가 생성되었습니다."


class MessageError(Enum):

    REQUIRED_COUPON = {
        "message": "⚠️ 쿠폰 등록 후 이용 할 수 있어요!",
        "error_message": "🎟️ 참여 방법은 도매꾹 홈페이지 톡탁 이벤트를 확인하세요. 😊",
    }

    NO_BATCH_REMAINING = {
        "message": "⚠️ 콘텐츠 생성 한도를 초과했어요!",
        "error_message": "🚫 더 이상 콘텐츠를 생성할 수 없습니다.",
    }

    WAIT_TOMORROW = {
        "message": "📌 무료 체험은 하루 1개만 생성할 수 있어요.",
        "error_message": "⏳ 내일 다시 시도해 주세요. 더 많은 콘텐츠가</br>필요하다면 유료 플랜을 확인해 보세요! 😊",
    }

    WAIT_RE_LOGIN = {
        "message": "⚠️ 현재는 재가입할 수 없어요!",
        "error_message": "🚫 탈퇴하신 계정은 30일간 재가입하실 수 없습니다.",
    }

    INVALID_URL = {
        "message": "⚠️ 잘못된 URL이에요!",
        "error_message": "ℹ️ 도매꾹, 쿠팡, 알리의 상품 URL을 사용해주세요. 😊",
    }

    NO_ANALYZE_URL = {
        "message": "⚠️ 상품 정보를 가져오는 데 문제가 생겼어요!",
        "error_message": "🔄 잠시 후 다시 시도해 주세요. 빠르게 해결할게요! 😊",
    }

    REQUIRE_LINK = {
        "message": "아직 SNS 연결 전이에요😢</br>지금 계정 연동하고 업로드 해보세요!",
        "error_message": "설정에서 SNS 계정을 먼저 연결해 주세요. 😊",
    }

    REQUIRE_LINK = {
        "message": "아직 SNS 연결 전이에요😢</br>지금 계정 연동하고 업로드 해보세요!",
        "error_message": "설정에서 SNS 계정을 먼저 연결해 주세요. 😊",
    }

    CANT_CONNECT_SNS = {
        "message": "⚠️ 계정 연결에 실패했습니다!",
        "error_message": "SNS 계정 정보를 확인해주세요😢",
    }

    NO_ACCESS_TOKEN_X = {
        "message": "🔒 X의 액세스 토큰이 만료됐어요!",
        "error_message": "🔗다시 연결해 주세요. 😊",
    }

    CHECK_CREATE_POST_VIDEO = {
        "message": "⚠️ 비디오 생성에 실패했습니다.",
        "error_message": "⏳ 잠시 후 다시 시도해 주세요. 😊",
    }

    CHECK_CREATE_POST_IMAGE = {
        "message": "⚠️ 비디오 생성에 실패했습니다.",
        "error_message": "⏳ 잠시 후 다시 시도해 주세요. 😊",
    }

    CREATE_POST_VIDEO = "비디오 생성이 성공적으로 완료되었습니다."
    CREATE_POST_IMAGE = "⚠️ 이미지 생성에 실패했습니다. 다시 시도해주세요."
    CREATE_POST_BLOG = "⚠️ 블로그 생성에 실패했습니다. 다시 시도해주세요."
