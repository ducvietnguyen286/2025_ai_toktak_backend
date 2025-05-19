# coding: utf8
import hashlib
import time
import datetime
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
from app.enums.messages import MessageError, MessageSuccess
from app.enums.social import SocialMedia
from app.lib.caller import get_shorted_link_coupang
from app.lib.logger import logger
from app.lib.response import Response
from app.lib.string import (
    split_text_by_sentences,
    should_replace_shortlink,
    update_ads_content,
    merge_by_key,
    replace_phrases_in_text,
    get_ads_content,
    convert_video_path,
    insert_hashtags_to_string,
    change_advance_hashtags,
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
from app.services.user import UserService

from app.extensions import redis_client
from flask import request, send_file, after_this_request

import tempfile, glob, shutil
from zipfile import ZipFile
from app.services.product import ProductService

from flask_jwt_extended import jwt_required
from app.services.auth import AuthService
import const

from flask_jwt_extended import (
    verify_jwt_in_request,
)

ns = Namespace(name="maker", description="Maker API")


def validater_create_batch(current_user, is_advance, url=""):
    try:
        allowed_domains = [
            "coupang.com",
            "aliexpress.com",
            "domeggook.com",
        ]
        if url and url != "":
            if not any(domain in url for domain in allowed_domains):
                return Response(
                    message=MessageError.INVALID_URL.value["message"],
                    data={
                        "error_message": MessageError.INVALID_URL.value["error_message"]
                    },
                    code=201,
                ).to_dict()

        user_id_login = current_user.id
        if current_user.subscription == "FREE":
            if is_advance:
                return Response(
                    message=MessageError.REQUIRED_COUPON.value["message"],
                    data={
                        "error_message": MessageError.REQUIRED_COUPON.value[
                            "error_message"
                        ]
                    },
                    code=201,
                ).to_dict()

            today_used = redis_client.get(f"toktak:users:free:used:{user_id_login}")
            if today_used:
                return Response(
                    message=MessageError.WAIT_TOMORROW.value["message"],
                    data={
                        "error_message": MessageError.WAIT_TOMORROW.value[
                            "error_message"
                        ]
                    },
                    code=201,
                ).to_dict()

        current_month = time.strftime("%Y-%m", time.localtime())

        if current_user.batch_remain == 0:
            if (
                current_user.subscription == "FREE"
                and current_user.batch_of_month
                and current_month != current_user.batch_of_month
            ):
                current_user.batch_total = const.LIMIT_BATCH[current_user.subscription]
                current_user.batch_remain = const.LIMIT_BATCH[current_user.subscription]
                current_user.batch_of_month = current_month
                current_user.save()
            else:
                return Response(
                    message=MessageError.NO_BATCH_REMAINING.value["message"],
                    data={
                        "error_message": MessageError.NO_BATCH_REMAINING.value[
                            "error_message"
                        ]
                    },
                    code=201,
                ).to_dict()

        redis_user_batch_key = f"toktak:users:batch_remain:{user_id_login}"

        current_remain = redis_client.get(redis_user_batch_key)
        if current_remain:
            current_remain = int(current_remain)
            if current_remain <= 0:
                return Response(
                    message=MessageError.NO_BATCH_REMAINING.value["message"],
                    data={
                        "error_message": MessageError.NO_BATCH_REMAINING.value[
                            "error_message"
                        ]
                    },
                    code=201,
                ).to_dict()
        return None
    except Exception as e:
        traceback.print_exc()
        logger.error("Exception: {0}".format(str(e)))
        return Response(
            message=MessageError.NO_ANALYZE_URL.value["message"],
            data={"error_message": MessageError.NO_ANALYZE_URL.value["error_message"]},
            code=201,
        ).to_dict()


@ns.route("/check-create-batch")
class APICheckCreateBatch(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "is_advance": {"type": "boolean"},
        },
        required=[],
    )
    def get(self, args):
        is_advance = args.get("is_advance", False)
        current_user = AuthService.get_current_identity() or None
        errors = validater_create_batch(current_user, is_advance)
        if errors:
            return errors

        return Response(
            message="Allow Create Batch",
            data={},
            code=200,
        ).to_dict()


