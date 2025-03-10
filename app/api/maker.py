# coding: utf8
import time
import json
import os
from flask_restx import Namespace, Resource
from app.ais.chatgpt import (
    call_chatgpt_create_caption,
    call_chatgpt_create_blog,
    call_chatgpt_create_social,
)
from app.decorators import jwt_optional, parameters
from app.lib.logger import logger
from app.lib.response import Response
from app.lib.string import split_text_by_sentences
from app.makers.images import ImageMaker
from app.makers.videos import MakerVideo
from app.scraper import Scraper
import traceback

from app.services.batch import BatchService
from app.services.post import PostService
from app.services.social_post import SocialPostService
from app.services.video_service import VideoService
from flask import request

from flask_jwt_extended import jwt_required
from app.services.auth import AuthService
import const

ns = Namespace(name="maker", description="Maker API")


@ns.route("/create-batch")
class APICreateBatch(Resource):

    @parameters(
        type="object",
        properties={
            "url": {"type": "string"},
        },
        required=["url"],
    )
    def post(self, args):
        try:
            user_id_login = 0
            current_user = AuthService.get_current_identity() or None
            if current_user:
                user_id_login = current_user.id
            url = args.get("url", "")
            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
            UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
            max_count_image = os.environ.get("MAX_COUNT_IMAGE") or "8"
            max_count_image = int(max_count_image)

            data = Scraper().scraper({"url": url})

            if not data:
                return Response(
                    message="상품의 URL을 분석할 수 없어요.",
                    code=201,
                ).to_dict()

            images = data.get("images", [])

            thumbnail_url = data.get("image", "")
            thumbnails = data.get("thumbnails", [])

            if images and len(images) > max_count_image:
                images = images[:max_count_image]

            data["images"] = images
            if "text" not in data:
                data["text"] = ""
            if "iframes" not in data:
                data["iframes"] = []

            # TODO: Save images
            # image_paths = []
            # for index, image_url in enumerate(images):
            #     timestamp = int(time.time())
            #     unique_id = uuid.uuid4().hex
            #     image_ext = image_url.split(".")[-1]

            #     file_name = f"{timestamp}_{unique_id}.{image_ext}"

            #     image_path = f"{UPLOAD_FOLDER}/{file_name}"
            #     with open(image_path, "wb") as image_file:
            #         image_file.write(requests.get(image_url).content)
            #     image_paths.append(f"{current_domain}/files/{file_name}")
            # data["images"] = image_paths

            post_types = ["video", "image", "blog"]

            batch = BatchService.create_batch(
                user_id=user_id_login,
                url=url,
                thumbnail=thumbnail_url,
                thumbnails=json.dumps(thumbnails),
                content=json.dumps(data),
                type=1,
                count_post=len(post_types),
                status=0,
                process_status="PENDING",
            )

            posts = []
            for post_type in post_types:
                post = PostService.create_post(
                    user_id=user_id_login, batch_id=batch.id, type=post_type, status=0
                )

                post_res = post._to_json()
                post_res["url_run"] = (
                    f"{current_domain}/api/v1/maker/make-post/{post.id}"
                )
                posts.append(post_res)

            batch_res = batch._to_json()
            batch_res["posts"] = posts

            return Response(
                data=batch_res,
                message="제품 정보를 성공적으로 가져왔습니다.",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="상품 정보를 불러올 수 없어요.(Error code : )",
                status=400,
                code=201,
            ).to_dict()


@ns.route("/test-create-video/<int:id>")
class APITestCreateVideo(Resource):

    def post(self, id):
        try:
            post = PostService.find_post(id)
            batch = BatchService.find_batch(post.batch_id)
            data = json.loads(batch.content)
            images = data.get("images", [])

            thumbnails = batch.thumbnails

            need_count = 5

            process_images = json.loads(thumbnails)
            if process_images and len(process_images) < need_count:
                current_length = len(process_images)
                need_length = need_count - current_length
                process_images = process_images + images[:need_length]
            elif process_images and len(process_images) >= need_count:
                process_images = process_images[:need_count]
            else:
                process_images = images
                process_images = process_images[:need_count]

            response = None
            captions = []
            response = call_chatgpt_create_caption(process_images, data, post.id)
            if response:
                parse_caption = json.loads(response)
                parse_response = parse_caption.get("response", {})

                captions = parse_response.get("captions", [])

                video_path = MakerVideo().make_video_with_moviepy(
                    process_images, captions
                )

                visual_path_1 = os.path.join(os.getcwd(), "uploads", "visual_1.mp4")
                visual_path_2 = os.path.join(os.getcwd(), "uploads", "visual_2.mp4")

                merged_video_path = MakerVideo().merge_videos(
                    [visual_path_1, video_path, visual_path_2]
                )

            return Response(
                data={
                    "video_path": video_path,
                    "merged_video_path": merged_video_path,
                },
                message="비디오 생성이 성공적으로 완료되었습니다.",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Tạo video that bai",
                status=200,
                code=201,
            ).to_dict()


