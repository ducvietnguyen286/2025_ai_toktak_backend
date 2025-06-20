# coding: utf8
import datetime
import json
import traceback
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response

from app.services.auth import AuthService
from app.services.coupon import CouponService
from app.services.user import UserService
from app.services.notification import NotificationServices

ns = Namespace(name="coupon", description="User API")
from app.extensions import db, redis_client
from sqlalchemy.orm import Session
import const
from app.lib.logger import logger


@ns.route("/used")
class APIUsedCoupon(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "code": {"type": "string"},
        },
        required=["code"],
    )
    def post(self, args):
        current_user = AuthService.get_current_identity(no_cache=True)
        current_user_id = current_user.id
        code = args.get("code", "")
        coupon = CouponService.find_coupon_by_code(code)
        if coupon == "not_exist":
            return Response(
                message="유효하지 않은 쿠폰입니다.<br/>쿠폰 번호를 확인해 주세요😭",
                code=201,
            ).to_dict()
        if coupon == "used":
            return Response(
                message="사용된 쿠폰 번호입니다.<br/>쿠폰 번호를Y 확인해 주세요😭",
                message_en="Coupon is used",
                code=201,
            ).to_dict()
        if coupon == "not_active":
            return Response(
                message="쿠폰 코드가 사용 불가능합니다<br/>쿠폰 번호를 확인해 주세요😭",
                message_en="Coupon is not active",
                code=201,
            ).to_dict()
        if coupon == "expired":
            return Response(
                message="유효하지 않은 쿠폰입니다.<br/>쿠폰 번호를 확인해 주세요😭",
                message_en="Mã đã hết hạn expired",
                code=201,
            ).to_dict()

        if coupon.is_has_whitelist:
            if current_user.id not in json.loads(coupon.white_lists):
                return Response(
                    message="쿠폰 코드가 사용 불가능합니다",
                    code=201,
                ).to_dict()

        today = datetime.datetime.today().date()
        if coupon.expired_from and coupon.expired_from.date() > today:
            return Response(
                message="쿠폰 코드가 사용 불가능합니다",
                code=201,
            ).to_dict()

        if coupon.expired and coupon.expired.date() < today:
            return Response(
                message="쿠폰 코드가 만료되었습니다",
                code=201,
            ).to_dict()

        if coupon.is_check_user:
            count_used = CouponService.count_coupon_used(coupon.id, current_user.id)
            if coupon.max_per_user and count_used >= coupon.max_per_user:
                return Response(
                    message="쿠폰 코드가 사용 가능 횟수를 초과했습니다",
                    message_en="The coupon code has exceeded the number of allowed uses with is_check_user",
                    code=201,
                ).to_dict()
        coupon_code = CouponService.find_coupon_code(code)

        # kiểm tra xem user đã dùng mã mời của KOL hay chưa
        # Nếu đã dùng của người khác thì không được dùng của KOL cũ
        if coupon.type == "KOL_COUPON":

            login_is_auth_nice = current_user.is_auth_nice
            if login_is_auth_nice == 0:
                return Response(
                    message_title="⏰ 아쉽지만 사용 기한이 지났어요.",
                    message="이 쿠폰은 가입 후 7일 이내에만 사용할 수 있어요! 😥",
                    message_en="It has been 8 days since registration.",
                    code=203,
                ).to_dict()

            # Use KOL coupon_Fail_over join date
            login_created_at = current_user.created_at
            today = datetime.datetime.today().date()
            if login_created_at and (today - login_created_at.date()).days >= 8:
                return Response(
                    message_title="⏰ 아쉽지만 사용 기한이 지났어요.",
                    message="이 쿠폰은 가입 후 7일 이내에만 사용할 수 있어요! 😥",
                    message_en="It has been 8 days since registration.",
                    code=202,
                ).to_dict()

            user_history = UserService.find_user_history_coupon_kol(
                current_user_id, "KOL_COUPON"
            )
            if user_history:
                return Response(
                    data={},
                    message="이 쿠폰은 중복 사용이 불가능해요. 😊",
                    message_title="⚠️ 이미 같은 종류의 쿠폰을 사용하셨어요!",
                    message_en="Use KOL coupon_Fail_use same type coupon",
                    code=202,
                ).to_dict()

        result = None

        coupon.expunge()
        coupon_code.expunge()
        # current_user.expunge()

        with Session(bind=db.engine) as session:
            try:
                with session.begin():
                    coupon.used += 1

                    coupon_code.is_used = True
                    coupon_code.used_by = current_user.id
                    coupon_code.used_at = datetime.datetime.now()
                    login_subscription_expired = (
                        current_user.subscription_expired or datetime.datetime.now()
                    )

                    if coupon.type == "DISCOUNT":
                        pass
                    elif (
                        coupon.type == "SUB_STANDARD" or coupon.type == "SUB_STANDARD_2"
                    ):
                        value_coupon = coupon_code.value if coupon_code.value else 30

                        if current_user.subscription == "FREE":
                            login_subscription_expired = datetime.datetime.now()
                            current_user.batch_total = value_coupon
                            current_user.batch_remain = value_coupon
                        else:
                            current_user.batch_total += value_coupon
                            current_user.batch_remain += value_coupon

                        login_subscription_expired = (
                            login_subscription_expired + datetime.timedelta(days=1)
                        )

                        current_user.batch_no_limit_sns = 1
                        # tong so luong kenh co the lien ket
                        current_user.total_link_active = 7
                        current_user.subscription = "COUPON_STANDARD"
                        expired_at = login_subscription_expired + datetime.timedelta(
                            days=coupon_code.num_days
                        )
                        end_of_expired_at = expired_at.replace(
                            hour=23, minute=59, second=59
                        )
                        coupon_code.expired_at = end_of_expired_at
                        current_user.subscription_expired = end_of_expired_at

                        redis_user_batch_key = (
                            f"toktak:users:batch_remain:{current_user_id}"
                        )
                        redis_user_batch_sns_key = (
                            f"toktak:users:batch_sns_remain:{current_user_id}"
                        )
                        redis_client.delete(redis_user_batch_key)
                        redis_client.delete(redis_user_batch_sns_key)

                    elif coupon.type == "SUB_PREMIUM":
                        pass
                    elif coupon.type == "SUB_PRO":
                        pass
                    elif coupon.type == "KOL_COUPON":
                        current_user_id = current_user.id
                        value_coupon = coupon_code.value if coupon_code.value else 30

                        if current_user.subscription == "FREE":
                            login_subscription_expired = datetime.datetime.now()
                            current_user.batch_total = value_coupon
                            current_user.batch_remain = value_coupon
                        else:
                            current_user.batch_total += value_coupon
                            current_user.batch_remain += value_coupon

                        login_subscription_expired = (
                            login_subscription_expired + datetime.timedelta(days=1)
                        )

                        current_user.batch_no_limit_sns = 1
                        current_user.total_link_active = (
                            coupon_code.total_link_active or 1
                        )
                        current_user.subscription = "COUPON_KOL"
                        expired_at = login_subscription_expired + datetime.timedelta(
                            days=coupon_code.num_days
                        )
                        end_of_expired_at = expired_at.replace(
                            hour=23, minute=59, second=59
                        )
                        coupon_code.expired_at = end_of_expired_at
                        current_user.subscription_expired = end_of_expired_at

                        redis_user_batch_key = (
                            f"toktak:users:batch_remain:{current_user_id}"
                        )
                        redis_user_batch_sns_key = (
                            f"toktak:users:batch_sns_remain:{current_user_id}"
                        )
                        redis_client.delete(redis_user_batch_key)
                        redis_client.delete(redis_user_batch_sns_key)

                    coupon = session.merge(coupon)
                    coupon_code = session.merge(coupon_code)
                    current_user = session.merge(current_user)

                    result = coupon_code._to_json()

                    # Ghi Log History
                    data_user_history = {
                        "user_id": current_user_id,
                        "type": "USED_COUPON",
                        "type_2": coupon.type,
                        "object_id": coupon_code.id,
                        "object_start_time": login_subscription_expired,
                        "object_end_time": end_of_expired_at,
                        "title": coupon_code.coupon.name,
                        "description": coupon_code.code,
                        "value": coupon_code.value,
                        "num_days": coupon_code.num_days,
                    }

                    UserService.create_user_history(**data_user_history)
                    NotificationServices.create_notification(
                        notification_type="COUPON_USED",
                        user_id=current_user_id,
                        title=f"사용자가 쿠폰 코드 {code} 를 성공적으로 입력했습니다.",
                    )

            except Exception as e:
                traceback.print_exc()
                print(f"Error: {e}")
                logger.error(f"Error: {e}")
                return Response(
                    message="Có lỗi xảy ra khi sử dụng coupon",
                    status=400,
                ).to_dict()

        return Response(
            data=result,
            message="Sử dụng thành công",
        ).to_dict()


