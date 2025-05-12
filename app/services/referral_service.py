from consts import MAX_REFERRAL_USAGE

from app.models.user import User

class ReferralService:

    @staticmethod
    def use_referral_code(current_user: User, referral_code: str) -> dict:
        if current_user.id == referral_code:
            return {"success": False, "message": "자기 추천 코드는 사용할 수 없습니다."}

        # Tìm người giới thiệu
        referrer = User.query.filter_by(referral_code=referral_code).first()
        if not referrer:
            return {"success": False, "message": "유효하지 않은 추천 코드입니다."}

        # Kiểm tra số lần đã được nhập mã
        usage_count = ReferralHistory.query.filter_by(referrer_id=referrer.id).count()
        if usage_count >= MAX_REFERRAL_USAGE:
            return {"success": False, "message": "해당 추천 코드는 더 이상 사용할 수 없습니다."}

        # Kiểm tra người dùng đã từng nhập chưa
        existing = ReferralHistory.query.filter_by(referred_user_id=current_user.id).first()
        if existing:
            return {"success": False, "message": "이미 추천 코드를 사용하였습니다."}

        # Lưu lịch sử
        history = ReferralHistory(
            referrer_id=referrer.id,
            referred_user_id=current_user.id,
        )
        db.session.add(history)
        db.session.commit()

        return {"success": True, "message": "추천 코드가 성공적으로 적용되었습니다."}
