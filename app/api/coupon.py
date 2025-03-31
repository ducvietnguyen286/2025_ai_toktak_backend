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
        coupon_code = CouponService.find_coupon_code(code)
        coupon_code.is_used = True
        coupon_code.is_active = False
        coupon_code.used_by = current_user.id
        coupon_code.used_at = datetime.datetime.now()
        coupon_code.save()

        current_user.subscription = "STANDARD"
        current_user.subscription_expired = (
            datetime.datetime.now() + datetime.timedelta(days=90)
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
        CouponService.create_codes(coupon.id, count_code=max_used)
        return Response(
            data=coupon._to_json(),
            message="Tạo coupon thành công",
        ).to_dict()