@ns.route("/make-post/<int:id>")
class APIMakePost(Resource):

    def post(self, id):
        try:
            current_user_id = 0
            current_user = AuthService.get_current_identity() or None
            if current_user:
                current_user_id = current_user.id

            message = "Tạo post thành công"
            post = PostService.find_post(id)
            if not post:
                return Response(
                    message="Post không tồn tại",
                    status=201,
                ).to_dict()
            batch = BatchService.find_batch(post.batch_id)
            if not batch:
                return Response(
                    message="Batch không tồn tại",
                    status=201,
                ).to_dict()

            if batch.status == 1 or post.status == 1:
                return Response(
                    message="Post đã được tạo",
                    status=201,
                ).to_dict()

            data = json.loads(batch.content)
            images = data.get("images", [])
            thumbnails = batch.thumbnails

            need_count = 5

            process_images = json.loads(thumbnails)
            if process_images and len(process_images) < need_count:
                current_length = len(process_images)
                need_length = need_count - current_length
                process_images = process_images + images[:need_length]
            elif process_images and len(process_images) >= need_count:
                process_images = process_images[:need_count]
            else:
                process_images = images
                process_images = process_images[:need_count]

            type = post.type

            response = None
            render_id = ""
            hooking = []
            maker_images = []
            captions = []
            thumbnail = batch.thumbnail

            if type == "video":
                response = call_chatgpt_create_caption(process_images, data, post.id)
                if response:
                    parse_caption = json.loads(response)
                    parse_response = parse_caption.get("response", {})
                    logger.info("parse_response: {0}".format(parse_response))

                    caption = parse_response.get("caption", "")
                    origin_caption = caption
                    hooking = parse_response.get("hooking", [])

                    captions = split_text_by_sentences(caption, len(process_images))

                    for image_url in process_images:
                        maker_image = ImageMaker.save_image_for_short_video(image_url)
                        maker_images.append(maker_image)

                    # Tạo video từ ảnh
                    if len(maker_images) > 0:
                        image_renders = maker_images[:1]  # Lấy tối đa 3 Ảnh đầu tiên
                        image_renders_sliders = maker_images[
                            :5
                        ]  # Lấy tối đa 5 Ảnh đầu tiên
                        caption_sliders = captions[:5]  # Lấy tối đa 5 Ảnh đầu tiên

                        product_name = data["name"]

                        # tạo từ gtts
                        # result = VideoService.create_video_from_images(
                        #     post.id,
                        #     origin_caption,
                        #     image_renders,
                        #     image_renders_sliders,
                        #     caption_sliders,
                        # )

                        # Tạo từ google
                        result = VideoService.create_video_from_images_v2(
                            post.id,
                            origin_caption,
                            image_renders,
                            image_renders_sliders,
                            caption_sliders,
                        )

                        logger.info("result: {0}".format(result))

                        if result["status_code"] == 200:
                            render_id = result["response"]["id"]

                            VideoService.create_create_video(
                                render_id=render_id,
                                user_id=current_user_id,
                                product_name=product_name,
                                images_url=json.dumps(image_renders),
                                description="",
                                origin_caption=origin_caption,
                                captions=json.dumps(caption_sliders),
                                post_id=post.id,
                            )
                        else:
                            return Response(
                                message=result["message"],
                                status=200,
                                code=201,
                            ).to_dict()

            elif type == "image":
                logger.info(
                    "-------------------- PROCESSING CREATE IMAGES -------------------"
                )
                response = call_chatgpt_create_social(process_images, data, post.id)
                if response:
                    parse_caption = json.loads(response)
                    parse_response = parse_caption.get("response", {})
                    captions = parse_response.get("caption", "")

                    for index, image_url in enumerate(process_images):
                        image_caption = captions[index] if index < len(captions) else ""
                        image_url = ImageMaker.save_image_and_write_text(
                            image_url, image_caption, font_size=80
                        )
                        maker_images.append(image_url)

                logger.info(
                    "-------------------- PROCESSED CREATE IMAGES -------------------"
                )
            elif type == "blog":
                logger.info(
                    "-------------------- PROCESSING CREATE LOGS -------------------"
                )
                response = call_chatgpt_create_blog(process_images, data, post.id)
                logger.info(
                    "-------------------- PROCESSED CREATE LOGS -------------------"
                )
            title = ""
            subtitle = ""
            content = ""
            video_url = ""
            hashtag = ""
            description = ""

            if response:
                parse_caption = json.loads(response)
                parse_response = parse_caption.get("response", {})

                if parse_response and "post" in parse_response:
                    content = parse_response.get("post", "")
                if parse_response and "description" in parse_response:
                    description = parse_response.get("description", "")
                    if "<" in description or ">" in description:
                        description = description.replace("<", "").replace(">", "")
                if parse_response and "title" in parse_response:
                    title = parse_response.get("title", "")
                if parse_response and "summarize" in parse_response:
                    subtitle = parse_response.get("summarize", "")
                if parse_response and "hashtag" in parse_response:
                    hashtag = parse_response.get("hashtag", "")
                if parse_response and "content" in parse_response:
                    content = parse_response.get("content", "")

                    blog_images = images
                    if blog_images and len(blog_images) < need_count:
                        current_length = len(blog_images)
                        need_length = need_count - current_length
                        blog_images = blog_images + process_images[:need_length]
                    elif blog_images and len(blog_images) >= need_count:
                        blog_images = blog_images[:need_count]
                    else:
                        blog_images = process_images
                        blog_images = blog_images[:need_count]

                    for index, image_url in enumerate(blog_images):
                        content = content.replace(f"IMAGE_URL_{index}", image_url)

            else:
                return Response(
                    message=f"Tạo {type} that bai.!",
                    status=200,
                    code=201,
                ).to_dict()

            post = PostService.update_post(
                post.id,
                thumbnail=thumbnail,
                images=json.dumps(maker_images),
                captions=json.dumps(captions),
                title=title,
                subtitle=subtitle,
                hooking=json.dumps(hooking),
                description=description,
                content=content,
                video_url=video_url,
                hashtag=hashtag,
                render_id=render_id,
                status=1,
                social_sns_description="[]",
            )
            current_done_post = batch.done_post

            batch = BatchService.update_batch(batch.id, done_post=current_done_post + 1)

            if batch.done_post == batch.count_post:
                BatchService.update_batch(batch.id, status=1)

            if type == "video":
                message = "비디오 생성이 성공적으로 완료되었습니다."
            elif type == "image":
                message = "이미지 생성이 성공적으로 완료되었습니다."
            elif type == "blog":
                message = "블로그 생성이 성공적으로 완료되었습니다."

            return Response(
                data=post._to_json(),
                message=message,
            ).to_dict()
        except Exception as e:
            logger.error(f"Exception: create {type} that bai  :  {str(e)}")
            traceback.print_exc()
            return Response(
                message=f"create {type} that bai...",
                status=200,
                code=201,
            ).to_dict()


