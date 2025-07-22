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
from flask_jwt_extended import jwt_required
from app.services.auth import AuthService

from datetime import datetime, date
import time
import os
import requests
from pathlib import Path
from app.services.user import UserService
from app.services.product import ProductService
import const
from app.extensions import redis_client
from gevent import sleep


ns = Namespace(name="video_maker", description="Video Maker API")


@ns.route("/video_status/<string:render_id>")
class VideoStatus(Resource):

    def get(self, render_id):
        # Giả lập trả về JSON cho render_id

        result = VideoService.get_video_status(render_id)
        return result


@ns.route("/create_video")
class CreateVideo(Resource):
    @jwt_required()
    def post(self):
        # Lấy dữ liệu từ request

        user_id_login = AuthService.get_user_id()

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
        batch_type = const.TYPE_NORMAL
        post_types = ["video", "image", "blog"]
        voice = 2
        voice_typecast = ""
        is_paid_advertisements = 0
        is_advance = 0
        template_info = get_template_info(is_advance, is_paid_advertisements)
        batch = BatchService.create_batch(
            user_id=user_id_login,
            url=url,
            shorten_link="",
            thumbnail=images_url,
            thumbnails=json.dumps(images_slider_url),
            content=json.dumps(data),
            type=batch_type,
            count_post=len(post_types),
            status=const.PENDING_STATUS,
            process_status="PENDING",
            voice_google=voice,
            voice_typecast=voice_typecast,
            is_paid_advertisements=is_paid_advertisements,
            is_advance=is_advance,
            template_info=template_info,
        )

        post = PostService.create_post(
            user_id=user_id_login,
            batch_id=batch.id,
            type="video",
            status=const.PENDING_STATUS,
        )

        voice_google = random.randint(1, 4)  # Chọn số nguyên từ 1 đến 4

        post_id = post.id
        batch_id = batch.id
        batch_content = json.loads(batch.content)

        gifs = batch_content.get("gifs", [])
        if gifs:
            images_slider_url = gifs + images_slider_url

        product_video_url = batch_content.get("video_url", "")

        if product_video_url != "":
            images_slider_url.insert(0, product_video_url)

        data_make_video = {
            "post_id": post.id,
            "batch_id": batch.id,
            "is_advance": batch.is_advance,
            "batch_type": batch.type,
            "template_info": batch.template_info,
            "voice_google": voice_google,
            "origin_caption": product_name,
            "images_url": images_url,
            "images_slider_url": images_slider_url,
            "product_video_url": product_video_url,
            "voice_typecast": batch.voice_typecast,
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
            "data_make_video": data_make_video,
            "post_id": post_id,
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
            batch_id = request.args.get("batch_id", 1, type=int)
            is_s3 = request.args.get("is_s3", 0, type=int)
            log_webhook_message(
                f"Received Shotstack batch_id: {batch_id}  is_s3: {is_s3}"
            )
            payload = request.get_json()

            # Ghi log thông tin nhận được
            log_webhook_message(f"Received Shotstack webhook: {payload}")
            if not payload:
                return {"message": "No JSON payload provided"}, 400

            # Lấy thông tin từ payload
            render_id = payload.get("id")
            status = payload.get("status")
            url_download = payload.get("url")
            action = payload.get("action")
            render = payload.get("render", "")
            error = payload.get("error", "")
            user_id = 0
            video_url = ""

            redis_key = f"shotstack_webhook_lock:{render_id}"
            if redis_client.exists(redis_key):
                log_webhook_message(
                    f"Webhook duplicate! render_id={render_id} đã xử lý trước đó."
                )
                return {
                    "message": "Webhook already processed",
                    "render_id": render_id,
                }, 200

            if is_s3 == 1:
                if action == "copy":
                    url_s3 = request.args.get("url_s3", "", type=str)
                    log_webhook_message(f"url_s3: {url_s3}")
                    if is_s3_file_public(url_s3):
                        redis_client.setex(redis_key, 600, "1")
                        video_url = url_s3

            else:
                if action == "render" and url_download != "":
                    if is_s3_file_public(url_download):
                        redis_client.setex(redis_key, 600, "1")
                        video_url = url_download

            if video_url != "":
                create_video_detail = VideoService.update_video_create(
                    render_id, status=status, video_url=video_url
                )
                if create_video_detail:
                    post_id = create_video_detail.post_id
                    post_detail = PostService.find_post(post_id)
                    if post_detail:
                        batch_id = post_detail.batch_id
                        user_id = post_detail.user_id
                        # PostService.update_post_by_batch_id(batch_id, video_url=video_url)

                        if status == "failed":
                            BatchService.update_batch(batch_id, status="2")
                            data_update = {
                                "notification_type": "shortstack_video",
                                "render_id": render_id,
                                "user_id": post_detail.user_id,
                                "batch_id": post_detail.batch_id,
                                "status": const.NOTIFICATION_FALSE,
                                "title": "⚠️ 비디오 생성에 실패했습니다. 다시 시도해주세요.",
                                "description": f"AI Shotstack  {str(error)}",
                            }
                        else:
                            data_update_batch = {
                                "status": const.DRAFT_STATUS,
                                "process_status": "DRAFT",
                            }
                            BatchService.update_batch(batch_id, **data_update_batch)
                            data_update = {
                                "notification_type": "shortstack_video",
                                "render_id": render_id,
                                "user_id": post_detail.user_id,
                                "batch_id": post_detail.batch_id,
                                "title": "🎥 비디오 생성이 완료되었습니다. 이제 공유할 수 있습니다.",
                                "description": json.dumps(payload),
                            }
                        NotificationServices.create_notification_render_id(
                            **data_update
                        )
                file_download_attr = download_video(video_url, batch_id)
                if file_download_attr:
                    file_path = file_download_attr["file_path"]
                    file_download = file_download_attr["file_download"]
                    PostService.update_post_by_batch_id(
                        batch_id,
                        video_url=video_url,
                        video_path=file_path,
                        status=const.DRAFT_STATUS,
                    )

                    check_and_update_user_batch_remain(user_id, batch_id)

            return {
                "message": "Webhook received successfully",
                "render_id": render_id,
                "render": render,
                "status": status,
                "video_url": video_url,
                "batch_id": str(batch_id),
                # "post_detail" : post_detail.to_dict(),
                # "create_video_detail" : create_video_detail.to_dict(),
            }, 200

        except Exception as e:
            # Ghi log lỗi kèm stack trace
            log_webhook_message(f"Error processing webhook: {e}")
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
    IS_MOUNT = int(os.environ.get("IS_MOUNT", 0))

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
                    f"❌ URL không phải (lần thử {attempt}/{MAX_RETRIES} video: batch_id: {batch_id} : {video_url} (Content-Type: {content_type})"
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
                f"✅ Đã tải file video (lần thử {attempt}/{MAX_RETRIES} batch_id: {batch_id} : {video_filename}"
            )
            file_path = os.path.relpath(video_filename, "static").replace("\\", "/")
            file_download = f"{current_domain}/{file_path}"
            if IS_MOUNT == 1:
                video_filename = (
                    Path(video_filename).as_posix().replace("static/voice", "/mnt")
                )

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
                f"🚫 Không kết nối được tới máy chủ (lần thử {attempt}/{MAX_RETRIES} batch_id: {batch_id} : {video_url} - Error: {e}"
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
            sleep(RETRY_DELAY)

    log_webhook_message(
        f"❌ Tải video thất bại batch_id: {batch_id} sau {MAX_RETRIES} lần: {video_url}"
    )
    return None


