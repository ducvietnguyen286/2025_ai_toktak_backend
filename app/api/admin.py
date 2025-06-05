# coding: utf8
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.decorators import parameters, admin_required
from app.lib.response import Response
from app.services.user import UserService
from app.services.payment_services import PaymentService
from datetime import datetime, timedelta

from app.lib.logger import logger
import json
from flask import request, send_file
from app.services.auth import AuthService
from app.services.referral_service import ReferralService
from app.lib.string import get_level_images
import const
import os
import secrets
import string
import pandas as pd
from io import BytesIO
import traceback

from app.services.social_post import SocialPostService

ns = Namespace(name="admin", description="Admin API")


LOG_DIR = "logs"


@ns.route("/login")
class APIAdminLoginByInput(Resource):

    @parameters(
        type="object",
        properties={
            "email": {"type": "string"},
            "password": {"type": "string"},
        },
        required=["email", "password"],
    )
    def post(self, args):
        email = args.get("email", "")
        password = args.get("password", "")

        user = AuthService.loginAdmin(email, password)
        if not user:
            return Response(
                code=201,
                message="비밀번호가 정확하지 않습니다.",
            ).to_dict()

        tokens = AuthService.generate_token(user)
        tokens.update(
            {
                "type": "Bearer",
                "expires_in": 7200,
                "user": user._to_json(),
            }
        )

        return Response(
            data=tokens,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/users")
class APIUsers(Resource):

    @jwt_required()
    @admin_required()
    def get(self):
        page = request.args.get("page", const.DEFAULT_PAGE, type=int)
        per_page = request.args.get("per_page", const.DEFAULT_PER_PAGE, type=int)
        status = request.args.get("status", const.UPLOADED, type=int)
        type_order = request.args.get("type_order", "", type=str)
        type_post = request.args.get("type_post", "", type=str)
        time_range = request.args.get("time_range", "", type=str)
        search = request.args.get("search", "", type=str)
        member_type = request.args.get("member_type", "", type=str)
        from_date = request.args.get("from_date", "", type=str)
        to_date = request.args.get("to_date", "", type=str)
        data_search = {
            "page": page,
            "per_page": per_page,
            "status": status,
            "type_order": type_order,
            "type_post": type_post,
            "time_range": time_range,
            "search": search,
            "member_type": member_type,
            "from_date": from_date,
            "to_date": to_date,
        }
        users = UserService.admin_search_users(data_search)
        return {
            "status": True,
            "message": "Success",
            "total": users.total,
            "page": users.page,
            "per_page": users.per_page,
            "total_pages": users.pages,
            "data": [user_detail._to_json() for user_detail in users.items],
        }, 200


@ns.route("/delete_user")
class APIDeleteUser(Resource):
    @jwt_required()
    @admin_required()
    @parameters(
        type="object",
        properties={
            "user_ids": {"type": "string"},
        },
        required=["user_ids"],
    )
    def post(self, args):
        try:
            user_ids = args.get("user_ids", "")
            # Chuyển chuỗi user_ids thành list các integer
            if not user_ids:
                return Response(
                    message="No user_ids provided",
                    code=201,
                ).to_dict()

            # Tách chuỗi và convert sang list integer
            id_list = [int(id.strip()) for id in user_ids.split(",")]

            if not id_list:
                return Response(
                    message="Invalid user_ids format",
                    code=201,
                ).to_dict()

            process_delete = UserService.delete_users_by_ids(id_list)
            if process_delete == 1:
                message = "Delete user Success"
            else:
                message = "사용자 삭제 중 오류"
                return Response(
                    message=message,
                    code=201,
                ).to_dict()

            return Response(message=message, code=200, data=id_list).to_dict()

        except Exception as e:
            logger.error(f"Exception: Delete user Fail  :  {str(e)}")
            return Response(
                message="사용자 삭제 중 오류",
                code=201,
            ).to_dict()


@ns.route("/socialposts")
class APISocialPost(Resource):
    @jwt_required()
    @admin_required()
    def get(self):
        filters = request.args.to_dict()  # Convert query string to dict
        data = SocialPostService.getTotalRunning(filters)
        return Response(message="", code=200, data=data).to_dict()



@ns.route("/report_dashboard")
class APIReportDashboard(Resource):
    @jwt_required()
    @admin_required()
    def get(self):
        selected_date_type = request.args.get("selected_date_type", "", type=str)
        from_date = request.args.get("from_date", "", type=str)
        to_date = request.args.get("to_date", "", type=str)
        data_search = {
            "type" : "user",
            "type_2" : "NEW_USER",
            "time_range" : selected_date_type,
            "from_date" : from_date,
            "to_date" : to_date,
        }
        new_users = UserService.report_user_by_type(data_search)
        logger.info(new_users)
        data = {} 
        data['new_users'] = new_users

        return Response(message="", code=200, data=data).to_dict()

@ns.route("/logs")
class GetListFileLogs(Resource):
    def get(self):
        try:
            log_files = []
            for idx, f in enumerate(os.listdir(LOG_DIR), start=1):
                file_path = os.path.join(LOG_DIR, f)
                if os.path.isfile(file_path):
                    modified_time = os.path.getmtime(file_path)
                    log_files.append(
                        {
                            "id": idx,
                            "filename": f,
                            "modified": datetime.fromtimestamp(modified_time).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        }
                    )

            # Sắp xếp theo thời gian cập nhật giảm dần
            log_files.sort(key=lambda x: x["modified"], reverse=True)

            # Cập nhật lại id sau sort
            for i, item in enumerate(log_files, start=1):
                item["id"] = i

            return {
                "status": True,
                "message": "Success",
                "total": len(log_files),
                "page": 1,
                "per_page": 100,
                "total_pages": 1,
                "data": log_files,
            }, 200

        except Exception as e:
            return Response(message=str(e), code=500).to_dict()


@ns.route("/logs/<path:filename>")
class GetDetailLog(Resource):
    def get(self, filename):
        try:
            file_path = os.path.join(LOG_DIR, filename)

            if not os.path.abspath(file_path).startswith(os.path.abspath(LOG_DIR)):
                return Response(
                    message="Không được phép truy cập file ngoài thư mục logs", code=403
                ).to_dict()

            if not os.path.isfile(file_path):
                return Response(message="File không tồn tại", code=404).to_dict()

            # Optional: hỗ trợ query param ?tail=100
            tail_lines = request.args.get("tail", default=None, type=int)

            with open(file_path, "r", encoding="utf-8") as f:
                if tail_lines:
                    # Đọc dòng cuối file
                    from collections import deque

                    lines = deque(f, maxlen=tail_lines)
                    content = "".join(lines)
                else:
                    content = f.read()

            return content, 200, {"Content-Type": "text/plain; charset=utf-8"}

        except Exception as e:
            return Response(message=str(e), code=500).to_dict()

    @ns.route("/referral_histories")
    class APIAdminReferralHistories(Resource):
        @jwt_required()
        @admin_required()
        def get(self):
            page = request.args.get("page", const.DEFAULT_PAGE, type=int)
            per_page = request.args.get("per_page", const.DEFAULT_PER_PAGE, type=int)
            status = request.args.get("status", const.UPLOADED, type=int)
            type_order = request.args.get("type_order", "", type=str)
            type_post = request.args.get("type_post", "", type=str)
            time_range = request.args.get("time_range", "", type=str)
            type_status = request.args.get("type_status", "", type=str)
            search_key = request.args.get("search_key", "", type=str)
            from_date = request.args.get("from_date", "", type=str)
            to_date = request.args.get("to_date", "", type=str)
            data_search = {
                "page": page,
                "per_page": per_page,
                "status": status,
                "type_order": type_order,
                "type_post": type_post,
                "time_range": time_range,
                "type_status": type_status,
                "search_key": search_key,
                "from_date": from_date,
                "to_date": to_date,
            }
            billings = ReferralService.get_admin_referral_history(data_search)
            return {
                "status": True,
                "message": "Success",
                "total": billings.total,
                "page": billings.page,
                "per_page": billings.per_page,
                "total_pages": billings.pages,
                "data": [post.to_dict() for post in billings.items],
            }, 200

    @ns.route("/delete_referral_history")
    class APIAdminDeleteReferralHistory(Resource):
        @jwt_required()
        @admin_required()
        @parameters(
            type="object",
            properties={
                "post_ids": {"type": "string"},
            },
            required=["post_ids"],
        )
        def post(self, args):
            try:
                post_ids = args.get("post_ids", "")
                # Chuyển chuỗi post_ids thành list các integer
                if not post_ids:
                    return Response(
                        message="No post_ids provided",
                        code=201,
                    ).to_dict()

                # Tách chuỗi và convert sang list integer
                id_list = [int(id.strip()) for id in post_ids.split(",")]

                if not id_list:
                    return Response(
                        message="Invalid post_ids format",
                        code=201,
                    ).to_dict()

                process_delete = ReferralService.admin_delete_by_ids(id_list)
                if process_delete == 1:
                    message = "Delete Referral Success"
                else:
                    message = "Delete Referral Fail"

                return Response(
                    message=message,
                    code=200,
                ).to_dict()

            except Exception as e:
                logger.error(f"Exception: Delete Referral Fail  :  {str(e)}")
                return Response(
                    message="Delete Referral Fail",
                    code=201,
                ).to_dict()

    @ns.route("/user_change_password")
    class APIAdminChangePassword(Resource):
        @jwt_required()
        @admin_required()
        def get(self):
            userId = request.args.get("userId", "", type=str)
            random_string = "".join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(60)
            )

            UserService.update_user(userId, password=random_string)
            fe_current_domain = os.environ.get("FE_DOMAIN") or "https://toktak.ai"
            url_return = (
                f"{fe_current_domain}/auth/loginadmin?random_string={random_string}"
            )
            return Response(
                data={"userId": userId, "url_return": url_return},
                message="Đăng nhập thành công",
            ).to_dict()


