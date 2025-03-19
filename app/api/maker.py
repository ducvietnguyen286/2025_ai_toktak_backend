# coding: utf8
import time
import json
import os
from flask_restx import Namespace, Resource
from app.ais.chatgpt import (
    call_chatgpt_clear_product_name,
    call_chatgpt_create_caption,
    call_chatgpt_create_blog,
    call_chatgpt_create_social,
)
from app.decorators import jwt_optional, parameters
from app.lib.caller import get_shorted_link_coupang
from app.lib.logger import logger
from app.lib.response import Response
from app.lib.string import split_text_by_sentences, should_replace_shortlink
from app.makers.docx import DocxMaker
from app.makers.images import ImageMaker
from app.makers.videos import MakerVideo
from app.scraper import Scraper
import traceback

from app.services.batch import BatchService
from app.services.post import PostService
from app.services.social_post import SocialPostService
from app.services.video_service import VideoService
from app.services.shotstack_services import ShotStackService
from app.services.shorten_services import ShortenServices
from app.services.notification import NotificationServices

from flask import request

from flask_jwt_extended import jwt_required
from app.services.auth import AuthService
import const
from flask_jwt_extended import (
    verify_jwt_in_request,
)

ns = Namespace(name="maker", description="Maker API")


@ns.route("/create-batch")
class APICreateBatch(Resource):

    @parameters(
        type="object",
        properties={
            "url": {"type": "string"},
            "voice": {"type": ["string", "null"]},
        },
        required=["url"],
    )
    def post(self, args):
        try:

            verify_jwt_in_request(optional=True)
            user_id_login = 0
            current_user = AuthService.get_current_identity() or None
            if current_user:
                user_id_login = current_user.id
            url = args.get("url", "")
            voice = args.get("voice", 1)
            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
            max_count_image = os.environ.get("MAX_COUNT_IMAGE") or "8"
            max_count_image = int(max_count_image)

            data = Scraper().scraper({"url": url})

            if not data:
                return Response(
                    message="상품의 URL을 분석할 수 없어요.",
                    code=201,
                ).to_dict()

            shorten_link = ""

            # if "coupang.com" in url and "link.coupang.com" not in url:
            #     shorten_link = get_shorted_link_coupang(url)
            # elif "link.coupang.com" in url:
            #     shorten_link = url

            # Kiểm tra nếu URL đã tồn tại trong DB
            if should_replace_shortlink(url):
                existing_entry = ShortenServices.get_short_by_original_url(url)
                domain_share_url = "https://s.toktak.ai/"
                if not existing_entry:
                    short_code = ShortenServices.make_short_url(url)

                    existing_entry = ShortenServices.create_shorten(
                        original_url=url, short_code=short_code
                    )

                shorten_link = f"{domain_share_url}{existing_entry.short_code}"

            product_name = data.get("name", "")
            product_name_cleared = call_chatgpt_clear_product_name(product_name)
            if product_name_cleared:
                product_name_cleared = json.loads(product_name_cleared)
                res_product_name = product_name_cleared.get("response", "")
                data["name"] = res_product_name.get("product_name", "")

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

            post_types = ["video", "image", "blog"]

            batch = BatchService.create_batch(
                user_id=user_id_login,
                url=url,
                shorten_link=shorten_link,
                thumbnail=thumbnail_url,
                thumbnails=json.dumps(thumbnails),
                content=json.dumps(data),
                type=1,
                count_post=len(post_types),
                status=0,
                process_status="PENDING",
                voice_google=voice,
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

            NotificationServices.create_notification(
                user_id=user_id_login,
                batch_id=batch.id,
                title=f"제품 정보를 성공적으로 가져왔습니다. {url}",
            )

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


@ns.route("/update_template_video_user")
class APIUpdateTemplateVideoUser(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "batch_id": {"type": "integer"},
            "is_paid_advertisements": {"type": "integer"},
            "product_name": {"type": "string"},
            "is_product_name": {"type": "integer"},
            "purchase_guide": {"type": "string"},
            "is_purchase_guide": {"type": "integer"},
            "voice_gender": {"type": ["integer", "null"]},
            "voice_id": {"type": ["integer", "null"]},
            "is_video_hooking": {"type": ["integer", "null"]},
            "is_caption_top": {"type": ["integer", "null"]},
            "is_caption_last": {"type": ["integer", "null"]},
            "image_caption_type": {"type": ["integer", "null"]},
        },
        required=["batch_id"],
    )
    def post(self, args):
        try:
            logger.info(f"update template : {args}")
            is_paid_advertisements = args.get("is_paid_advertisements", 0)
            product_name = args.get("product_name", "")
            is_product_name = args.get("is_product_name", 0)
            purchase_guide = args.get("purchase_guide", "")
            is_purchase_guide = args.get("is_purchase_guide", 0)
            voice_gender = args.get("voice_gender", 0)
            voice_id = args.get("voice_id", 0)
            is_video_hooking = args.get("is_video_hooking", 0)
            is_caption_top = args.get("is_caption_top", 0)
            is_caption_last = args.get("is_caption_last", 0)
            image_caption_type = args.get("image_caption_type", 0)

            user_id_login = 0
            current_user = AuthService.get_current_identity() or None
            user_id_login = current_user.id
            user_template = PostService.get_template_video_by_user_id(user_id_login)
            if not user_template:
                user_template = PostService.create_user_template(
                    user_id=current_user.id
                )

            # user_template = PostService.up

            data_update = {
                "is_paid_advertisements": is_paid_advertisements,
                "product_name": product_name,
                "is_product_name": is_product_name,
                "purchase_guide": purchase_guide,
                "is_purchase_guide": is_purchase_guide,
                "voice_gender": voice_gender,
                "voice_id": voice_id,
                "is_video_hooking": is_video_hooking,
                "is_caption_top": is_caption_top,
                "is_caption_last": is_caption_last,
                "image_caption_type": image_caption_type,
            }

            logger.info(f"update template : {data_update}")

            user_template = PostService.update_template(user_template.id, **data_update)
            user_template_data = user_template.to_dict()
            return Response(
                data=user_template_data,
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

            verify_jwt_in_request(optional=True)
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
                if len(images) > need_length:
                    process_images = process_images + images[:need_length]
                else:
                    process_images = process_images + images
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
            blog_images = []
            thumbnail = batch.thumbnail
            file_size = 0
            mime_type = ""
            docx_url = ""

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

                        voice_google = batch.voice_google or 1
                        result = ShotStackService.create_video_from_images_v2(
                            post.id,
                            voice_google,
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
                    img_res = ImageMaker.save_image_and_write_text(
                        image_url, image_caption, font_size=80
                    )
                    image_url = img_res.get("image_url", "")
                    file_size += img_res.get("file_size", 0)
                    mime_type = img_res.get("mime_type", "")
                    maker_images.append(image_url)

                logger.info(
                    "-------------------- PROCESSED CREATE IMAGES -------------------"
                )
            elif type == "blog":
                logger.info(
                    "-------------------- PROCESSING CREATE LOGS -------------------"
                )

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

                response = call_chatgpt_create_blog(blog_images, data, post.id)
                if response:
                    parse_caption = json.loads(response)
                    parse_response = parse_caption.get("response", {})
                    docx_title = parse_response.get("title", "")
                    docx_content = parse_response.get("docx_content", "")
                    res_docx = DocxMaker().make(docx_title, docx_content, blog_images)

                    docx_url = res_docx.get("docx_url", "")
                    file_size = res_docx.get("file_size", 0)
                    mime_type = res_docx.get("mime_type", "")

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
                if parse_response and "docx_content" in parse_response:
                    docx = parse_response.get("docx_content", "")
                    description = json.dumps(docx)
                if parse_response and "content" in parse_response:
                    content = parse_response.get("content", "")
                    for index, image_url in enumerate(blog_images):
                        content = content.replace(f"IMAGE_URL_{index}", image_url)

            else:
                return Response(
                    message=f"Tạo {type} that bai.!",
                    status=200,
                    code=201,
                ).to_dict()

            url = batch.url
            if should_replace_shortlink(url):
                shorten_link = batch.shorten_link
                description = description.replace(url, shorten_link)

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
                docx_url=docx_url,
                file_size=file_size,
                mime_type=mime_type,
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


@ns.route("/get-status-upload-by-sync-id/<string:id>")
class APIGetStatusUploadBySyncId(Resource):

    def get(self, id):
        try:
            social_sync = SocialPostService.find_social_sync(id)
            if not social_sync:
                return Response(
                    message="Sync không tồn tại",
                    status=404,
                ).to_dict()
            sync_status = SocialPostService.get_status_social_sycns__by_id(
                social_sync.id
            )
            return Response(
                data=sync_status,
                message="Lấy sync thành công",
            ).to_dict()
        except Exception as e:
            logger.error(f"Exception: get status upload by sync id fail  :  {str(e)}")
            return Response(
                message="Lấy trạng thái upload theo sync id thất bại",
                status=200,
                code=201,
            ).to_dict()


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

            status_check_sns = 0
            for social_post_each in social_post_detail:
                status = social_post_each["status"]
                if status == "PUBLISHED":
                    status_check_sns = 1

            update_data = {"social_sns_description": json.dumps(social_post_detail)}
            if status_check_sns == 1:
                update_data["status_sns"] = 1

            for sns_post_detail in social_post_detail:
                sns_post_id = sns_post_detail["post_id"]
                sns_status = sns_post_detail["status"]
                notification_type = sns_post_detail["title"]

                notification = NotificationServices.find_notification_sns(
                    sns_post_id, notification_type
                )
                if not notification:
                    notification = NotificationServices.create_notification(
                        user_id=post_detail.user_id,
                        batch_id=post_detail.batch_id,
                        title="🔔AI로 생성된 비디오가 성공적으로 만들어졌습니다.",
                    )
                if sns_status == "PUBLISHED":
                    NotificationServices.update_notification(
                        notification.id,
                        title= "",
                    )

            PostService.update_post(post_id, **update_data)

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
                batch.id, status=99, process_status="DRAFT", user_id=current_user.id
            )

            PostService.update_post_by_batch_id(
                batch.id, status=const.DRAFT_STATUS, user_id=current_user.id
            )

            NotificationServices.update_notification_by_batch_id(
                batch.id, user_id=current_user.id
            )

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


@ns.route("/template_video")
class APITemplateVideo(Resource):
    @jwt_required()
    def get(self):
        current_user = AuthService.get_current_identity()
        user_template = PostService.get_template_video_by_user_id(current_user.id)
        if not user_template:
            image_template = [
                {
                    "id": 1,
                    "name": "노트필기형",
                    "image_url": "https://apitoktak.voda-play.com/voice/img/1.png",
                },
                {
                    "id": 2,
                    "name": "블러이미지형",
                    "image_url": "https://apitoktak.voda-play.com/voice/img/2.png",
                },
                {
                    "id": 3,
                    "name": "상품이미지형",
                    "image_url": "https://apitoktak.voda-play.com/voice/img/3.png",
                },
            ]

            video_hooks = ShotStackService.get_random_videos(3)
            user_template = PostService.create_user_template(
                user_id=current_user.id,
                video_hooks=json.dumps(video_hooks),
                image_template=json.dumps(image_template),
            )

        user_template_data = user_template.to_dict()

        return Response(
            data=user_template_data,
            code=200,
        ).to_dict()