@ns.route("/create-batch")
class APICreateBatch(Resource):
    @jwt_required()
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
        url = args.get("url", "")
        is_advance = args.get("is_advance", False)
        current_month = time.strftime("%Y-%m", time.localtime())
        current_user = AuthService.get_current_identity(no_cache=True) or None

        user_id_login = current_user.id if current_user else 0

        try:
            batch_type = const.TYPE_NORMAL

            errors = validater_create_batch(current_user, is_advance, url)
            if errors:
                return errors

            if current_user:
                user_id_login = current_user.id

                if (
                    current_user.subscription != "FREE"
                    and datetime.datetime.strptime(
                        current_user.subscription_expired, "%Y-%m-%d %H:%M:%S"
                    )
                    >= datetime.datetime.now()
                ):
                    batch_type = const.TYPE_PRO

                redis_user_batch_key = f"toktak:users:batch_remain:{user_id_login}"
                redis_client.set(
                    redis_user_batch_key, current_user.batch_remain - 1, ex=180
                )
                if current_user.batch_of_month != current_month:
                    UserService.update_user(
                        user_id_login,
                        batch_of_month=current_month,
                    )

            voice = args.get("voice", 1)
            narration = args.get("narration", "female")
            if narration == "female":
                voice = 3
            else:
                voice = 2

            is_paid_advertisements = args.get("is_paid_advertisements", 0)
            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"

            data = Scraper().scraper({"url": url})

            if not data:
                NotificationServices.create_notification(
                    user_id=user_id_login,
                    status=const.NOTIFICATION_FALSE,
                    title=f"❌ 해당 {url}은 분석이 불가능합니다. 올바른 링크인지 확인해주세요.",
                    description=f"Scraper False {url}",
                )

                redis_client.set(
                    redis_user_batch_key, current_user.batch_remain + 1, ex=180
                )

                return Response(
                    message=MessageError.NO_ANALYZE_URL.value["message"],
                    data={
                        "error_message": MessageError.NO_ANALYZE_URL.value[
                            "error_message"
                        ]
                    },
                    code=201,
                ).to_dict()

            shorten_link, is_shorted = ShortenServices.shorted_link(url)
            data["base_url"] = shorten_link
            data["shorten_link"] = shorten_link if is_shorted else ""

            product_name = data.get("name", "")
            product_name_cleared = call_chatgpt_clear_product_name(product_name)
            if product_name_cleared:
                data["name"] = product_name_cleared

            thumbnail_url = data.get("image", "")
            thumbnails = data.get("thumbnails", [])

            if "text" not in data:
                data["text"] = ""
            if "iframes" not in data:
                data["iframes"] = []

            post_types = ["video", "image", "blog"]

            template_info = get_template_info(is_advance, is_paid_advertisements)

            data["cleared_images"] = []

            batch = BatchService.create_batch(
                user_id=user_id_login,
                url=url,
                shorten_link=shorten_link,
                thumbnail=thumbnail_url,
                thumbnails=json.dumps(thumbnails),
                content=json.dumps(data),
                type=batch_type,
                count_post=len(post_types),
                status=0,
                process_status="PENDING",
                voice_google=voice,
                is_paid_advertisements=is_paid_advertisements,
                is_advance=is_advance,
                template_info=template_info,
            )

            posts = []
            for post_type in post_types:
                post = PostService.create_post(
                    user_id=user_id_login,
                    batch_id=batch.id,
                    type=post_type,
                    status=0,
                )

                post_res = post.to_json()
                post_res["url_run"] = (
                    f"{current_domain}/api/v1/maker/make-post/{post.id}"
                )
                posts.append(post_res)

            batch_res = batch.to_json()
            batch_res["posts"] = posts

            # Save batch for batch-make-image
            batch_id = batch.id
            redis_key = f"batch_info_{batch_id}"
            print(posts)
            redis_client.set(redis_key, json.dumps(posts), ex=3600)

            if current_user:

                if not is_advance:
                    user_template = PostService.get_template_video_by_user_id(
                        user_id_login
                    )
                    if not user_template:
                        user_template = PostService.create_user_template_make_video(
                            user_id=current_user.id
                        )
                    data_update_template = {
                        "is_paid_advertisements": is_paid_advertisements,
                        "narration": narration,
                    }

                    user_template = PostService.update_template(
                        user_template.id, **data_update_template
                    )

                    # current_user.batch_remain -= 1
                    # current_user.save()

                time_to_end_of_day = int(
                    (
                        datetime.datetime.combine(
                            datetime.date.today(), datetime.time.max
                        )
                        - datetime.datetime.now()
                    ).total_seconds()
                    + 1
                )

                redis_client.set(
                    f"toktak:users:free:used:{user_id_login}",
                    "1",
                    ex=time_to_end_of_day,
                )

            NotificationServices.create_notification(
                user_id=user_id_login,
                batch_id=batch.id,
                notification_type="create_batch",
                title=f"제품 정보를 성공적으로 가져왔습니다. {url}",
            )

            batch_res["batch_remain"] = current_user.batch_remain if current_user else 0
            batch_res["batch_total"] = current_user.batch_total if current_user else 0

            return Response(
                data=batch_res,
                message=MessageSuccess.CREATE_BATCH.value,
            ).to_dict()

        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            if current_user:
                user_id_login = current_user.id
                redis_user_batch_key = f"toktak:users:batch_remain:{user_id_login}"
                redis_client.delete(f"toktak:users:free:used:{user_id_login}")
                redis_client.set(
                    redis_user_batch_key, current_user.batch_remain + 1, ex=180
                )
            return Response(
                message=MessageError.NO_ANALYZE_URL.value["message"],
                data={
                    "error_message": MessageError.NO_ANALYZE_URL.value["error_message"]
                },
                code=201,
            ).to_dict()


