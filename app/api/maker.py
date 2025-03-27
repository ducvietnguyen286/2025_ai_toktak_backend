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
from app.lib.string import (
    split_text_by_sentences,
    should_replace_shortlink,
    update_ads_content,
)
from app.makers.docx import DocxMaker
from app.makers.images import ImageMaker
from app.makers.videos import MakerVideo
from app.scraper import Scraper
import traceback
import random

from app.services.batch import BatchService
from app.services.image_template import ImageTemplateService
from app.services.post import PostService
from app.services.social_post import SocialPostService
from app.services.video_service import VideoService
from app.services.shotstack_services import ShotStackService
from app.services.shorten_services import ShortenServices
from app.services.notification import NotificationServices

from app.extensions import redis_client
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
            "narration": {"type": ["string", "null"]},
            "is_advance": {"type": "boolean"},
            "is_paid_advertisements": {"type": "integer"},
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
            narration = args.get("narration", "female")
            if narration == "female":
                voice = random.randint(3, 4)
            else:
                voice = random.randint(1, 2)

            is_paid_advertisements = args.get("is_paid_advertisements", 0)
            is_advance = args.get("is_advance", False)
            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"

            data = Scraper().scraper({"url": url})

            # return data
            if not data:
                NotificationServices.create_notification(
                    user_id=user_id_login,
                    title=f"❌ 해당 {url}은 분석이 불가능합니다. 올바른 링크인지 확인해주세요.",
                )

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
                data["base_url"] = shorten_link

            data["shorten_link"] = shorten_link

            product_name = data.get("name", "")
            product_name_cleared = call_chatgpt_clear_product_name(product_name)
            if product_name_cleared:
                data["name"] = product_name_cleared

            # if is_advance:
            #     return Response(
            #         data=data,
            #         message="상품 정보를 성공적으로 가져왔습니다.",
            #     ).to_dict()

            thumbnail_url = data.get("image", "")
            thumbnails = data.get("thumbnails", [])

            if "text" not in data:
                data["text"] = ""
            if "iframes" not in data:
                data["iframes"] = []

            post_types = ["video", "image", "blog"]

            template_info = get_template_info(is_advance)

            batch = BatchService.create_batch(
                user_id=user_id_login,
                url=url,
                shorten_link=shorten_link,
                thumbnail=thumbnail_url,
                thumbnails=json.dumps(thumbnails),
                content="",
                type=1,
                count_post=len(post_types),
                status=0,
                process_status="PENDING",
                voice_google=voice,
                is_paid_advertisements=is_paid_advertisements,
                is_advance=is_advance,
                template_info=template_info,
            )

            data["cleared_images"] = []
            if os.environ.get("USE_CUT_OUT_IMAGE") == "true":
                images = data.get("images", [])
                cleared_images = []
                for image in images:
                    cutout_images = ImageMaker.cut_out_long_heihgt_images_by_sam(
                        image, batch_id=batch.id
                    )
                    cleared_images.extend(cutout_images)
                data["cleared_images"] = cleared_images

            batch.content = json.dumps(data)
            batch.save()

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
            "image_template_id": {"type": ["string", "null"]},
        },
        required=["batch_id"],
    )
    def post(self, args):
        try:
            batch_id = args.get("batch_id", 0)
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
            image_template_id = args.get("image_template_id", 0)

            user_id_login = 0
            current_user = AuthService.get_current_identity() or None
            user_id_login = current_user.id
            user_template = PostService.get_template_video_by_user_id(user_id_login)
            if not user_template:
                user_template = PostService.create_user_template(
                    user_id=current_user.id
                )

            # user_template = PostService.up

            data_update_template = {
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
                "image_template_id": image_template_id,
            }

            user_template = PostService.update_template(
                user_template.id, **data_update_template
            )
            user_template_data = user_template.to_dict()

            posts = PostService.get_posts_by_batch_id(batch_id)
            user_template_data["posts"] = posts

            batch_detail = BatchService.find_batch(batch_id)

            if not batch_detail:
                return Response(
                    message="Batch không tồn tại",
                    code=201,
                ).to_dict()

            data_update_batch = {
                "is_paid_advertisements": is_paid_advertisements,
                "voice_google": voice_id,
                "template_info": json.dumps(data_update_template),
            }
            BatchService.update_batch(batch_id, **data_update_batch)

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

    @parameters(
        type="object",
        properties={},
        required=[],
    )
    def post(self, id, **kwargs):
        try:
            args = kwargs.get("req_args", False)
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

            batch_id = batch.id
            is_paid_advertisements = batch.is_paid_advertisements
            template_info = json.loads(batch.template_info)

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
                        maker_image = ImageMaker.save_image_for_short_video(
                            image_url, batch_id
                        )
                        maker_images.append(maker_image)

                    # Tạo video từ ảnh
                    if len(maker_images) > 0:
                        image_renders = maker_images[:1]  # Lấy tối đa 3 Ảnh đầu tiên
                        image_renders_sliders = maker_images[
                            :5
                        ]  # Lấy tối đa 5 Ảnh đầu tiên
                        caption_sliders = captions[:5]  # Lấy tối đa 5 Ảnh đầu tiên

                        product_name = data["name"]

                        voice_google = batch.voice_google or 1
                        data_make_video = {
                            "post_id": post.id,
                            "batch_id": batch.id,
                            "is_advance": batch.is_advance,
                            "template_info": batch.template_info,
                            "voice_google": voice_google,
                            "origin_caption": origin_caption,
                            "images_url": image_renders,
                            "images_slider_url": image_renders_sliders,
                        }
                        result = ShotStackService.create_video_from_images_v2(
                            data_make_video
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
                image_template_id = template_info.get("image_template_id", "")
                if image_template_id == "":
                    return Response(
                        message="Vui lòng chọn template",
                        status=200,
                        code=201,
                    ).to_dict()

                response = call_chatgpt_create_social(process_images, data, post.id)
                if response:
                    parse_caption = json.loads(response)
                    parse_response = parse_caption.get("response", {})
                    captions = parse_response.get("caption", "")
                    image_template = ImageTemplateService.find_image_template(
                        image_template_id
                    )
                    if not image_template:
                        return Response(
                            message="Template không tồn tại",
                            status=200,
                            code=201,
                        ).to_dict()

                    img_res = ImageTemplateService.create_image_by_template(
                        template=image_template,
                        captions=captions,
                        process_images=process_images,
                        post=post,
                    )
                    image_urls = img_res.get("image_urls", [])
                    file_size += img_res.get("file_size", 0)
                    mime_type = img_res.get("mime_type", "")
                    maker_images = image_urls

                    # if is_advance:

                    # else:
                    #     for index, image_url in enumerate(process_images):
                    #         image_caption = (
                    #             captions[index] if index < len(captions) else ""
                    #         )
                    #         img_res = ImageMaker.save_image_and_write_text(
                    #             image_url, image_caption, font_size=80
                    #         )
                    #         image_url = img_res.get("image_url", "")
                    #         file_size += img_res.get("file_size", 0)
                    #         mime_type = img_res.get("mime_type", "")
                    #         maker_images.append(image_url)

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
                    res_docx = DocxMaker().make(
                        docx_title, docx_content, blog_images, batch_id=batch_id
                    )

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
                    cleared_images = data.get("cleared_images", [])
                    if cleared_images:
                        pre_content = ""
                        for cleared_image in enumerate(cleared_images):
                            pre_content += f'<p><img src="{cleared_image}" /></p>'

                        content = pre_content + content

                    for index, image_url in enumerate(blog_images):
                        content = content.replace(f"IMAGE_URL_{index}", image_url)

            else:
                return Response(
                    message=f"Tạo {type} that bai.!",
                    status=200,
                    code=201,
                ).to_dict()

            url = batch.url

            if type == "blog":
                content = update_ads_content(url, content)

            if is_paid_advertisements == 1:
                hashtag = f"#광고 {hashtag}"

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
                message = "🖼 이미지 생성이 완료되었습니다."
                NotificationServices.create_notification(
                    user_id=current_user_id,
                    batch_id=batch.id,
                    title=message,
                )

            elif type == "blog":
                message = "✍️ 블로그 콘텐츠가 생성되었습니다."
                NotificationServices.create_notification(
                    user_id=current_user_id,
                    batch_id=batch.id,
                    title=message,
                )

            return Response(
                data=post._to_json(),
                message=message,
            ).to_dict()
        except Exception as e:
            logger.error(f"Exception: create {type} that bai  :  {str(e)}")
            traceback.print_exc()

            if type == "video":
                message = "비디오 생성이 성공적으로 완료되었습니다."
            elif type == "image":
                message = "⚠️ 이미지 생성에 실패했습니다. 다시 시도해주세요."
                NotificationServices.create_notification(
                    user_id=current_user_id,
                    batch_id=batch.id,
                    title=message,
                )

            elif type == "blog":
                message = "⚠️ 블로그 생성에 실패했습니다. 다시 시도해주세요."
                NotificationServices.create_notification(
                    user_id=current_user_id,
                    batch_id=batch.id,
                    title=message,
                )

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
        try:
            batch = BatchService.find_batch(id)
            if not batch:
                return Response(
                    message="Batch không tồn tại",
                    status=404,
                ).to_dict()

            posts = PostService.get_posts_by_batch_id(batch.id)
            for post_detail in posts:
                try:
                    post_id = post_detail["id"]
                    social_post_detail = (
                        SocialPostService.by_post_id_get_latest_social_posts(post_id)
                    )
                    post_detail["social_post_detail"] = social_post_detail

                    status_check_sns = 0
                    for social_post_each in social_post_detail:
                        status = social_post_each["status"]
                        if status == "PUBLISHED":
                            status_check_sns = 1

                    update_data = {
                        "social_sns_description": json.dumps(social_post_detail)
                    }
                    if status_check_sns == 1:
                        update_data["status_sns"] = 1

                    for sns_post_detail in social_post_detail:
                        try:
                            sns_post_id = sns_post_detail["post_id"]
                            sns_status = sns_post_detail["status"]
                            notification_type = sns_post_detail["title"]

                            logger.info(f"sns_post_detail: {sns_post_detail}")
                            logger.info(f"sns_post_id: {sns_post_id}")
                            logger.info(f"sns_status: {sns_status}")
                            logger.info(f"notification_type: {notification_type}")
                            notification = NotificationServices.find_notification_sns(
                                sns_post_id, notification_type
                            )
                            logger.info(f"notification: {notification}")
                            if not notification:
                                notification = NotificationServices.create_notification(
                                    user_id=post_detail["user_id"],
                                    batch_id=post_detail["batch_id"],
                                    post_id=sns_post_id,
                                    notification_type=notification_type,
                                    title=f"🔄{notification_type}에 업로드 중입니다.",
                                )
                            if sns_status == "PUBLISHED":
                                NotificationServices.update_notification(
                                    notification.id,
                                    title=f"✅{notification_type} 업로드에 성공했습니다.",
                                )
                            elif sns_status == "ERRORED":
                                NotificationServices.update_notification(
                                    notification.id,
                                    title=f"❌{notification_type} 업로드에 실패했습니다.",
                                )
                        except Exception as e:
                            logger.error(
                                f"Lỗi xử lý SNS post detail: {e}", exc_info=True
                            )

                    PostService.update_post(post_id, **update_data)
                except Exception as e:
                    logger.error(f"Lỗi xử lý post {post_id}: {e}", exc_info=True)

            batch_res = batch._to_json()
            batch_res["posts"] = posts

            return Response(
                data=batch_res,
                message="Lấy batch thành công",
            ).to_dict()
        except Exception as e:
            logger.error(
                f"Lỗi trong API get-status-upload-with-batch-id: {e}", exc_info=True
            )
            return Response(
                message="Đã xảy ra lỗi trong quá trình xử lý",
                status=500,
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

            NotificationServices.create_notification(
                user_id=current_user.id,
                batch_id=id,
                title="💾 작업이 임시 저장되었습니다.",
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
        batch_id = request.args.get("batch_id")

        batch_info = BatchService.find_batch(batch_id)
        if not batch_info:
            return Response(
                message="Batch không tồn tại",
                code=201,
            ).to_dict()

        current_user = AuthService.get_current_identity()
        user_template = PostService.get_template_video_by_user_id(current_user.id)
        if not user_template:
            image_templates = ImageTemplateService.get_image_templates()
            video_hooks = [
                {
                    "video_name": "NViral Video_41.mp4",
                    "video_url": "https://apitoktak.voda-play.com/voice/advance/1_advance.mp4",
                    "duration": 2.9,
                },
                {
                    "video_name": "Video_67.mp4",
                    "video_url": "https://apitoktak.voda-play.com/voice/advance/2_advance.mp4",
                    "duration": 2.42,
                },
                {
                    "video_name": "Video_16.mp4",
                    "video_url": "https://apitoktak.voda-play.com/voice/advance/3_advance.mp4",
                    "duration": 4.04,
                },
            ]
            viral_messages = [
                {
                    "video_name": "",
                    "video_url": "https://apitoktak.voda-play.com/voice/advance/viral_message1.gif",
                    "duration": 2.42,
                },
                {
                    "video_name": "",
                    "video_url": "https://apitoktak.voda-play.com/voice/advance/viral_message2.gif",
                    "duration": 4.04,
                },
                {
                    "video_name": "",
                    "video_url": "https://apitoktak.voda-play.com/voice/advance/viral_message3.gif",
                    "duration": 2.42,
                },
                {
                    "video_name": "",
                    "video_url": "https://apitoktak.voda-play.com/voice/advance/viral_message4.gif",
                    "duration": 4.04,
                },
                {
                    "video_name": "",
                    "video_url": "https://apitoktak.voda-play.com/voice/advance/viral_message5.gif",
                    "duration": 4.04,
                },
            ]
            subscribe_video = (
                "https://apitoktak.voda-play.com/voice/advance/subscribe_video.mp4"
            )

            user_template = PostService.create_user_template(
                user_id=current_user.id,
                video_hooks=json.dumps(video_hooks),
                image_template=json.dumps(image_templates),
                viral_messages=json.dumps(viral_messages),
                subscribe_video=subscribe_video,
            )

        user_template_data = user_template.to_dict()

        content_batch = json.loads(batch_info.content)

        user_template_data["product_name_full"] = content_batch.get("name", "")
        user_template_data["product_name"] = content_batch.get("name", "")[:10]

        return Response(
            data=user_template_data,
            code=200,
        ).to_dict()


def get_template_info(is_advance):
    if is_advance:
        return json.dumps({})

    redis_key = "template_image_default"

    template_image_default = redis_client.get(redis_key)
    if template_image_default:
        return json.dumps({"image_template_id": template_image_default.decode()})

    try:
        image_templates = ImageTemplateService.get_image_templates()
        if not image_templates:
            return json.dumps({})

        template_image_default = str(image_templates[0]["id"])
        redis_client.set(redis_key, template_image_default)

        return json.dumps({"image_template_id": template_image_default})

    except Exception as ex:
        error_message = (
            f"Error fetching image templates: {ex}\n{traceback.format_exc()}"
        )
        logger.error(error_message)
        return json.dumps({})