@ns.route("/create")
class APICreateCoupon(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "image": {"type": ["string", "null"]},
            "name": {"type": ["string", "null"]},
            "type": {
                "type": ["string", "null"],
                "enum": [
                    "DISCOUNT",
                    "SUB_STANDARD",
                    "SUB_STANDARD_2",
                    "SUB_PREMIUM",
                    "SUB_PRO",
                    "KOL_COUPON",
                ],
            },
            "is_check_user": {"type": "boolean"},
            "max_per_user": {"type": "string"},
            "max_used": {"type": ["string", "null"]},
            "num_days": {"type": ["string", "null"]},
            "total_link_active": {"type": ["string", "null"]},
            "value": {"type": ["string", "null"]},
            # "is_has_whitelist": {"type": "boolean"},
            # "white_lists": {"type": "array", "items": {"type": ["string", "null"]}},
            "description": {"type": ["string", "null"]},
            "expired": {"type": ["string", "null"]},
            "expired_from": {"type": ["string", "null"]},
        },
        required=["name", "max_used"],
    )
    def post(self, args):
        user_id = AuthService.get_user_id()
        image = args.get("image", "")
        name = args.get("name", "")
        type = args.get("type", "SUB_STANDARD")
        is_check_user = args.get("is_check_user", False)
        max_per_user = args.get("max_per_user", 1)
        try:
            expired_from = datetime.datetime.strptime(
                args.get("expired_from", ""), "%Y-%m-%d"
            ).date()
        except ValueError:
            expired_from = None
        try:
            expired = datetime.datetime.strptime(
                args.get("expired", ""), "%Y-%m-%d"
            ).date()
            expired = datetime.datetime.combine(expired, datetime.time(23, 59, 59))
        except ValueError:
            expired = None

        max_used = int(args.get("max_used", 1)) if args.get("max_used") else 1
        num_days = (
            int(args.get("num_days", const.DATE_EXPIRED))
            if args.get("num_days")
            else const.DATE_EXPIRED
        )

        total_link_active = (
            int(args.get("total_link_active", const.MAX_SNS))
            if args.get("total_link_active")
            else const.MAX_SNS
        )

        value = args.get("value")
        is_has_whitelist = args.get("is_has_whitelist", False)
        white_lists = args.get("white_lists", [])
        description = args.get("description", "")

        code_coupon = ""
        if type == "KOL_COUPON":
            coupon_detail = CouponService.find_coupon_by_name(name)
            if coupon_detail:
                return Response(message="이미 생성된 이름입니다.", code=201).to_dict()
            code_coupon = name
            max_used = 1

        coupon = CouponService.create_coupon(
            image=image,
            name=name,
            type=type,
            max_used=max_used,
            value=value,
            is_has_whitelist=is_has_whitelist,
            is_check_user=is_check_user,
            max_per_user=max_per_user,
            white_lists=json.dumps(white_lists),
            description=description,
            expired=expired,
            expired_from=expired_from,
            created_by=user_id,
            # number_expired=number_expired,
        )

        CouponService.create_codes(
            coupon.id,
            code_coupon,
            count_code=max_used,
            value=value,
            num_days=num_days,
            total_link_active=total_link_active,
            expired_at=expired,
        )
        return Response(
            data=coupon._to_json(),
            message="쿠폰 생성 성공",
        ).to_dict()


