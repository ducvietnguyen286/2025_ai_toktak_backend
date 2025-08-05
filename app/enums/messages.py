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
        "error_message_en": "🎟️ Please check the Toktak event on the Domeggook website for participation instructions. 😊",
    }

    REQUIRED_BILLING = {
        "message": "⚠️ 플랜 구매 후 이용 할 수 있어요!",
        "error_message": "🎟️ 요금제 메뉴를 확인하세요. 😊",
        "error_message_en": "🎟️ Please check the plan . 😊",
    }

    NO_BATCH_REMAINING = {
        "message": "⚠️ 콘텐츠 생성 한도를 초과했어요!",
        "error_message": "🚫 더 이상 콘텐츠를 생성할 수 없습니다.",
        "error_message_en": "🚫 You can no longer create content.",
    }

    WAIT_TOMORROW = {
        "message": "📌 무료 체험은 하루 1개만 생성할 수 있어요.",
        "error_message": "⏳ 내일 다시 시도해 주세요. 더 많은 콘텐츠가</br>필요하다면 유료 플랜을 확인해 보세요! 😊",
        "error_message_en": "⏳ Please try again tomorrow. If you need more content, consider a paid plan. 😊",
    }

    WAIT_RE_LOGIN = {
        "message": "⚠️ 현재는 재가입할 수 없어요!",
        "error_message": "🚫 탈퇴하신 계정은 30일간 재가입하실 수 없습니다.",
        "error_message_en": "🚫 Deleted accounts cannot re-register for 30 days.",
    }

    INVALID_URL = {
        "message": "⚠️ 잘못된 URL이에요!",
        "error_message": "ℹ️ 도매꾹, 쿠팡, 알리의 상품 URL을 사용해주세요. 😊",
        "error_message_en": "ℹ️ Please use product URLs from Domeggook, Coupang, or AliExpress. 😊",
    }

    NO_ANALYZE_URL = {
        "message": "⚠️ 상품 정보를 가져오는 데 문제가 생겼어요!",
        "error_message": "🔄 잠시 후 다시 시도해 주세요. 빠르게 해결할게요! 😊",
        "error_message_en": "🔄 Please try again shortly. We’ll fix it quickly! 😊",
    }

    REQUIRE_LINK = {
        "message": "아직 SNS 연결 전이에요😢</br>지금 계정 연동하고 업로드 해보세요!",
        "error_message": "설정에서 SNS 계정을 먼저 연결해 주세요. 😊",
        "error_message_en": "Please link your SNS account first in the settings. 😊",
    }

    CANT_CONNECT_SNS = {
        "message": "⚠️ 계정 연결에 실패했습니다!",
        "error_message": "SNS 계정 정보를 확인해주세요😢",
        "error_message_en": "Please check your SNS account information. 😢",
    }

    NO_ACCESS_TOKEN_X = {
        "message": "🔒 X의 액세스 토큰이 만료됐어요!",
        "error_message": "🔗다시 연결해 주세요. 😊",
        "error_message_en": "🔗 Please reconnect your X account. 😊",
    }

    CHECK_CREATE_POST_VIDEO = {
        "message": "⚠️ 비디오 생성에 실패했습니다.",
        "error_message": "⏳ 잠시 후 다시 시도해 주세요. 😊",
        "error_message_en": "⏳ Please try again shortly. 😊",
    }

    CHECK_CREATE_POST_IMAGE = {
        "message": "⚠️ 비디오 생성에 실패했습니다.",
        "error_message": "⏳ 잠시 후 다시 시도해 주세요. 😊",
        "error_message_en": "⏳ Please try again shortly. 😊",
    }

    CREATE_POST_VIDEO = "⚠️ 동영상 생성에 실패했습니다. 다시 시도해주세요."
    CREATE_POST_IMAGE = "⚠️ 이미지 생성에 실패했습니다. 다시 시도해주세요."
    CREATE_POST_BLOG = "⚠️ 블로그 생성에 실패했습니다. 다시 시도해주세요."


class message_payment(Enum):
    CHECK_BUY_PAYMENT = {
        "message": "이미 {package_name} 요금제에 대한 구매 이력이 있습니다.",
        "error_message": "이미 {package_name} 요금제에 대한 구매 이력이 있습니다.",
        "error_message_en": "You already have a previous purchase order for the {package_name} package.",
    }

    CHECK_UPGRADE_PAYMENT = {
        "error_message": "{old_package_name}에서 {package_name}(으)로 하향 변경할 수 없습니다.",
        "error_message_en": "You cannot downgrade from {old_package_name} to {package_name}.",
    }

    CHECK_EXITS_REFUND_PAYMENT = {
        "error_message": "이 거래에 대해 이미 환불 요청이 접수되었습니다.",
        "error_message_en": "A refund request has already been made for this transaction.",
    }

    CREATE_REFUND_PAYMENT = {
        "error_message": "환불 요청이 처리되었습니다.",
        "error_message_en": "The refund request has been processed.",
    }
    
    CREATE_FAIL_REFUND_PAYMENT = {
        "error_message": "환불 요청이 처리되었습니다.",
        "error_message_en": "The refund request has been processed.",
    }

    def format(self, **kwargs):
        return {
            key: val.format(**kwargs) if isinstance(val, str) else val
            for key, val in self.value.items()
        }
