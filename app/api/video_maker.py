# coding: utf8
import json
from flask_restx import Namespace, Resource
from flask import request
from app.services.video_service import VideoService
from app.services.shotstack_services import ShotStackService
from app.services.post import PostService
from app.services.batch import BatchService
import random
from app.lib.logger import logger
from app.services.notification import NotificationServices
import datetime
import os
import requests

ns = Namespace(name="video_maker", description="Video Maker API")


@ns.route("/video_status/<string:render_id>")
class VideoStatus(Resource):
    def get(self, render_id):
        # Giả lập trả về JSON cho render_id

        result = VideoService.get_video_status(render_id)
        return result


@ns.route("/create_video")
class CreateVideo(Resource):
    def post(self):
        # Lấy dữ liệu từ request
        data = request.get_json()
        images_url = data["images_url"]  # Đây là một list các URL của hình ảnh
        images_slider_url = data[
            "images_slider_url"
        ]  # Đây là một list các URL của hình ảnh
        captions = data["captions"]  # Đây là một list các URL của hình ảnh

        if (
            "product_name" not in data
            or "images_url" not in data
            or "images_slider_url" not in data
        ):
            return {
                "message": "Missing required fields (product_name or images_url or images_slider_url)"
            }, 400

        product_name = data["product_name"]

        if not isinstance(images_url, list):
            return {"message": "images_url must be a list of URLs"}, 400

        for url in images_url:
            if not isinstance(url, str):
                return {"message": "Each URL must be a string"}, 400
        batch_id = random.randint(1, 10000)  # Chọn số nguyên từ 1 đến 100
        voice_google = random.randint(1, 4)  # Chọn số nguyên từ 1 đến 4

        result = ShotStackService.create_video_from_images_v2(
            batch_id,
            voice_google,
            product_name,
            images_url,
            images_slider_url,
            captions,
        )

        render_id = ""
        status = True
        message = "Video  created successfully"
        if result["status_code"] == 200:
            render_id = result["response"]["id"]
            # Chèn vào bảng video_create với user_id = 0
            VideoService.create_create_video(
                render_id=render_id,
                user_id=0,
                product_name=product_name,
                origin_caption=product_name,
                images_url=json.dumps(images_url),
                description="",
            )
        else:
            status = False
            message = result["message"]

        return {
            "batch_id": batch_id,
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

        videos = VideoService.get_videos(page, per_page)

        return {
            "status": True,
            "message": "Success",
            "total": videos.total,
            "page": videos.page,
            "per_page": videos.per_page,
            "total_pages": videos.pages,
            "data": [video.to_dict() for video in videos.items],
        }, 200


@ns.route("/shotstack_webhook")
class ShortstackWebhook(Resource):
    def post(self):
        try:
            # Lấy payload JSON từ request
            payload = request.get_json()
            if not payload:
                return {"message": "No JSON payload provided"}, 400

            # Lấy thông tin từ payload
            render_id = payload.get("id")
            status = payload.get("status")
            video_url = payload.get("url")
            action = payload.get("action")
            render = payload.get("render", "")

            # Ghi log thông tin nhận được
            logger.info("Received Shotstack webhook: %s", payload)
            create_video_detail = VideoService.update_video_create(
                render_id, status=status, video_url=video_url
            )
            batch_id = 0
            if create_video_detail:
                post_id = create_video_detail.post_id
                post_detail = PostService.find_post(post_id)
                if post_detail:
                    batch_id = post_detail.batch_id or "0"
                    PostService.update_post_by_batch_id(batch_id, video_url=video_url)

                    if status == "failed":
                        BatchService.update_batch(batch_id, status="2")
                        NotificationServices.create_notification(
                            user_id=post_detail.user_id,
                            batch_id=post_detail.batch_id,
                            title="⚠️ 비디오 생성에 실패했습니다. 다시 시도해주세요.",
                        )
                    else:
                        NotificationServices.create_notification(
                            user_id=post_detail.user_id,
                            batch_id=post_detail.batch_id,
                            title="🎥 비디오 생성이 완료되었습니다. 이제 공유할 수 있습니다.",
                        )

            if action == "copy":

                create_video_detail = VideoService.update_video_create(
                    render, google_driver_url=video_url, video_url=video_url
                )
                # if create_video_detail:
                # post_id = create_video_detail.post_id
                # post_detail = PostService.find_post(post_id)
                # if post_detail:
                #     batch_id = post_detail.batch_id or "0"
                #     PostService.update_post_by_batch_id(
                #         batch_id, video_url=video_url
                #     )

            # Trả về phản hồi JSON
            elif action == "render":
                file_download = download_video(video_url, post_id)
                if file_download:
                    PostService.update_post_by_batch_id(
                        batch_id, video_url=file_download
                    )

            return {
                "message": "Webhook received successfully",
                "render_id": render_id,
                "render": render,
                "status": status,
                "video_url": video_url,
                "batch_id": batch_id,
                # "post_detail" : post_detail.to_dict(),
                # "create_video_detail" : create_video_detail.to_dict(),
            }, 200

        except Exception as e:
            # Ghi log lỗi kèm stack trace
            logger.exception("Error processing webhook: %s", e)
            return {"message": "Internal Server Error"}, 500


@ns.route("/test_create_video")
class TestCreateVideo(Resource):
    def post(self):
        # Lấy dữ liệu từ request
        data = request.get_json()
        images_url = data["images_url"]  # Đây là một list các URL của hình ảnh
        prompts = data["prompts"]  # Đây là một list các URL của hình ảnh

        batch_id = random.randint(1, 10000)  # Chọn số nguyên từ 1 đến 100
        result = VideoService.test_create_video_from_images(
            batch_id, images_url, prompts
        )

        render_id = ""
        status = True
        message = "Video  created successfully"
        if result["status_code"] == 200:
            render_id = result["response"]["id"]
        else:
            status = False
            message = result["message"]

        return {
            "status": status,
            "message": message,
            "render_id": render_id,
        }


def download_video(video_url, post_id):
    try:
        # Tạo đường dẫn thư mục theo ngày và post_id
        today = datetime.datetime.now().strftime("%Y_%m_%d")
        save_dir = os.path.join("static", "voice", "gtts_voice", today, str(post_id))

        # Tạo thư mục nếu chưa có
        os.makedirs(save_dir, exist_ok=True)

        # Tên file video
        video_filename = os.path.join(save_dir, "downloaded_video.mp4")

        # Gửi request tải file
        response = requests.get(video_url, stream=True)
        response.raise_for_status()  # Kiểm tra lỗi HTTP

        # Ghi dữ liệu vào file
        with open(video_filename, "wb") as video_file:
            for chunk in response.iter_content(chunk_size=8192):
                video_file.write(chunk)


        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
        file_path = video_filename.replace("static/", "").replace("\\", "/")
        file_url = f"{current_domain}/{file_path}"
        return file_url

    except Exception as e:
        logger.exception("Error processing webhook download: %s", e)
        return None