@ns.route("/user/detail/<path:id>")
class APIUserDetailById(Resource):

    @jwt_required()
    @admin_required()
    def get(self, id):

        user = UserService.find_user(id)
        return Response(
            data=user._to_json(),
            message="Get User Info",
        ).to_dict()


@ns.route("/user/save")
class APIAdminSaveUser(Resource):
    @jwt_required()
    @admin_required()
    @parameters(
        type="object",
        properties={
            "id": {"type": ["integer", "null"]},
            "phone": {"type": ["string", "null"]},
            "subscription": {"type": ["string", "null"]},
            "subscription_expired": {"type": ["string", "null"]},
            "batch_total": {"type": ["integer", "null"]},
            "batch_remain": {"type": ["integer", "null"]},
            "total_link_active": {"type": ["integer", "null"]},
        },
        required=["id"],
    )
    def post(self, args):
        try:
            userId = args.get("id", 0)
            phone = args.get("phone", "")
            subscription = args.get("subscription", "")
            subscription_expired = args.get("subscription_expired", "")
            batch_total = args.get("batch_total", "")
            batch_remain = args.get("batch_remain", "")
            total_link_active = args.get("total_link_active", "")

            data_update = {
                "phone": phone,
                "subscription": subscription,
                "subscription_expired": subscription_expired,
                "batch_total": batch_total,
                "batch_remain": batch_remain,
                "total_link_active": total_link_active,
            }
            user_info = UserService.update_user(userId, **data_update)

            if subscription == "FREE":
                # update hết payment
                active = PaymentService.has_active_subscription(userId)
                if active:
                    end_date = datetime.now().date() - timedelta(days=1)
                    data_update_payment = {
                        "end_date": end_date,
                    }

                    payment = PaymentService.update_payment(
                        active.id, **data_update_payment
                    )

            return Response(
                # data=user_info,
                message="Updated User successfully",
            ).to_dict()
        except Exception as e:
            logger.error(f"Exception: Updated User Fail  :  {str(e)}")
            return Response(
                message="Updated User Fail",
                code=201,
            ).to_dict()


