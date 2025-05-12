from app.models.user import User
from app.models.referral_history import ReferralHistory
import const


class ReferralService:

    @staticmethod
    def use_referral_code(referral_code, login_user) -> dict:
        user = User.query.filter_by(referral_code=referral_code).first()
        if not user:
            return False

        usage_count = ReferralHistory.query.filter_by(referrer_user_id=user.id).count()

        if usage_count >= const.MAX_REFERRAL_USAGE:
            return False

        # Lưu lịch sử
        history = ReferralHistory(
            referrer_user_id=user.id,
            referred_user_id=login_user.id,
            referral_code=referral_code,
        )
        history.save()
        return True

    @staticmethod
    def update_nice(id, *args, **kwargs):
        usage_user = ReferralHistory.query.filter_by(referred_user_id=id)
        if not usage_user:
            return None
        usage_user.update(**kwargs)
        return usage_user