@ns.route("/<int:id>/add-codes")
class APIAddCouponCodes(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "count": {"type": "integer"},
            "expired_at": {"type": "string"},
        },
        required=["count"],
    )
    def post(self, args, id):
        count = args.get("count", 0)
        expired_at = args.get("expired_at", None)
        if expired_at:
            expired_at = datetime.datetime.strptime(expired_at, "%Y-%m-%dT%H:%M:%SZ")
        coupon = CouponService.find_coupon(id)
        if not coupon:
            return Response(
                message="Không tìm thấy coupon",
                status=400,
            ).to_dict()
        if not expired_at:
            expired_at = coupon.expired

        num_days = (expired_at - datetime.datetime.now()).days

        CouponService.create_codes(
            coupon.id,
            value=coupon.value,
            count_code=count,
            num_days=num_days,
            expired_at=expired_at,
        )

        return Response(
            message="Thêm mã coupon thành công",
        ).to_dict()


@ns.route("/list")
class APIListCoupon(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "name": {"type": "string"},
            "type": {"type": "string"},
            "from_max_used": {"type": ["integer", "null"]},
            "to_max_used": {"type": ["integer", "null"]},
            "from_used": {"type": ["integer", "null"]},
            "to_used": {"type": ["integer", "null"]},
            "from_expired": {"type": "string"},
            "to_expired": {"type": "string"},
            "from_created_at": {"type": "string"},
            "to_created_at": {"type": "string"},
            "created_by": {"type": "array", "items": {"type": ["integer", "null"]}},
            "is_active": {"type": "boolean"},
            "page": {"type": ["string", "null"]},
            "per_page": {"type": ["string", "null"]},
            "sort": {"type": "string"},
        },
        required=[],
    )
    def get(self, args):
        name = args.get("name", None)
        type = args.get("type", None)
        from_max_used = args.get("from_max_used", None)
        to_max_used = args.get("to_max_used", None)
        from_used = args.get("from_used", None)
        to_used = args.get("to_used", None)
        from_expired = args.get("from_expired", None)
        to_expired = args.get("to_expired", None)
        from_created_at = args.get("from_created_at", None)
        to_created_at = args.get("to_created_at", None)
        is_active = args.get("is_active", None)
        created_by = args.get("created_by", None)
        page = int(args.get("page", 1)) if args.get("page") else 1
        limit = int(args.get("per_page", 10)) if args.get("per_page") else 10
        sort = args.get("sort", "created_at|desc")

        if from_expired:
            from_expired = datetime.datetime.strptime(
                from_expired, "%Y-%m-%dT%H:%M:%SZ"
            )
        if to_expired:
            to_expired = datetime.datetime.strptime(to_expired, "%Y-%m-%dT%H:%M:%SZ")
        if from_created_at:
            from_created_at = datetime.datetime.strptime(
                from_created_at, "%Y-%m-%dT%H:%M:%SZ"
            )
        if to_created_at:
            to_created_at = datetime.datetime.strptime(
                to_created_at, "%Y-%m-%dT%H:%M:%SZ"
            )
        if from_max_used:
            from_max_used = int(from_max_used)
        if to_max_used:
            to_max_used = int(to_max_used)
        if from_used:
            from_used = int(from_used)
        if to_used:
            to_used = int(to_used)
        if created_by:
            created_by = [int(x) for x in created_by]
        if is_active:
            is_active = bool(is_active)

        query_params = {
            "name": name,
            "type": type,
            "from_max_used": from_max_used,
            "to_max_used": to_max_used,
            "from_used": from_used,
            "to_used": to_used,
            "from_expired": from_expired,
            "to_expired": to_expired,
            "from_created_at": from_created_at,
            "to_created_at": to_created_at,
            "is_active": is_active,
            "created_by": created_by,
            "page": page,
            "limit": limit,
            "sort": sort,
        }
        coupons, total_coupons = CouponService.get_coupons(query_params)
        pagination = {
            "page": page,
            "limit": limit,
            "total": total_coupons,
            "total_pages": total_coupons // limit
            + (1 if total_coupons % limit > 0 else 0),
            "has_next": total_coupons > page * limit,
            "has_prev": page > 1,
        }

        return Response(
            data={
                "list": coupons,
                "pagination": pagination,
            },
            message="Lấy danh sách coupon thành công",
        ).to_dict()


