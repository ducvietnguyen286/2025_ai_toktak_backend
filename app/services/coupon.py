import datetime
import hashlib
from app.models.coupon import Coupon
from app.models.coupon_code import CouponCode
from app.models.user import User
import random
import string
from app.extensions import redis_client, db
from sqlalchemy.orm import Session, aliased

BATCH_SIZE = 1000


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
        if coupon_code.expired_at and coupon_code.expired_at < datetime.datetime.now():
            return "expired"
        return Coupon.query.where(Coupon.id == coupon_code.coupon_id).first()

    @staticmethod
    def find_coupon_code(code):
        return CouponCode.query.where(CouponCode.code == code).first()

    @staticmethod
    def update_coupon_codes(coupon_id, **kwargs):
        session = Session(bind=db.engine)
        try:
            session.query(CouponCode).filter(CouponCode.coupon_id == coupon_id).update(
                kwargs
            )
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def delete_coupon_codes(coupon_id):
        session = Session(bind=db.engine)
        try:
            session.query(CouponCode).filter(CouponCode.coupon_id == coupon_id).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def get_coupons(query_params={}):
        coupon_query = Coupon.query
        if "name" in query_params and query_params["name"]:
            coupon_query = coupon_query.filter(
                Coupon.name.ilike(f"%{query_params['name']}%")
            )
        if "type" in query_params and query_params["type"]:
            coupon_query = coupon_query.filter(Coupon.type == query_params["type"])
        if "from_max_used" in query_params and query_params["from_max_used"]:
            coupon_query = coupon_query.filter(
                Coupon.max_used >= query_params["from_max_used"]
            )
        if "to_max_used" in query_params and query_params["to_max_used"]:
            coupon_query = coupon_query.filter(
                Coupon.max_used <= query_params["to_max_used"]
            )
        if "from_used" in query_params and query_params["from_used"]:
            coupon_query = coupon_query.filter(Coupon.used >= query_params["from_used"])
        if "to_used" in query_params and query_params["to_used"]:
            coupon_query = coupon_query.filter(Coupon.used <= query_params["to_used"])
        if "from_expired" in query_params and query_params["from_expired"]:
            coupon_query = coupon_query.filter(
                Coupon.expired >= query_params["from_expired"]
            )
        if "to_expired" in query_params and query_params["to_expired"]:
            coupon_query = coupon_query.filter(
                Coupon.expired <= query_params["to_expired"]
            )
        if "from_created_at" in query_params and query_params["from_created_at"]:
            coupon_query = coupon_query.filter(
                Coupon.created_at >= query_params["from_created_at"]
            )
        if "to_created_at" in query_params and query_params["to_created_at"]:
            coupon_query = coupon_query.filter(
                Coupon.created_at <= query_params["to_created_at"]
            )
        if "is_active" in query_params and query_params["is_active"] is not None:
            coupon_query = coupon_query.filter(
                Coupon.is_active == query_params["is_active"]
            )
        if "created_by" in query_params and query_params["created_by"]:
            coupon_query = coupon_query.filter(
                Coupon.created_by == query_params["created_by"]
            )
        total_coupons = coupon_query.count()
        if "sort" in query_params and query_params["sort"]:
            sort = query_params["sort"].split("|")
            if len(sort) == 2:
                field, order = sort
                order = order.lower()
                if order == "asc":
                    coupon_query = coupon_query.order_by(getattr(Coupon, field).asc())
                elif order == "desc":
                    coupon_query = coupon_query.order_by(getattr(Coupon, field).desc())
        if "page" in query_params and "limit" in query_params:
            page = int(query_params["page"])
            limit = int(query_params["limit"])
            coupon_query = coupon_query.offset((page - 1) * limit).limit(limit)

        coupons = coupon_query.all()
        coupons = [coupon._to_json() for coupon in coupons]
        return coupons, total_coupons

    @staticmethod
    def get_coupon_codes(query_params={}):
        # Alias bảng User để tránh xung đột trong join
        user_alias = aliased(User)

        # Tạo query với LEFT JOIN giữa CouponCode và User
        code_query = db.session.query(
            CouponCode, user_alias.username, user_alias.name, user_alias.email
        ).outerjoin(
            user_alias, CouponCode.used_by == user_alias.id
        )  # LEFT JOIN

        # Áp dụng các bộ lọc nếu có
        if "code" in query_params and query_params["code"]:
            code_query = code_query.filter(
                CouponCode.code.ilike(f"%{query_params['code']}%")
            )
        if "coupon_id" in query_params and query_params["coupon_id"]:
            code_query = code_query.filter(
                CouponCode.coupon_id == query_params["coupon_id"]
            )
        if "is_used" in query_params and query_params["is_used"] is not None:
            code_query = code_query.filter(
                CouponCode.is_used == query_params["is_used"]
            )
        if "used_by" in query_params and query_params["used_by"] is not None:
            code_query = code_query.filter(
                CouponCode.used_by == query_params["used_by"]
            )
        if "is_active" in query_params and query_params["is_active"] is not None:
            code_query = code_query.filter(
                CouponCode.is_active == query_params["is_active"]
            )
        if "from_expired" in query_params and query_params["from_expired"]:
            code_query = code_query.filter(
                CouponCode.expired_at >= query_params["from_expired"]
            )
        if "to_expired" in query_params and query_params["to_expired"]:
            code_query = code_query.filter(
                CouponCode.expired_at <= query_params["to_expired"]
            )
        if "from_created_at" in query_params and query_params["from_created_at"]:
            code_query = code_query.filter(
                CouponCode.created_at >= query_params["from_created_at"]
            )
        if "to_created_at" in query_params and query_params["to_created_at"]:
            code_query = code_query.filter(
                CouponCode.created_at <= query_params["to_created_at"]
            )
        if "from_used_at" in query_params and query_params["from_used_at"]:
            code_query = code_query.filter(
                CouponCode.used_at >= query_params["from_used_at"]
            )
        if "to_used_at" in query_params and query_params["to_used_at"]:
            code_query = code_query.filter(
                CouponCode.used_at <= query_params["to_used_at"]
            )

        # Đếm tổng số coupon (trước khi phân trang)
        total_codes = code_query.count()

        # Sắp xếp kết quả nếu có yêu cầu
        if "type_order" in query_params and query_params["type_order"]:
            sort = query_params["type_order"].split("_")
            if len(sort) == 2:
                field, order = sort
                order = order.lower()
                if order == "asc":
                    code_query = code_query.order_by(getattr(CouponCode, field).asc())
                elif order == "desc":
                    code_query = code_query.order_by(getattr(CouponCode, field).desc())
            else:
                code_query = code_query.order_by(CouponCode.id.desc())

        # Phân trang nếu có yêu cầu
        if "page" in query_params and "limit" in query_params:
            page = int(query_params["page"])
            limit = int(query_params["limit"])
            code_query = code_query.offset((page - 1) * limit).limit(limit)

        # Xử lý kết quả truy vấn
        coupon_codes = []
        for coupon_code, username, name, email in code_query.all():
            data = coupon_code._to_json()
            data.update({"username": username, "name": name, "email": email})
            coupon_codes.append(data)

        return coupon_codes, total_codes

    @staticmethod
    def create_codes(coupon_id, count_code=100, value=0, num_days=30, expired_at=None):
        coupon_codes = []
        code_by_day = CouponService.get_code_by_day()
        code_by_month = CouponService.get_code_by_month()
        code_by_year = CouponService.get_code_by_year()
        inserted_codes = set()

        for _ in range(count_code):
            code = CouponService.generate_code(6)
            code = f"{code_by_year}{code_by_month}{code_by_day}{code}"
            if code in inserted_codes:
                continue
            inserted_codes.add(code)
            data = {
                "coupon_id": coupon_id,
                "code": code,
                "value": value,
                "is_used": False,
                "is_active": True,
                "num_days": num_days,
                "created_at": datetime.datetime.now(),
                "updated_at": datetime.datetime.now(),
            }
            if expired_at:
                data["expired_at"] = expired_at
            coupon_code = CouponCode(**data)
            coupon_codes.append(coupon_code)

        session = Session(bind=db.engine)
        try:
            for i in range(0, len(coupon_codes), BATCH_SIZE):
                batch = coupon_codes[i : i + BATCH_SIZE]
                session.bulk_save_objects(batch)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def generate_code(length=10):
        """Generate a random coupon code of fixed length"""
        random_code = CouponService.generate_random_code(length)
        code_exist = CouponService.get_exist_code(random_code)
        while code_exist:
            random_code = CouponService.generate_random_code(length)
            code_exist = CouponService.get_exist_code(random_code)
        CouponService.set_exist_code(random_code)
        return random_code

    @staticmethod
    def generate_random_code(length=10):
        """Generate a random coupon code of fixed length"""
        characters = string.ascii_uppercase + string.digits
        return "".join(random.choice(characters) for _ in range(length))

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
        index = int(today) - 1
        return string_for_day[index]

    @staticmethod
    def get_code_by_month():
        month = datetime.datetime.now().strftime("%m")
        string_for_month = "YJ6B1NQK3XW0"
        index = int(month) - 1
        return string_for_month[index]

    @staticmethod
    def get_code_by_year():
        year = datetime.datetime.now().strftime("%Y")
        string_for_year = "XJ7A9ZLQKM8D6W3N2TYCBRF0O5VUGE1S4PHI"
        length = len(string_for_year)
        index1 = int(year[:2]) % length
        index2 = int(year[-2:]) % length
        return string_for_year[index1] + string_for_year[index2]

    @staticmethod
    def get_last_used(user_id):
        coupons = (
            CouponCode.query.where(CouponCode.used_by == user_id)
            .order_by(CouponCode.used_at.desc())
            .all()
        )
        return [coupon._to_json() for coupon in coupons]
