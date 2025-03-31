import datetime
import hashlib
from app.models.coupon import Coupon
from app.models.coupon_code import CouponCode
import random
import string
from app.extensions import redis_client, db


class CouponService:

    @staticmethod
    def create_coupon(*args, **kwargs):
        coupon = Coupon(*args, **kwargs)
        coupon.save()
        return coupon

    @staticmethod
    def find_coupon(id):
        return Coupon.query.get(id)

    @staticmethod
    def find_coupon_by_code(code):
        coupon_code = CouponCode.query.where(CouponCode.code == code).first()
        if not coupon_code:
            return "not_exist"
        if coupon_code.is_used:
            return "used"
        if not coupon_code.is_active:
            return "not_active"
        return Coupon.query.where(Coupon.id == coupon_code.coupon_id).first()

    @staticmethod
    def find_coupon_code(code):
        return CouponCode.query.where(Coupon.code == code).first()

    @staticmethod
    def get_coupons():
        coupons = Coupon.query.where(Coupon.status == 1).all()
        return [coupon._to_json() for coupon in coupons]

    @staticmethod
    def create_codes(coupon_id, count_code=100):
        coupon_codes = []
        code_by_day = CouponService.get_code_by_day()
        code_by_month = CouponService.get_code_by_month()
        code_by_year = CouponService.get_code_by_year()
        inserted_codes = set()
        for _ in range(count_code):
            code = CouponService.generate_code()
            code = f"{code_by_year}{code_by_month}{code_by_day}{code}"
            if code in inserted_codes:
                continue
            inserted_codes.add(code)
            coupon_codes.append(
                {
                    "coupon_id": coupon_id,
                    "code": code,
                    "is_used": False,
                    "is_active": True,
                }
            )
        session = db.session()
        try:
            session.bulk_insert_mappings(CouponCode, coupon_codes, return_defaults=True)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

        return coupon_codes

    @staticmethod
    def generate_code(length=6):
        """Generate a random coupon code of fixed length"""
        characters = string.ascii_uppercase + string.digits
        random_code = "".join(random.choice(characters) for _ in range(length))
        is_exist = CouponService.get_exist_code(random_code)
        while is_exist:
            random_code = "".join(random.choice(characters) for _ in range(length))
            is_exist = CouponService.get_exist_code(random_code)

        CouponService.set_exist_code(random_code)
        return random_code

    @staticmethod
    def get_exist_code(code):
        """Check if a coupon code exists using Redis bitmap"""

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        key = f"toktak:coupon_codes_bitmap:{today}"
        hash_val = int(hashlib.md5(code.encode()).hexdigest(), 16)
        bit_position = hash_val % 1000000

        return redis_client.getbit(key, bit_position) == 1

    @staticmethod
    def set_exist_code(code):
        """Check if a coupon code exists using Redis bitmap"""

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        key = f"toktak:coupon_codes_bitmap:{today}"
        hash_val = int(hashlib.md5(code.encode()).hexdigest(), 16)
        bit_position = hash_val % 1000000

        redis_client.setbit(key, bit_position, 1)
        if redis_client.ttl(key) == -1:
            now = datetime.datetime.now()
            tomorrow = now + datetime.timedelta(days=1)
            midnight = datetime.datetime.combine(tomorrow.date(), datetime.time.min)
            seconds_until_midnight = int((midnight - now).total_seconds())
            redis_client.expire(key, seconds_until_midnight)

    @staticmethod
    def get_code_by_day():
        today = datetime.datetime.now().strftime("%d")
        string_for_day = "0C9XJ2T5VMRZK6Y3H7A1PNLQ48WDBFG"
        index = int(today)
        return string_for_day[index]

    @staticmethod
    def get_code_by_month():
        month = datetime.datetime.now().strftime("%m")
        string_for_month = "YJ6B1NQK3XW0"
        index = int(month)
        return string_for_month[index]

    @staticmethod
    def get_code_by_year():
        year = datetime.datetime.now().strftime("%Y")
        string_for_year = "XJ7A9ZLQKM8D6W3N2TYCBRF0O5VUGE1S4PHI"
        length = len(string_for_year)
        index1 = int(year[:2]) % length
        index2 = int(year[-2:]) % length
        return string_for_year[index1] + string_for_year[index2]