def check_and_update_user_batch_remain(user_id: int, batch_id: int):
    redis_key = f"user_batch_remain_updated:{user_id}:{batch_id}"

    try:
        # Nếu đã cập nhật rồi trong 5 phút, thì không làm gì
        if redis_client.exists(redis_key):
            return False  # Đã cập nhật rồi

        current_user = UserService.find_user_with_out_session(user_id)
        if not current_user:
            return False  # Không tìm thấy user

        batch_remain = current_user.batch_remain
        subscription = current_user.subscription
        subscription_expired = current_user.subscription_expired
        total_link_active = current_user.total_link_active
        new_batch_remain = max(current_user.batch_remain - 1, 0)

        log_webhook_message(
            f"[Cap Nhat batch_remain  ] user_id={user_id}, batch_id={batch_id}, batch_remain={batch_remain}, new_batch_remain={new_batch_remain}"
        )

        UserService.update_user(user_id, batch_remain=new_batch_remain)

        data_user_history = {
            "user_id": user_id,
            "batch_id": batch_id,
            "subscription": subscription,
            "subscription_expired": subscription_expired,
            "old_batch_remain": batch_remain,
            "new_batch_remain": new_batch_remain,
            "total_link_active": total_link_active,
            "description": f"[Cap Nhat batch_remain  ] user_id={user_id}, batch_id={batch_id}, batch_remain={batch_remain}, new_batch_remain={new_batch_remain}",
        }

        UserService.create_coupon_user_histories(**data_user_history)

        # Đặt key trong Redis với TTL là 5 phút (300 giây)
        redis_client.setex(redis_key, 3000, "1")
        return True  # Đã cập nhật thành công

    except Exception as e:
        # Log lỗi nếu cần
        log_webhook_message(
            f"[Redis/UserService Error] user_id={user_id}, batch_id={batch_id}, error={str(e)}"
        )
        return False  # Báo lỗi chung


def is_s3_file_public(s3_url):
    """Check S3 file (public) tồn tại không qua HTTP HEAD."""
    resp = requests.head(s3_url)
    return resp.status_code == 200


def get_template_info(is_advance, is_paid_advertisements):
    if is_advance:
        return json.dumps({})

    redis_key = "template_image_default"

    template_image_default = redis_client.get(redis_key)
    if template_image_default:
        return json.dumps(
            {
                "image_template_id": template_image_default.decode(),
                "is_paid_advertisements": is_paid_advertisements,
            }
        )