@ns.route("/<int:id>")
class APICoupon(Resource):

    @jwt_required()
    def get(self, id):
        coupon = CouponService.find_coupon(id)
        if not coupon:
            return Response(
                message="Không tìm thấy coupon",
                status=400,
            ).to_dict()

        return Response(
            data=coupon._to_json(),
            message="Lấy coupon thành công",
        ).to_dict()


@ns.route("/<int:id>/update")
class APIUpdateCoupon(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "image": {"type": "string"},
            "name": {"type": "string"},
            "is_has_whitelist": {"type": "boolean"},
            "white_lists": {"type": "array", "items": {"type": "integer"}},
            "description": {"type": "string"},
            "expired": {"type": "string"},
        },
        required=[],
    )
    def post(self, args, id):
        image = args.get("image", None)
        name = args.get("name", None)
        is_has_whitelist = args.get("is_has_whitelist", None)
        white_lists = args.get("white_lists", None)
        description = args.get("description", None)
        expired = args.get("expired", None)

        coupon = CouponService.find_coupon(id)
        if not coupon:
            return Response(
                message="Không tìm thấy coupon",
                status=400,
            ).to_dict()

        if image:
            coupon.image = image
        if name:
            coupon.name = name
        if is_has_whitelist:
            coupon.is_has_whitelist = is_has_whitelist
        if white_lists:
            coupon.white_lists = json.dumps(white_lists)
        if description:
            coupon.description = description
        if expired:
            expired = datetime.datetime.strptime(expired, "%Y-%m-%dT%H:%M:%SZ")
            coupon.expired_at = expired

            CouponService.update_coupon_codes(
                coupon.id,
                expired_at=expired,
            )

        coupon.save()

        return Response(
            data=coupon._to_json(),
            message="Cập nhật coupon thành công",
        ).to_dict()