@ns.route("/download-excel")
class APIDownloadUserExcel(Resource):
    def post(self):
        try:
            data = request.get_json()
            type_order = data.get("type_order")
            type_post = data.get("type_post")
            time_range = data.get("time_range")
            search = data.get("search")
            member_type = data.get("member_type")
            status = data.get("status")

            data_search = {
                "page": 1,
                "per_page": 99999999999,
                "status": status,
                "type_order": type_order,
                "type_post": type_post,
                "time_range": time_range,
                "search": search,
                "member_type": member_type,
            }
            users = UserService.admin_search_users(data_search)

            data = users.items

            # Convert data thành DataFrame
            df = pd.DataFrame(
                [
                    {
                        "ID": u.id,
                        "Name": u.name,
                        "Email": u.email,
                        "Subscription": u.subscription,
                        "Created At": (
                            u.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            if u.created_at
                            else ""
                        ),
                        "Subscription Expired At": (
                            u.subscription_expired.strftime("%Y-%m-%d %H:%M:%S")
                            if u.subscription_expired
                            else ""
                        ),
                    }
                    for u in data
                ]
            )

            # Ghi vào bộ nhớ tạm
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Users")

            output.seek(0)

            filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message=f"download-excel.(Error code : ) {str(e)}",
                code=201,
            ).to_dict()
