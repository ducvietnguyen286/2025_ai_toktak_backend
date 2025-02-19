# coding: utf8
import json
from flask_restx import Namespace, Resource
from flask import request
from app.services.video_service import VideoService

from app.models.video_create import VideoCreate, db

ns = Namespace(name="video_maker", description="Video Maker API")


@ns.route("/video_status/<string:video_id>")
class VideoStatus(Resource):
    def get(self, video_id):
        # Giả lập trả về JSON cho video_id
        return {
            "status": "success",
            "video_id": video_id,
            "message": "Video status retrieved successfully XXXX TTTT XXX CCCC  TTT",
        }


@ns.route("/create_video")
class CreateVideo(Resource):
    def post(self):
        # Lấy dữ liệu từ request
        data = request.get_json()
        images_url = data["images_url"]  # Đây là một list các URL của hình ảnh

        if "product_name" not in data or "images_url" not in data:
            return {
                "message": "Missing required fields (product_name or images_url)"
            }, 400

        product_name = data["product_name"]

        if not isinstance(images_url, list):
            return {"message": "images_url must be a list of URLs"}, 400

        for url in images_url:
            if not isinstance(url, str):
                return {"message": "Each URL must be a string"}, 400

        result = VideoService.create_video_from_images(product_name, images_url)

        render_id = ""
        status = True
        message = f"Video  created successfully"
        if result["status_code"] == 200:
            render_id = result["response"]["id"]
            # Chèn vào bảng video_create với user_id = 0
            VideoService.create_create_video(
                render_id=render_id,
                user_id=0,
                product_name=product_name,
                images_url=json.dumps(images_url),
                description="",
            )
        else:
            status = False
            message = result["message"]

        return {
            "status": status,
            "message": message,
            "render_id": render_id,
        }
 
    @ns.route("/video_list")
    class VideoList(Resource):
        def get(self):
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 10, type=int)
            print("page", page)
            print("per_page", per_page)

            pagination = VideoService.get_videos(page, per_page)
            
            videos = [
                {
                    "id": video.id,
                    "user_id": video.user_id,
                    "product_name": video.product_name,
                    "images_url": video.images_url,
                    "status": video.status,
                    "description": video.description,
                    "created_at": video.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": video.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for video in pagination.items
            ]

            return {
                "status": True,
                "message": "Success",
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_pages": pagination.pages,
                "data": videos,
            }, 200