@ns.route("/<int:id>/delete")
class APIDeleteCoupon(Resource):

    @jwt_required()
    def post(self, id):
        coupon = CouponService.find_coupon(id)
        if not coupon:
            return Response(
                message="Không tìm thấy coupon",
                status=400,
            ).to_dict()

        CouponService.delete_coupon_codes(coupon.id)
        coupon.delete()

        return Response(
            message="Xóa coupon thành công",
        ).to_dict()


@ns.route("/list/codes")
class APIListCouponCodes(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "coupon_id": {"type": ["string", "null"]},
            "code": {"type": "string"},
            "is_used": {"type": ["string", "null"]},
            "is_active": {"type": "boolean"},
            "from_created_at": {"type": "string"},
            "to_created_at": {"type": "string"},
            "from_expired": {"type": "string"},
            "to_expired": {"type": "string"},
            "used_by": {"type": ["string", "null"]},
            "from_used_at": {"type": "string"},
            "to_used_at": {"type": "string"},
            "type_coupon": {"type": ["string", "null"]},
            "type_use_coupon": {"type": ["string", "null"]},
            "page": {"type": ["string", "null"]},
            "limit": {"type": ["string", "null"]},
            "type_order": {"type": "string"},
            "category_id": {"type": "string"},
        },
        required=[],
    )
    def get(self, args):
        coupon_id = args.get("coupon_id", None)
        code = args.get("code", None)
        is_used = args.get("is_used", None)
        is_active = args.get("is_active", None)
        from_created_at = args.get("from_created_at", None)
        to_created_at = args.get("to_created_at", None)
        from_expired = args.get("from_expired", None)
        to_expired = args.get("to_expired", None)
        used_by = args.get("used_by", None)
        from_used_at = args.get("from_used_at", None)
        to_used_at = args.get("to_used_at", None)
        type_use_coupon = args.get("type_use_coupon", None)
        page = int(args.get("page", 1)) if args.get("page") else 1
        limit = int(args.get("per_page", 10)) if args.get("per_page") else 10
        type_order = args.get("type_order", "id_desc")
        category_id = args.get("category_id", "")

        if from_created_at:
            from_created_at = datetime.datetime.strptime(
                from_created_at, "%Y-%m-%dT%H:%M:%SZ"
            )
        if to_created_at:
            to_created_at = datetime.datetime.strptime(
                to_created_at, "%Y-%m-%dT%H:%M:%SZ"
            )
        if from_expired:
            from_expired = datetime.datetime.strptime(
                from_expired, "%Y-%m-%dT%H:%M:%SZ"
            )
        if to_expired:
            to_expired = datetime.datetime.strptime(to_expired, "%Y-%m-%dT%H:%M:%SZ")
        if from_used_at:
            from_used_at = datetime.datetime.strptime(
                from_used_at, "%Y-%m-%dT%H:%M:%SZ"
            )
        if to_used_at:
            to_used_at = datetime.datetime.strptime(to_used_at, "%Y-%m-%dT%H:%M:%SZ")
        if coupon_id:
            coupon_id = int(coupon_id)

        if is_used:
            is_used = bool(is_used)

        if is_active:
            is_active = bool(is_active)
        if used_by:
            used_by = int(used_by)

        query_params = {
            "coupon_id": coupon_id,
            "code": code,
            "is_used": is_used,
            "is_active": is_active,
            "from_created_at": from_created_at,
            "to_created_at": to_created_at,
            "from_expired": from_expired,
            "to_expired": to_expired,
            "used_by": used_by,
            "from_used_at": from_used_at,
            "to_used_at": to_used_at,
            "type_use_coupon": type_use_coupon,
            "page": page,
            "limit": limit,
            "type_order": type_order,
            "category_id": category_id,
        }
        coupon_codes, total_codes = CouponService.get_coupon_codes(query_params)

        total_pages = total_codes // limit + (1 if total_codes % limit > 0 else 0)
        pagination = {
            "page": page,
            "limit": limit,
            "total": total_codes,
            "total_pages": total_pages,
            "has_next": total_codes > page * limit,
            "has_prev": page > 1,
        }

        return {
            "status": True,
            "message": "Lấy danh sách coupon thành công",
            "total": total_codes,
            "page": page,
            "per_page": limit,
            "total_pages": total_pages,
            "data": coupon_codes,
        }, 200