@ns.route("/get-batch/<int:id>")
class APIGetBatch(Resource):

    def get(self, id):
        batch = BatchService.find_batch(id)
        if not batch:
            return Response(
                message="Batch không tồn tại",
                status=404,
            ).to_dict()

        posts = PostService.get_posts_by_batch_id(batch.id)

        batch_res = batch._to_json()
        batch_res["posts"] = posts

        return Response(
            data=batch_res,
            message="Lấy batch thành công",
        ).to_dict()


@ns.route("/batchs")
class APIBatchs(Resource):

    def get(self):

        user_id_login = 0
        current_user = AuthService.get_current_identity() or None
        if current_user:
            user_id_login = current_user.id

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        batches = BatchService.get_all_batches(page, per_page, user_id_login)

        return {
            "status": True,
            "message": "Success",
            "total": batches.total,
            "page": batches.page,
            "per_page": batches.per_page,
            "total_pages": batches.pages,
            "data": [batch_detail.to_dict() for batch_detail in batches.items],
        }, 200


@ns.route("/get-status-upload-with-batch-id/<int:id>")
class APIGetStatusUploadWithBatch(Resource):

    def get(self, id):
        batch = BatchService.find_batch(id)
        if not batch:
            return Response(
                message="Batch không tồn tại",
                status=404,
            ).to_dict()

        posts = PostService.get_posts_by_batch_id(batch.id)

        for post_detail in posts:
            post_id = post_detail["id"]

            social_post_detail = SocialPostService.by_post_id_get_latest_social_posts(
                post_id
            )
            post_detail["social_post_detail"] = social_post_detail
            PostService.update_post(
                post_id, social_sns_description=json.dumps(social_post_detail)
            )

        batch_res = batch._to_json()
        batch_res["posts"] = posts

        return Response(
            data=batch_res,
            message="Lấy batch thành công",
        ).to_dict()


@ns.route("/save_draft_batch/<int:id>")
class APIUpdateStatusBatch(Resource):
    @jwt_required()
    def post(self, id):
        try:
            current_user = AuthService.get_current_identity()
            message = "Update Batch Success"
            batch = BatchService.find_batch(id)
            if not batch:
                return Response(
                    message="Batch không tồn tại",
                    code=201,
                ).to_dict()

            batch_detail = BatchService.update_batch(
                batch.id, status=99, process_status="DRAFT"
            )

            PostService.update_post_by_batch_id(batch.id, status=const.DRAFT_STATUS)

            return Response(
                data=batch_detail.to_dict(),
                message=message,
                code=200,
            ).to_dict()
        except Exception as e:
            logger.error(f"Exception: Update Batch Fail  :  {str(e)}")
            return Response(
                message="Update Batch Fail",
                status=200,
                code=201,
            ).to_dict()


@ns.route("/histories")
class APIHistories(Resource):

    @jwt_required()
    def get(self):
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
        posts = PostService.get_posts_upload(data_search)
        return {
            "current_user": current_user.id,
            "status": True,
            "message": "Success",
            "total": posts.total,
            "page": posts.page,
            "per_page": posts.per_page,
            "total_pages": posts.pages,
            "data": [post._to_json() for post in posts.items],
        }, 200


@ns.route("/delete_post")
class APIDeletePostBatch(Resource):
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

            process_delete = PostService.delete_posts_by_ids(id_list)
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
