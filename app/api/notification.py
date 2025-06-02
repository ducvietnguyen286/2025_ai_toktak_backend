# coding: utf8
import time
import json
import os
from flask_restx import Namespace, Resource
from app.lib.logger import logger
from app.lib.response import Response
from app.services.notification import NotificationServices
from app.decorators import parameters, admin_required
from flask import request

from flask_jwt_extended import jwt_required
from app.services.auth import AuthService
import const

ns = Namespace(name="notification", description="Notification API")


@ns.route("/histories")
class APINotificationHistories(Resource):
    @jwt_required()
    def get(self):
        try:
            current_user = AuthService.get_current_identity()
            page = request.args.get("page", const.DEFAULT_PAGE, type=int)
            per_page = request.args.get("per_page", const.DEFAULT_PER_PAGE, type=int)
            status = request.args.get("status", const.UPLOADED, type=int)
            type_order = request.args.get("type_order", "", type=str)
            type_post = request.args.get("type_post", "", type=str)
            time_range = request.args.get("time_range", "", type=str)
            data_search = {
                "page": page,
                "per_page": per_page,
                "status": status,
                "type_order": type_order,
                "type_post": type_post,
                "time_range": time_range,
                "user_id": current_user.id,
            }
            result = NotificationServices.get_notifications(data_search)
            return {
                "current_user": current_user.id,
                "status": True,
                "message": "Success",
                "total": result.get("total", 0),
                "page": result.get("page", 0),
                "per_page": result.get("per_page", 0),
                "total_pages": result.get("pages", 0),
                "data": [post._to_json() for post in result.get("items", [])],
            }, 200
        except Exception as e:
            logger.error(f"Exception: Get Notification Fail  :  {str(e)}")
            return Response(
                message="Get Notification Fail",
                code=201,
            ).to_dict()


@ns.route("/delete_notification")
class APIDeleteNotification(Resource):
    @jwt_required()
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

            process_delete = NotificationServices.delete_posts_by_ids(id_list)
            if process_delete == 1:
                message = "Delete Post Success"
            else:
                message = "Delete Post Fail"

            return Response(
                message=message,
                code=200,
            ).to_dict()

        except Exception as e:
            logger.error(f"Exception: Delete Post Fail  :  {str(e)}")
            return Response(
                message="Delete Post Fail",
                code=201,
            ).to_dict()


@ns.route("/get_total_unread_notification")
class APIGetTotalNotification(Resource):
    @jwt_required()
    def get(self):
        current_user = AuthService.get_current_identity()
        data_search = {
            "user_id": current_user.id,
            "type_read": "0",
        }
        total_pages = NotificationServices.getTotalNotification(data_search)
        return Response(
            data={"total_pages": total_pages},
            message="Get Total Notification",
        ).to_dict()


@ns.route("/update_read_notification")
class APIUpdateReadNotification(Resource):
    @jwt_required()
    def post(self):
        try:
            current_user = AuthService.get_current_identity()
            user_id = current_user.id

            NotificationServices.update_post_by_user_id(user_id, is_read=1)
            message = "Update Notification Successfully"

            return Response(
                # data={"user_id": user_id},
                message=message,
                code=200,
            ).to_dict()

        except Exception as e:
            logger.error(f"Exception: Update Notification Fail  :  {str(e)}")
            return Response(
                message="Update Notification Fail",
                code=201,
            ).to_dict()


@ns.route("/admin/histories")
class APIAdminNotificationHistories(Resource):
    @jwt_required()
    @admin_required()
    def get(self):
        page = request.args.get("page", const.DEFAULT_PAGE, type=int)
        per_page = request.args.get("per_page", const.DEFAULT_PER_PAGE, type=int)
        status = request.args.get("status", const.UPLOADED, type=int)
        type_order = request.args.get("type_order", "", type=str)
        type_post = request.args.get("type_post", "", type=str)
        time_range = request.args.get("time_range", "", type=str)
        type_notification = request.args.get("type_notification", "", type=str)
        search_key = request.args.get("search_key", "", type=str)
        data_search = {
            "page": page,
            "per_page": per_page,
            "status": status,
            "type_order": type_order,
            "type_post": type_post,
            "time_range": time_range,
            "type_notification": type_notification,
            "search_key": search_key,
        }
        result = NotificationServices.get_admin_notifications(data_search)
        return {
            "status": True,
            "message": "Success",
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"],
            "total_pages": result["pages"],
            "data": [item._to_json() for item in result["items"]],
        }, 200


@ns.route("/admin/delete_notification")
class APIAdminDeleteNotification(Resource):
    @jwt_required()
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

            process_delete = NotificationServices.delete_posts_by_ids(id_list)
            if process_delete == 1:
                message = "Delete Post Success"
            else:
                message = "Delete Post Fail"

            return Response(
                message=message,
                code=200,
            ).to_dict()

        except Exception as e:
            logger.error(f"Exception: Delete Post Fail  :  {str(e)}")
            return Response(
                message="Delete Post Fail",
                code=201,
            ).to_dict()