@ns.route("/category")
class APIListCouponCodes(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "coupon_id": {"type": ["string", "null"]},
            "code": {"type": "string"},
            "is_used": {"type": ["string", "null"]},
            "is_active": {"type": "boolean"},
            "from_created_at": {"type": "string"},
            "to_created_at": {"type": "string"},
            "from_expired": {"type": "string"},
            "to_expired": {"type": "string"},
            "used_by": {"type": ["string", "null"]},
            "from_used_at": {"type": "string"},
            "to_used_at": {"type": "string"},
            "type_coupon": {"type": ["string", "null"]},
            "type_use_coupon": {"type": ["string", "null"]},
            "page": {"type": ["string", "null"]},
            "limit": {"type": ["string", "null"]},
            "type_order": {"type": "string"},
        },
        required=[],
    )
    def get(self, args):
        coupon_id = args.get("coupon_id", None)
        code = args.get("code", None)
        is_used = args.get("is_used", None)
        is_active = args.get("is_active", None)
        from_created_at = args.get("from_created_at", None)
        to_created_at = args.get("to_created_at", None)
        from_expired = args.get("from_expired", None)
        to_expired = args.get("to_expired", None)
        used_by = args.get("used_by", None)
        from_used_at = args.get("from_used_at", None)
        to_used_at = args.get("to_used_at", None)
        type_coupon = args.get("type_coupon", "")
        page = int(args.get("page", 1)) if args.get("page") else 1
        limit = int(args.get("per_page", 10)) if args.get("per_page") else 10
        type_order = args.get("type_order", "id_desc")

        if from_created_at:
            from_created_at = datetime.datetime.strptime(
                from_created_at, "%Y-%m-%dT%H:%M:%SZ"
            )
        if to_created_at:
            to_created_at = datetime.datetime.strptime(
                to_created_at, "%Y-%m-%dT%H:%M:%SZ"
            )
        if from_expired:
            from_expired = datetime.datetime.strptime(
                from_expired, "%Y-%m-%dT%H:%M:%SZ"
            )
        if to_expired:
            to_expired = datetime.datetime.strptime(to_expired, "%Y-%m-%dT%H:%M:%SZ")
        if from_used_at:
            from_used_at = datetime.datetime.strptime(
                from_used_at, "%Y-%m-%dT%H:%M:%SZ"
            )
        if to_used_at:
            to_used_at = datetime.datetime.strptime(to_used_at, "%Y-%m-%dT%H:%M:%SZ")
        if coupon_id:
            coupon_id = int(coupon_id)

        if is_used:
            is_used = bool(is_used)

        if is_active:
            is_active = bool(is_active)
        if used_by:
            used_by = int(used_by)

        query_params = {
            "coupon_id": coupon_id,
            "code": code,
            "is_used": is_used,
            "is_active": is_active,
            "from_created_at": from_created_at,
            "to_created_at": to_created_at,
            "from_expired": from_expired,
            "to_expired": to_expired,
            "used_by": used_by,
            "from_used_at": from_used_at,
            "to_used_at": to_used_at,
            "type_coupon": type_coupon,
            "page": page,
            "limit": limit,
            "type_order": type_order,
        }
        coupon_codes, total_codes = CouponService.get_coupon_category(query_params)

        total_pages = total_codes // limit + (1 if total_codes % limit > 0 else 0)
        pagination = {
            "page": page,
            "limit": limit,
            "total": total_codes,
            "total_pages": total_pages,
            "has_next": total_codes > page * limit,
            "has_prev": page > 1,
        }

        return {
            "status": True,
            "message": "Lấy danh sách coupon thành công",
            "total": total_codes,
            "page": page,
            "per_page": limit,
            "total_pages": total_pages,
            "data": coupon_codes,
        }, 200


@ns.route("/get_user_coupon")
class APIGetUserCoupon(Resource):
    @jwt_required()
    def get(self):
        user_id = AuthService.get_user_id()
        coupon = CouponService.get_last_used(user_id)
        if not coupon:
            return Response(
                message="Không tìm thấy coupon",
                code=201,
            ).to_dict()

        return Response(
            data=coupon,
            message="Lấy coupon user thành công",
        ).to_dict()