@ns.route("/batch-make-image")
class APIBatchMakeImage(Resource):

    @parameters(
        type="object",
        properties={
            "batch_id": {"type": "string"},
        },
        required=["batch_id"],
    )
    def post(self, args):
        try:
            batch_id = args.get("batch_id", 0)
            posts = []
            if os.environ.get("USE_CUT_OUT_IMAGE") == "true":

                batch_detail = BatchService.find_batch(batch_id)
                if not batch_detail:
                    return Response(
                        message="Batch không tồn tại",
                        code=201,
                    ).to_dict()

                content = json.loads(batch_detail.content)

                base_images = content["images"] or []
                images = []

                crawl_url = content["url_crawl"] or ""

                is_avif = True if "aliexpress" in crawl_url else False
                if os.environ.get("USE_OCR") == "true":
                    images = ImageMaker.get_only_beauty_images(
                        base_images, batch_id=batch_id, is_avif=is_avif
                    )
                else:
                    images = ImageMaker.save_normal_images(
                        base_images, batch_id=batch_id
                    )

                description_images = []
                # cutout_images = []
                cutout_by_sam_images = []

                for image in images:
                    # has_google_cut_out = False
                    # has_sam_cut_out = False
                    # cuted_image = ImageMaker.cut_out_long_height_images_by_google(
                    #     image, batch_id=batch_id
                    # )
                    # if not cuted_image or (
                    #     cuted_image and "is_cut_out" not in cuted_image
                    # ):
                    #     continue
                    # elif cuted_image:
                    #     is_cut_out = cuted_image.get("is_cut_out", False)
                    #     image_urls = cuted_image.get("image_urls", [])
                    #     if is_cut_out:
                    #         cutout_images.extend(image_urls)
                    #         has_google_cut_out = True

                    sam_cuted_image = ImageMaker.cut_out_long_height_images_by_sam(
                        image, batch_id=batch_id
                    )
                    if not sam_cuted_image or (
                        sam_cuted_image and "is_cut_out" not in sam_cuted_image
                    ):
                        continue
                    else:
                        is_sam_cut_out = sam_cuted_image.get("is_cut_out", False)
                        sam_image_urls = sam_cuted_image.get("image_urls", [])
                        if is_sam_cut_out:
                            cutout_by_sam_images.extend(sam_image_urls)
                        else:
                            description_images.extend(sam_image_urls)

                merge_cleared_images = []
                # if len(cutout_images) > 0:
                #     merge_cleared_images.extend(cutout_images)
                if len(cutout_by_sam_images) > 0:
                    merge_cleared_images.extend(cutout_by_sam_images)
                if len(description_images) > 0:
                    merge_cleared_images.extend(description_images)
                content["cleared_images"] = merge_cleared_images
                # content["cutout_images"] = cutout_images
                content["sam_cutout_images"] = cutout_by_sam_images
                content["description_images"] = description_images
                data_update_batch = {
                    "content": json.dumps(content),
                }
                BatchService.update_batch(batch_id, **data_update_batch)

            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
            redis_key = f"batch_info_{batch_id}"
            batch_info = redis_client.get(redis_key)
            if batch_info:
                posts = json.loads(batch_info)
            else:
                posts = PostService.get_posts_by_batch_id(batch_id)
                for post in posts:
                    post["url_run"] = (
                        f"{current_domain}/api/v1/maker/make-post/{post['id']}"
                    )

                redis_client.set(redis_key, json.dumps(posts), ex=3600)

            return Response(
                data=posts,
                message="제품 정보를 성공적으로 가져왔습니다.",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Batch IMAGE Exception: {0}".format(str(e)))
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
            "comment": {"type": "string"},
            "hashtag": {"type": "array", "items": {"type": "string"}},
            "is_comment": {"type": ["integer", "null"]},
            "is_hashtag": {"type": ["integer", "null"]},
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
            is_comment = args.get("is_comment", 0)
            is_hashtag = args.get("is_hashtag", 0)
            comment = args.get("comment", "")
            hashtag = args.get("hashtag", [])

            user_id_login = 0
            current_user = AuthService.get_current_identity(no_cache=True) or None
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
                "is_comment": is_comment,
                "is_hashtag": is_hashtag,
                "comment": comment,
                "hashtag": json.dumps(hashtag),
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

            # current_user.batch_remain -= 1
            # current_user.save()

            time_to_end_of_day = int(
                (
                    datetime.datetime.combine(datetime.date.today(), datetime.time.max)
                    - datetime.datetime.now()
                ).total_seconds()
                + 1
            )

            redis_client.set(
                f"toktak:users:free:used:{user_id_login}",
                "1",
                ex=time_to_end_of_day,
            )

            user_template_data["batch_remain"] = (
                current_user.batch_remain if current_user else 0
            )
            user_template_data["batch_total"] = (
                current_user.batch_total if current_user else 0
            )

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


@ns.route("/make-post/<id>")
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
            url = batch.url

            type = post.type

            need_count = 10 if type == "video" else 5
            cleared_images = data.get("cleared_images", [])

            process_images = json.loads(thumbnails)
            if process_images and len(process_images) < need_count:
                current_length = len(process_images)
                need_length = need_count - current_length
                if len(cleared_images) > need_length:
                    process_images = process_images + cleared_images[:need_length]
                else:
                    process_images = process_images + cleared_images

                if len(process_images) < need_count:
                    current_length = len(process_images)
                    need_length = need_count - current_length
                    if len(images) > need_length:
                        process_images = process_images + images[:need_length]
                    else:
                        process_images = process_images + images
            elif process_images and len(process_images) >= need_count:
                process_images = process_images[:need_count]
            else:
                if len(cleared_images) > need_count:
                    process_images = cleared_images[:need_count]
                else:
                    process_images = cleared_images

                if len(process_images) < need_count:
                    current_length = len(process_images)
                    need_length = need_count - current_length
                    if len(images) > need_length:
                        process_images = process_images + images[:need_length]
                    else:
                        process_images = process_images + images

            logger.info(f"PROCESSED IMAGES: {process_images}")

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

            is_avif = False
            crawl_url = data.get("domain", "")
            if "aliexpress" in crawl_url:
                is_avif = True

            if type == "video":
                logger.info(f"START PROCESS VIDEO: {post}")
                response = call_chatgpt_create_caption(process_images, data, post.id)
                if response:
                    parse_caption = json.loads(response)
                    parse_response = parse_caption.get("response", {})
                    logger.info("parse_response: {0}".format(parse_response))

                    caption = parse_response.get("caption", "")
                    origin_caption = caption
                    hooking = parse_response.get("hooking", [])

                    product_video_url = data.get("video_url", "")

                    captions = split_text_by_sentences(caption, len(process_images))

                    for image_url in process_images:
                        maker_image = ImageMaker.save_image_for_short_video(
                            image_url, batch_id, is_avif=is_avif
                        )
                        maker_images.append(maker_image)

                    # Tạo video từ ảnh
                    if len(maker_images) > 0:
                        image_renders = maker_images[:3]  # Lấy tối đa 3 Ảnh đầu tiên
                        image_renders_sliders = maker_images[
                            :10
                        ]  # Lấy tối đa 10 Ảnh đầu tiên
                        # Add gifs image
                        gifs = data.get("gifs", [])
                        if gifs:
                            image_renders_sliders = gifs + image_renders_sliders

                        product_name = data["name"]

                        voice_google = batch.voice_google or 1

                        product_video_url = data.get("video_url", "")
                        if product_video_url != "":
                            image_renders_sliders.insert(0, product_video_url)

                        data_make_video = {
                            "post_id": post.id,
                            "batch_id": batch.id,
                            "is_advance": batch.is_advance,
                            "template_info": batch.template_info,
                            "batch_type": batch.type,
                            "voice_google": voice_google,
                            "origin_caption": origin_caption,
                            "images_url": image_renders,
                            "images_slider_url": image_renders_sliders,
                            "product_video_url": product_video_url,
                        }
                        result = ShotStackService.create_video_from_images_v2(
                            data_make_video
                        )

                        if result["status_code"] == 200:
                            render_id = result["response"]["id"]

                            VideoService.create_create_video(
                                render_id=render_id,
                                user_id=current_user_id,
                                product_name=product_name,
                                images_url=json.dumps(image_renders),
                                description="",
                                origin_caption=origin_caption,
                                post_id=post.id,
                            )
                        else:
                            logger.info(f"PROCESS VIDEO ERROR: {post}")
                            return Response(
                                message=result["message"],
                                status=200,
                                code=201,
                            ).to_dict()
                logger.info(f"END PROCESS VIDEO: {post}")
                logger.info(f"RESPONSE PROCESS VIDEO: {response}")
            elif type == "image":
                logger.info(f"START PROCESS IMAGES: {post}")

                image_template_id = template_info.get("image_template_id", "")
                if image_template_id == "":
                    logger.info(f"ERROR TEMPLATE IMAGE")
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
                        logger.info(f"ERROR PROCESS TEMPLATE IMAGES: {post}")
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
                        is_avif=is_avif,
                    )
                    image_urls = img_res.get("image_urls", [])
                    file_size += img_res.get("file_size", 0)
                    mime_type = img_res.get("mime_type", "")
                    maker_images = image_urls
                logger.info(f"END PROCESS IMAGES: {post}")
                logger.info(f"RESPONSE PROCESS IMAGES: {response}")
            elif type == "blog":
                logger.info(f"START PROCESS BLOG: {post}")
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

                response = call_chatgpt_create_blog(process_images, data, post.id)
                if response:
                    parse_caption = json.loads(response)
                    parse_response = parse_caption.get("response", {})
                    docx_title = parse_response.get("title", "")
                    docx_content = parse_response.get("docx_content", "")

                    ads_text = get_ads_content(url)
                    # res_docx = DocxMaker().make(
                    #     docx_title , ads_text , docx_content, process_images, batch_id=batch_id
                    # )
                    # docx_url = res_docx.get("docx_url", "")
                    # file_size = res_docx.get("file_size", 0)
                    # mime_type = res_docx.get("mime_type", "")

                    res_txt = DocxMaker().make_txt(
                        docx_title,
                        ads_text,
                        docx_content,
                        process_images,
                        batch_id=batch_id,
                    )
                    images = ImageMaker.save_normal_images(
                        process_images, batch_id=batch_id
                    )

                    txt_path = res_txt.get("txt_path", "")
                    docx_url = res_txt.get("docx_url", "")
                    file_size = res_txt.get("file_size", 0)
                    mime_type = res_txt.get("mime_type", "")

                logger.info(f"END PROCESS BLOG: {post}")
                logger.info(f"RESPONSE PROCESS BLOG: {response}")

            title = ""
            subtitle = ""
            content = ""
            video_url = ""
            hashtag = ""
            description = ""

            logger.info(f"START PROCESS DATA: {type} - {post}")
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
                    # cutout_images = data.get("cutout_images", [])
                    cutout_by_sam_images = data.get("sam_cutout_images", [])
                    description_images = data.get("description_images", [])
                    cleared_images = data.get("cleared_images", [])
                    # pre_content_cutout = f"<h2>IMAGES CUTTED OUT BY GOOGLE VISION: TOTAL - {len(cutout_images)}</h2>"
                    # if len(cutout_images) > 0:
                    #     current_stt = 0
                    #     for index, cutout_image in enumerate(cutout_images):
                    #         current_stt = index + 1
                    #         pre_content_cutout += f'<p><h2>IMAGE NUM: {current_stt}</h2><img src="{cutout_image}" /></p>'

                    pre_content_cutout_sam = f"<br></br><h2>IMAGES CUTTED OUT BY SERVER: TOTAL - {len(cutout_by_sam_images)}</h2>"
                    if len(cutout_by_sam_images) > 0:
                        current_stt = 0
                        for index, cutout_image in enumerate(cutout_by_sam_images):
                            current_stt = index + 1
                            pre_content_cutout_sam += f'<p><h2>IMAGE NUM: {current_stt}</h2><img src="{cutout_image}" /></p>'

                    pre_content = f"<br></br><h2>DESCRIPTION IMAGES: TOTAL - {len(description_images)}</h2>"
                    if len(description_images) > 0:
                        current_stt = 0
                        for index, cleared_image in enumerate(description_images):
                            current_stt = index + 1
                            pre_content += f'<p><h2>IMAGE NUM: {current_stt}</h2><img src="{cleared_image}" /></p>'

                    content = pre_content_cutout_sam + pre_content + content

                    for index, image_url in enumerate(process_images):
                        content = content.replace(f"IMAGE_URL_{index}", image_url)
                logger.info(f"END PROCESS DATA: {type} - {post}")
            else:
                logger.info(f"ERROR PROCESS DATA: {type} - {response}")
                message_error = {
                    "video": MessageError.CREATE_POST_VIDEO.value,
                    "image": MessageError.CREATE_POST_IMAGE.value,
                    "blog": MessageError.CREATE_POST_BLOG.value,
                }

                return Response(
                    message=message_error.get(type, ""),
                    status=200,
                    code=201,
                ).to_dict()

            url = batch.url
            logger.info(f"START SAVING DATA: {type}")
            if type == "blog":
                content = update_ads_content(url, content)

            if is_paid_advertisements == 1:
                hashtag = f"#광고 {hashtag}"

            if type == "image" or type == "video":
                hashtag = insert_hashtags_to_string(hashtag)

            comment = template_info.get("comment", "")
            is_comment = template_info.get("is_comment", 0)
            is_hashtag = template_info.get("is_hashtag", 0)
            if is_comment == 1 and comment != "":
                description = f"{comment}\n{description}"

            if is_hashtag == 1:
                raw_hashtag = template_info.get("hashtag", "[]")
                try:
                    new_hashtag = json.loads(raw_hashtag)
                except Exception:
                    logger.error("can get change_advance_hashtags")
                    new_hashtag = []
                hashtag = change_advance_hashtags(hashtag, new_hashtag)

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

            logger.info(f"END SAVING DATA: {type}")

            logger.info(f"START NOTIFICATION DATA: {type}")
            if type == "video":
                message = MessageSuccess.CREATE_POST_VIDEO.value
            elif type == "image":
                message = MessageSuccess.CREATE_POST_IMAGE.value
                NotificationServices.create_notification(
                    user_id=current_user_id,
                    batch_id=batch.id,
                    title=message,
                    post_id=post.id,
                    notification_type="image",
                )

            elif type == "blog":
                message = MessageSuccess.CREATE_POST_BLOG.value
                NotificationServices.create_notification(
                    user_id=current_user_id,
                    batch_id=batch.id,
                    title=message,
                    post_id=post.id,
                    notification_type="blog",
                )
            logger.info(f"END NOTIFICATION DATA: {type}")

            post = PostService.find_post(post.id)

            return Response(
                data=post.to_json(),
                message=message,
            ).to_dict()
        except Exception as e:
            print(e)
            logger.error(f"Exception: create {type} that bai  :  {str(e)}")
            traceback.print_exc()

            if type == "video":
                message = MessageError.CREATE_POST_VIDEO.value
            elif type == "image":
                message = MessageError.CREATE_POST_IMAGE.value
                NotificationServices.create_notification(
                    user_id=current_user_id,
                    status=const.NOTIFICATION_FALSE,
                    batch_id=batch.id,
                    title=message,
                    post_id=post.id,
                    notification_type="image",
                    description=f"Create Image False {str(e)}",
                )

            elif type == "blog":
                message = MessageError.CREATE_POST_BLOG.value
                NotificationServices.create_notification(
                    user_id=current_user_id,
                    status=const.NOTIFICATION_FALSE,
                    batch_id=batch.id,
                    title=message,
                    post_id=post.id,
                    notification_type="blog",
                    description=f"Create Blog False {str(e)}",
                )

            return Response(
                message=message,
                status=200,
                code=201,
            ).to_dict()


