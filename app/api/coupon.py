# coding: utf8
import datetime
import json
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters
from app.lib.response import Response

from app.services.auth import AuthService
from app.services.coupon import CouponService

ns = Namespace(name="coupon", description="User API")


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
        current_user = AuthService.get_current_identity()
        code = args.get("code", "")
        coupon = CouponService.find_coupon_by_code(code)
        if coupon == "not_exist":
            return Response(
                message="Mã coupon không tồn tại",
                status=400,
            ).to_dict()
        if coupon == "used":
            return Response(
                message="Mã coupon đã được sử dụng",
                status=400,
            ).to_dict()
        if coupon == "not_active":
            return Response(
                message="Mã coupon không khả dụng",
                status=400,
            ).to_dict()
        if coupon == "expired":
            return Response(
                message="Mã coupon đã hết hạn",
                status=400,
            ).to_dict()

        if coupon.is_has_whitelist:
            if current_user.id not in json.loads(coupon.white_lists):
                return Response(
                    message="Mã coupon không khả dụng",
                    status=400,
                ).to_dict()

        if coupon.expired and coupon.expired < datetime.datetime.now():
            return Response(
                message="Mã coupon đã hết hạn",
                status=400,
            ).to_dict()

        if coupon.max_used and coupon.used >= coupon.max_used:
            return Response(
                message="Mã coupon đã hết lượt sử dụng",
                status=400,
            ).to_dict()

        coupon.used += 1
        coupon.save()

        coupon_code = CouponService.find_coupon_code(code)
        coupon_code.is_used = True
        coupon_code.is_active = False
        coupon_code.used_by = current_user.id
        coupon_code.used_at = datetime.datetime.now()
        coupon_code.save()

        if coupon.type == "SUB_STANDARD":
            current_user.subscription = "STANDARD"
            current_user.subscription_expired = (
                datetime.datetime.now() + datetime.timedelta(days=30)
            )
            current_user.save()

        return Response(
            data=coupon_code._to_json(),
            message="Sử dụng thành công",
        ).to_dict()


@ns.route("/create")
class APICreateCoupon(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "image": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string"},
            "max_used": {"type": "integer"},
            "is_has_whitelist": {"type": "boolean"},
            "white_lists": {"type": "array", "items": {"type": "string"}},
            "description": {"type": "string"},
            "expired": {"type": "string"},
        },
        required=["name", "type", "max_used"],
    )
    def post(self, args):
        current_user = AuthService.get_current_identity()
        print(current_user)
        image = args.get("image", "")
        name = args.get("name", "")
        type = args.get("type", "")
        max_used = args.get("max_used", 0)
        is_has_whitelist = args.get("is_has_whitelist", False)
        white_lists = args.get("white_lists", [])
        description = args.get("description", "")
        expired = args.get("expired", None)
        if expired:
            expired = datetime.datetime.strptime(expired, "%Y-%m-%dT%H:%M:%SZ")
        else:
            expired = datetime.datetime.now() + datetime.timedelta(days=30)
        coupon = CouponService.create_coupon(
            image=image,
            name=name,
            type=type,
            max_used=max_used,
            is_has_whitelist=is_has_whitelist,
            white_lists=json.dumps(white_lists),
            description=description,
            expired=expired,
            created_by=current_user.id,
        )
        CouponService.create_codes(coupon.id, count_code=max_used, expired_at=expired)
        return Response(
            data=coupon._to_json(),
            message="Tạo coupon thành công",
        ).to_dict()


@ns.route("/list")
class APIListCoupon(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "name": {"type": "string"},
            "type": {"type": "string"},
            "from_max_used": {"type": "integer"},
            "to_max_used": {"type": "integer"},
            "from_used": {"type": "integer"},
            "to_used": {"type": "integer"},
            "from_expired": {"type": "string"},
            "to_expired": {"type": "string"},
            "from_created_at": {"type": "string"},
            "to_created_at": {"type": "string"},
            "created_by": {"type": "array", "items": {"type": "integer"}},
            "is_active": {"type": "boolean"},
            "page": {"type": "integer"},
            "limit": {"type": "integer"},
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
        page = args.get("page", 1)
        limit = args.get("limit", 10)
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
            "coupon_id": {"type": "integer"},
            "code": {"type": "string"},
            "is_used": {"type": "boolean"},
            "is_active": {"type": "boolean"},
            "from_created_at": {"type": "string"},
            "to_created_at": {"type": "string"},
            "from_expired": {"type": "string"},
            "to_expired": {"type": "string"},
            "used_by": {"type": "integer"},
            "from_used_at": {"type": "string"},
            "to_used_at": {"type": "string"},
            "page": {"type": "integer"},
            "limit": {"type": "integer"},
            "sort": {"type": "string"},
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
        page = args.get("page", 1)
        limit = args.get("limit", 10)
        sort = args.get("sort", "created_at|desc")

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
            "page": page,
            "limit": limit,
            "sort": sort,
        }
        coupon_codes, total_codes = CouponService.get_coupon_codes(query_params)

        pagination = {
            "page": page,
            "limit": limit,
            "total": total_codes,
            "total_pages": total_codes // limit + (1 if total_codes % limit > 0 else 0),
            "has_next": total_codes > page * limit,
            "has_prev": page > 1,
        }

        return Response(
            data={"list": coupon_codes, "pagination": pagination},
            message="Lấy danh sách coupon thành công",
        ).to_dict()
