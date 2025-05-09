from flask import request
from flask_restx import Resource, Namespace
from flask_jwt_extended import jwt_required, get_jwt_identity

import json
from app.services.auth import AuthService
from app.services.payment_services import PaymentService
from app.services.post import PostService
from app.lib.response import Response
from app.lib.logger import logger

ns = Namespace("payment", description="Payment API")


@ns.route("/create_new_payment")
class APICreateNewPayment(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        payment_type = data.get("payment_type", 0)

        user_id_login = 0
        current_user = AuthService.get_current_identity() or None
        user_id_login = current_user.id

        data_update_template = {
            "payment_type": payment_type,
            "user_id": user_id_login,
        }

        payment = PaymentService.create_payment(
            user_id=user_id_login, **data_update_template
        )

        return Response(
            message="Payment created",
            data={"payment": payment._to_json()},
            code=200,
        ).to_dict()