@ns.route("/get-batch/<id>")
class APIGetBatch(Resource):
    @jwt_required()
    def get(self, id):
        try:
            batch = BatchService.find_batch(id)
            if not batch:
                return Response(
                    message="Batch không tồn tại",
                    status=404,
                ).to_dict()

            posts = PostService.get_posts_by_batch_id(batch.id)

            batch_res = batch.to_json()
            batch_res["posts"] = posts

            user_login = AuthService.get_current_identity()
            user_info = UserService.get_user_info_detail(user_login.id)
            batch_res["user_info"] = user_info

            return Response(
                data=batch_res,
                message="Lấy batch thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Exception: get batch fail  :  {str(e)}")
            return Response(
                message="Lấy batch thất bại",
                status=200,
                code=201,
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

            show_posts = []
            posts = sync_status["posts"]
            for post in posts:
                social_post_detail = post["social_posts"]
                social_sns_description = json.loads(post["social_sns_description"])
                new_social_sns_description = merge_by_key(
                    social_sns_description, social_post_detail
                )

                post_id = post["id"]
                notification_type = post["type"]

                update_data = {
                    "social_sns_description": json.dumps(new_social_sns_description),
                    "schedule_date": datetime.datetime.utcnow(),
                }
                show_post_detail = []
                status_check_sns = 0
                for social_post_each in social_post_detail:
                    sns_status = social_post_each["status"]
                    error_message = social_post_each["error_message"]
                    link_type = social_post_each["link_type"]
                    process_number = social_post_each["process_number"]
                    if sns_status == SocialMedia.PUBLISHED.value:
                        status_check_sns = const.UPLOADED

                    notification = NotificationServices.find_notification_sns(
                        post_id, notification_type
                    )
                    if not notification:
                        notification = NotificationServices.create_notification(
                            user_id=post["user_id"],
                            batch_id=post["batch_id"],
                            post_id=post_id,
                            notification_type=notification_type,
                            title=f"🔄{notification_type}에 업로드 중입니다.",
                        )

                    if (
                        link_type == SocialMedia.INSTAGRAM.value
                        and process_number == 100
                    ):
                        status_check_sns = const.UPLOADED
                        social_post_each["status"] == SocialMedia.PUBLISHED.value
                        NotificationServices.update_notification(
                            notification.id,
                            status=const.NOTIFICATION_SUCCESS,
                            title=f"✅Instagram 업로드에 성공했습니다.",
                            description="업로드가 잘 됐는지 한 번만 확인해 주세요 😊",
                            description_korea="업로드가 잘 됐는지 한 번만 확인해 주세요 😊",
                        )
                    if (
                        sns_status == SocialMedia.PUBLISHED.value
                        and link_type != SocialMedia.INSTAGRAM.value
                    ):
                        NotificationServices.update_notification(
                            notification.id,
                            title=f"✅{notification_type} 업로드에 성공했습니다.",
                            status=const.NOTIFICATION_SUCCESS,
                            description=error_message,
                            description_korea="",
                        )
                    elif (
                        sns_status == SocialMedia.ERRORED.value
                        and link_type != SocialMedia.INSTAGRAM.value
                    ):
                        description_korea = replace_phrases_in_text(error_message)
                        NotificationServices.update_notification(
                            notification.id,
                            status=const.NOTIFICATION_FALSE,
                            title=f"❌{notification_type} 업로드에 실패했습니다.",
                            description=error_message,
                            description_korea=description_korea,
                        )

                    show_post_detail.append(social_post_each)

                post["social_sns_description"] = json.dumps(new_social_sns_description)
                post["social_posts"] = show_post_detail

                if status_check_sns == const.UPLOADED:
                    update_data["status_sns"] = const.UPLOADED
                    update_data["status"] = const.UPLOADED

                    ProductService.create_sns_product(post["user_id"], post["batch_id"])
                else:
                    update_data["status_sns"] = const.UPLOADED_FALSE
                    update_data["status"] = const.DRAFT_STATUS

                PostService.update_post(post_id, **update_data)

                show_posts.append(post)

            sync_status["posts"] = show_posts
            return Response(
                data=sync_status,
                message="Lấy sync thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Exception: get status upload by sync id fail  :  {str(e)}")
            return Response(
                message="Lấy trạng thái upload theo sync id thất bại",
                status=200,
                code=201,
            ).to_dict()


@ns.route("/get-status-upload-with-batch-id/<string:id>")
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
            show_posts = []
            for post_detail in posts:
                try:
                    post_id = post_detail["id"]
                    social_post_detail = (
                        SocialPostService.by_post_id_get_latest_social_posts(post_id)
                    )
                    post_detail["social_post_detail"] = social_post_detail

                    status_check_sns = 0
                    show_detail_posts = []
                    for sns_post_detail in social_post_detail:
                        sns_post_id = sns_post_detail["post_id"]
                        sns_status = sns_post_detail["status"]
                        notification_type = sns_post_detail["title"]
                        error_message = sns_post_detail["error_message"]
                        link_type = sns_post_detail["link_type"]
                        process_number = sns_post_detail["process_number"]
                        if sns_status == SocialMedia.PUBLISHED.value:
                            status_check_sns = const.UPLOADED

                        notification = NotificationServices.find_notification_sns(
                            sns_post_id, notification_type
                        )
                        if not notification:
                            notification = NotificationServices.create_notification(
                                user_id=post_detail["user_id"],
                                batch_id=post_detail["batch_id"],
                                post_id=sns_post_id,
                                notification_type=notification_type,
                                title=f"🔄{notification_type}에 업로드 중입니다.",
                            )

                        if (
                            link_type == SocialMedia.INSTAGRAM.value
                            and process_number == 100
                        ):
                            status_check_sns = const.UPLOADED
                            NotificationServices.update_notification(
                                notification.id,
                                status=const.NOTIFICATION_SUCCESS,
                                title=f"✅Instagram 업로드에 성공했습니다.",
                                description="업로드가 잘 됐는지 한 번만 확인해 주세요 😊",
                                description_korea="업로드가 잘 됐는지 한 번만 확인해 주세요 😊",
                            )
                            sns_post_detail["status"] = SocialMedia.PUBLISHED.value

                        if (
                            sns_status == SocialMedia.PUBLISHED.value
                            and link_type != SocialMedia.INSTAGRAM.value
                        ):
                            NotificationServices.update_notification(
                                notification.id,
                                title=f"✅{notification_type} 업로드에 성공했습니다.",
                                status=const.NOTIFICATION_SUCCESS,
                                description=error_message,
                                description_korea="",
                            )
                        elif (
                            sns_status == SocialMedia.ERRORED.value
                            and link_type != SocialMedia.INSTAGRAM.value
                        ):
                            description_korea = replace_phrases_in_text(error_message)
                            NotificationServices.update_notification(
                                notification.id,
                                status=const.NOTIFICATION_FALSE,
                                title=f"❌{notification_type} 업로드에 실패했습니다.",
                                description=error_message,
                                description_korea=description_korea,
                            )

                        show_detail_posts.append(sns_post_detail)

                    update_data = {
                        "social_sns_description": json.dumps(social_post_detail),
                        "schedule_date": datetime.datetime.utcnow(),
                    }
                    if status_check_sns == 1:
                        update_data["status_sns"] = const.UPLOADED
                        update_data["status"] = const.UPLOADED

                        ProductService.create_sns_product(
                            post_detail["user_id"], post_detail["batch_id"]
                        )
                    else:
                        update_data["status_sns"] = const.UPLOADED_FALSE

                    PostService.update_post(post_id, **update_data)

                    post_detail["social_sns_description"] = json.dumps(
                        social_post_detail
                    )
                    post_detail["social_post_detail"] = show_detail_posts
                    show_posts.append(post_detail)

                except Exception as e:
                    logger.error(f"Lỗi xử lý post {post_id}: {e}", exc_info=True)

            batch_res = batch.to_json()
            batch_res["posts"] = show_posts

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


@ns.route("/save_draft_batch/<string:id>")
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
        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"

        return {
            "current_user": current_user.id,
            "status": True,
            "message": "Success",
            "total": posts.total,
            "page": posts.page,
            "per_page": posts.per_page,
            "total_pages": posts.pages,
            "data": [
                {
                    **post_json,
                    "video_path": convert_video_path(
                        post_json.get("video_path", ""), current_domain
                    ),
                }
                for post in posts.items
                if (post_json := post.to_json())
            ],
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
        try:
            batch_id = request.args.get("batch_id")
            current_user = AuthService.get_current_identity()
            user_template = PostService.get_template_video_by_user_id(current_user.id)

            if not user_template:
                user_template = PostService.create_user_template_make_video(
                    user_id=current_user.id
                )
            user_template_data = user_template.to_dict()

            if batch_id:
                batch_info = BatchService.find_batch(batch_id)
                if batch_info:
                    content_batch = json.loads(batch_info.content)
                    user_template_data["product_name_full"] = content_batch.get(
                        "name", ""
                    )
                    user_template_data["product_name"] = content_batch.get("name", "")[
                        :10
                    ]

            return Response(
                data=user_template_data,
                code=200,
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            trace = traceback.format_exc()
            logger.error(trace)
            logger.error(f"Exception: get template video fail  :  {str(e)}")
            return Response(
                message="Lấy template video thất bại",
                status=200,
                code=201,
            ).to_dict()


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

    try:
        image_templates = ImageTemplateService.get_image_templates()
        if not image_templates:
            return json.dumps({})

        template_image_default = str(image_templates[0]["id"])
        redis_client.set(redis_key, template_image_default)

        return json.dumps(
            {
                "image_template_id": template_image_default,
                "is_paid_advertisements": is_paid_advertisements,
            }
        )

    except Exception as ex:
        error_message = (
            f"Error fetching image templates: {ex}\n{traceback.format_exc()}"
        )
        logger.error(error_message)
        return json.dumps({})


@ns.route("/admin_histories")
class APIAdminHistories(Resource):

    @jwt_required()
    def get(self):
        current_user = AuthService.get_current_identity()
        user_type = current_user.user_type
        if user_type != const.ADMIN:
            return Response(
                message="접근 권한이 없습니다.",
                code=201,
            ).to_dict()

        page = request.args.get("page", const.DEFAULT_PAGE, type=int)
        per_page = request.args.get("per_page", const.DEFAULT_PER_PAGE, type=int)
        status = request.args.get("status", const.UPLOADED, type=int)
        type_order = request.args.get("type_order", "", type=str)
        type_post = request.args.get("type_post", "", type=str)
        time_range = request.args.get("time_range", "", type=str)
        search_text = request.args.get("search_text", "", type=str)
        data_search = {
            "page": page,
            "per_page": per_page,
            "status": status,
            "type_order": type_order,
            "type_post": type_post,
            "time_range": time_range,
            "search_text": search_text,
        }
        posts = PostService.admin_get_posts_upload(data_search)
        return {
            "current_user": current_user.id,
            "status": True,
            "message": "Success",
            "total": posts.total,
            "page": posts.page,
            "per_page": posts.per_page,
            "total_pages": posts.pages,
            "data": [post.to_dict() for post in posts.items],
        }, 200


@ns.route("/copy-blog")
class APICopyBlog(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "blog_id": {"type": "integer"},
        },
        required=["blog_id"],
    )
    def post(self, args):
        try:
            blog_id = args.get("blog_id", "")
            message = "블로그 업데이트 성공"
            post = PostService.update_post(
                blog_id, status=const.UPLOADED, status_sns=const.UPLOADED
            )
            if not post:
                return Response(
                    message="업데이트 실패",
                    code=201,
                ).to_dict()

            NotificationServices.create_notification(
                user_id=post.user_id,
                batch_id=post.batch_id,
                title="블로그를 성공적으로 복사하였습니다.",
                post_id=post.id,
                notification_type="copy_blog",
            )

            return Response(
                message=message,
                code=200,
            ).to_dict()
        except Exception as e:
            logger.error(f"Exception: Update Blog Fail  :  {str(e)}")
            return Response(
                message="업데이트 실패",
                code=201,
            ).to_dict()


@ns.route("/create-scraper")
class APICreateScraper(Resource):
    @parameters(
        type="object",
        properties={
            "url": {"type": "string"},
        },
        required=["url"],
    )
    def post(self, args):
        try:
            url = args.get("url", "")

            data_scraper = Scraper().scraper({"url": url})
            logger.error(data_scraper)
            if not data_scraper:
                return Response(
                    message="Khong co data scraper",
                    code=201,
                ).to_dict()

            return Response(
                data=data_scraper,
                message="Data scraper.",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="상품 정보를 불러올 수 없어요.(Error code : )",
                code=201,
            ).to_dict()


@ns.route("/download-zip")
class APIDownloadZip(Resource):
    def post(self):
        try:
            data = request.get_json()
            post_id = data.get("post_id")

            if not post_id:
                return Response(
                    message="Khong co data post_id",
                    code=201,
                ).to_dict()

            post = PostService.find_post(post_id)
            if not post:
                return Response(
                    message="Khong co data post_id",
                    code=201,
                ).to_dict()

            UPLOAD_BASE_PATH = "uploads"
            post_date = post.created_at.strftime("%Y_%m_%d")
            IMAGE_EXTENSIONS = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp", "*.svg"]
            folder_path = os.path.join(UPLOAD_BASE_PATH, post_date, str(post.batch_id))
            if not os.path.exists(folder_path):
                return Response(
                    message="Folder not found",
                    code=201,
                ).to_dict()

            # Lấy tất cả ảnh theo định dạng cho phép
            file_list = []
            for pattern in IMAGE_EXTENSIONS:
                file_list.extend(glob.glob(os.path.join(folder_path, pattern)))
            if not file_list:
                return Response(
                    message="No image files found",
                    code=201,
                ).to_dict()

            tmp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(tmp_dir, "images.zip")

            with ZipFile(zip_path, "w") as zipf:
                for file_path in file_list:
                    filename = os.path.basename(file_path)
                    zipf.write(file_path, arcname=filename)

            if request:
                after_this_request(
                    lambda response: _cleanup_zip(zip_path, tmp_dir, response)
                )
            return send_file(
                zip_path,
                mimetype="application/zip",
                as_attachment=True,
                download_name=f"post_{post_id}_images.zip",
            )

        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="상품 정보를 불러올 수 없어요.(Error code : )",
                code=201,
            ).to_dict()


@ns.route("/schedule_batch")
class ApiScheduleBatch(Resource):
    def post(self):
        from app.tasks import call_maker_batch_api  # 👈 Lazy import tránh circular

        data = request.json
        try:
            # Hỗ trợ định dạng "2025-05-06 17:11:00"
            run_at = datetime.datetime.strptime(data["run_at"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return {
                "message": "Định dạng thời gian không hợp lệ. Đúng định dạng: YYYY-MM-DD HH:MM:SS"
            }, 400

        delay_seconds = (run_at - datetime.datetime.now()).total_seconds()

        if delay_seconds <= 0:
            return {"message": "Thời gian không hợp lệ (trong quá khứ)"}, 400

        call_maker_batch_api.apply_async(countdown=delay_seconds)
        hours, remainder = divmod(int(delay_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)

        return {
            "message": f"Đã lên lịch gọi API sau {hours} giờ {minutes} phút {seconds} giây"
        }


def _cleanup_zip(zip_path, tmp_dir, response):
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
    except Exception as e:
        logger.warning(f"Không thể xóa tệp tạm: {e}")
    return response
