# coding: utf8
import json
from flask_restx import Namespace, Resource
from flask import request
from app.services.video_service import VideoService
from app.services.shotstack_services import ShotStackService
from app.services.post import PostService
from app.services.batch import BatchService
import random
from app.lib.logger import logger, log_webhook_message
from app.services.notification import NotificationServices

from datetime import datetime, date
import time
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

        post_id = data["post_id"]
        post = PostService.find_post(post_id)
        batch = BatchService.find_batch(post.batch_id)

        data_make_video = {
            "post_id": post.id,
            "batch_id": batch.id,
            "is_advance": batch.is_advance,
            "template_info": batch.template_info,
            "voice_google": voice_google,
            "origin_caption": product_name,
            "images_url": images_url,
            "images_slider_url": images_slider_url,
        }

        result = ShotStackService.create_video_from_images_v2(data_make_video)

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

            batch_id = 0
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
            if create_video_detail:
                post_id = create_video_detail.post_id
                post_detail = PostService.find_post(post_id)
                if post_detail:
                    batch_id = post_detail.batch_id or "0"
                    # PostService.update_post_by_batch_id(batch_id, video_url=video_url)

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
                    render,
                    google_driver_url=video_url,
                    video_url=video_url,
                    video_path=video_url,
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
                if video_url != "":
                    file_download_attr = download_video(video_url, batch_id)
                    if file_download_attr:
                        file_path = file_download_attr["file_path"]
                        file_download = file_download_attr["file_download"]
                        PostService.update_post_by_batch_id(
                            batch_id,
                            video_url=video_url,
                            video_path=file_path,
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


def download_video(video_url, batch_id):
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # giây
    TIMEOUT = 20  # giây

    # Lấy ngày hiện tại (YYYY_MM_DD)
    today = date.today().strftime("%Y_%m_%d")
    save_dir = os.path.join("static", "voice", "gtts_voice", today, str(batch_id))
    os.makedirs(save_dir, exist_ok=True)

    # Thêm timestamp vào tên file để tránh trùng lặp
    timestamp = datetime.now().strftime("%H%M%S")
    video_filename = os.path.join(save_dir, f"{batch_id}_video_{timestamp}.mp4")

    # Domain hiện tại
    current_domain = os.environ.get("CURRENT_DOMAIN", "http://localhost:5000")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(
                video_url, stream=True, headers=headers, timeout=TIMEOUT
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "video" not in content_type:
                log_webhook_message(
                    f"❌ URL không phải video: batch_id: {batch_id} : {video_url} (Content-Type: {content_type})"
                )
                return None

            with open(video_filename, "wb") as video_file:
                for chunk in response.iter_content(chunk_size=16384):
                    if chunk:
                        video_file.write(chunk)

            # Kiểm tra kích thước file
            size = os.path.getsize(video_filename)
            if size < 1024:  # <1KB
                log_webhook_message(
                    f"⚠️ Video tải về quá nhỏ ({size} bytes), có thể lỗi: batch_id: {batch_id} : {video_filename}"
                )
                return None

            # Thành công
            log_webhook_message(
                f"✅ Đã tải file video batch_id: {batch_id} : {video_filename}"
            )
            file_path = os.path.relpath(video_filename, "static").replace("\\", "/")
            file_download = f"{current_domain}/{file_path}"

            return {
                "file_path": video_filename,
                "file_download": file_download,
            }

        except requests.exceptions.Timeout:
            log_webhook_message(
                f"⚠️ Timeout khi tải video batch_id: {batch_id} (lần thử {attempt}/{MAX_RETRIES}): {video_url}"
            )
        except requests.exceptions.ConnectionError as e:
            log_webhook_message(
                f"🚫 Không kết nối được tới máy chủ batch_id: {batch_id} : {video_url} - Error: {e}"
            )
        except requests.exceptions.RequestException as e:
            log_webhook_message(
                f"⚠️ Lỗi khi tải video batch_id: {batch_id} (lần thử {attempt}/{MAX_RETRIES}): {video_url} - Error: {e}"
            )
        except Exception as e:
            log_webhook_message(
                f"❌ Lỗi hệ thống khi tải video batch_id: {batch_id} : {e}"
            )

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    log_webhook_message(
        f"❌ Tải video thất bại batch_id: {batch_id} sau {MAX_RETRIES} lần: {video_url}"
    )
    return None
