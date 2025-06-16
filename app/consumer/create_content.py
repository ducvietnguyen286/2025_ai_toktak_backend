import datetime
import json
import os
from app.ais.chatgpt import (
    call_chatgpt_clear_product_name,
    call_chatgpt_create_blog,
    call_chatgpt_create_caption,
    call_chatgpt_create_social,
)
from app.enums.messages import MessageError, MessageSuccess
from app.lib.logger import log_create_content_message, logger
from app.lib.string import (
    change_advance_hashtags,
    get_ads_content,
    insert_hashtags_to_string,
    should_replace_shortlink,
    split_text_by_sentences,
    update_ads_content,
)
from app.makers.docx import DocxMaker
from app.makers.images import ImageMaker
from app.services.batch import BatchService
from app.services.image_template import ImageTemplateService
from app.services.notification import NotificationServices
from app.services.post import PostService
from app.services.shorten_services import ShortenServices
from app.extensions import redis_client
from app.services.shotstack_services import ShotStackService
from app.services.video_service import VideoService
import const
import asyncio


class CreateContent:
    def __init__(self, batch, data):
        self.batch = batch
        self.data = data
        self.app = None

    def create_content(self, app):
        try:
            with app.app_context():
                self.app = app
                batch_id = self.create_batch()
                batch_id = self.create_images(batch_id)
                self.create_posts(batch_id)
            return True
        except Exception as e:
            log_create_content_message(f"Error in create_content: {e}")
            return None

    def create_batch(self):
        try:
            batch = self.batch
            data = self.data
            batch_id = batch.id

            url = data.get("input_url", "")

            shorten_link, is_shorted = ShortenServices.shorted_link(url)
            data["base_url"] = shorten_link
            data["shorten_link"] = shorten_link if is_shorted else ""

            product_name = data.get("name", "")
            product_name_cleared = call_chatgpt_clear_product_name(product_name)
            if product_name_cleared:
                data["name"] = product_name_cleared

            BatchService.update_batch(
                batch_id,
                base_url=shorten_link,
                shorten_link=shorten_link,
                content=json.dumps(data),
            )

            is_advance = batch.is_advance
            is_paid_advertisements = batch.is_paid_advertisements
            narration = data.get("narration", "")
            user_id = batch.user_id

            if not is_advance:
                user_template = PostService.get_template_video_by_user_id(user_id)
                if not user_template:
                    user_template = PostService.create_user_template_make_video(
                        user_id=user_id
                    )
                data_update_template = {
                    "is_paid_advertisements": is_paid_advertisements,
                    "narration": narration,
                }

                user_template = PostService.update_template(
                    user_template.id, **data_update_template
                )

            time_to_end_of_day = int(
                (
                    datetime.datetime.combine(datetime.date.today(), datetime.time.max)
                    - datetime.datetime.now()
                ).total_seconds()
                + 1
            )

            redis_client.set(
                f"toktak:users:free:used:{user_id}",
                "1",
                ex=time_to_end_of_day,
            )

            NotificationServices.create_notification(
                user_id=user_id,
                batch_id=batch.id,
                notification_type="create_batch",
                title=f"제품 정보를 성공적으로 가져왔습니다. {url}",
            )

            return batch_id
        except Exception as e:
            traceback = e.__traceback__
            if traceback:
                log_create_content_message(
                    f"Error creating batch content Traceback: {str(e)} at line {traceback.tb_lineno} at file {traceback.tb_frame.f_code.co_filename}"
                )
            log_create_content_message(f"Error creating batch content: {e}")
            return None

    def create_images(self, batch_id):
        try:
            batch_detail = BatchService.find_batch(batch_id)
            if not batch_detail:
                return None

            content = json.loads(batch_detail.content)
            batch_thumbnails = batch_detail.thumbnails
            crawl_url = content.get("url_crawl", "") or ""
            base_images = content.get("images", []) or []
            base_thumbnails = json.loads(batch_thumbnails)
            images, thumbnails = [], []

            is_cut_out = os.environ.get("USE_CUT_OUT_IMAGE") == "true"
            is_ocr = os.environ.get("USE_OCR") == "true"
            is_avif = "aliexpress" in crawl_url
            image_with_base = {}

            if is_cut_out:
                if is_ocr:
                    images, image_with_base = ImageMaker.get_only_beauty_images(
                        base_images, batch_id=batch_id, is_avif=is_avif
                    )
                else:
                    images = ImageMaker.save_normal_images(
                        base_images, batch_id=batch_id, is_avif=is_avif
                    )

                cutout_by_sam_images = []
                description_images = []

                if "domeggook" in crawl_url:
                    thumbnails = ImageMaker.save_normal_images(
                        base_thumbnails, batch_id=batch_id, is_avif=is_avif
                    )
                    thumbnails = ImageMaker.get_multiple_image_url_from_path(thumbnails)
                else:
                    thumbnails = base_thumbnails

                for image in images:
                    sam_cuted_image = ImageMaker.cut_out_long_height_images_by_sam(
                        image, batch_id=batch_id, base_image=image_with_base
                    )
                    if not sam_cuted_image or "is_cut_out" not in sam_cuted_image:
                        continue
                    if sam_cuted_image.get("is_cut_out", False):
                        cutout_by_sam_images.extend(
                            sam_cuted_image.get("image_urls", [])
                        )
                    else:
                        description_images.extend(sam_cuted_image.get("image_urls", []))

                merge_cleared_images = cutout_by_sam_images + description_images
                content["cleared_images"] = merge_cleared_images
                content["images"] = []
                content["sam_cutout_images"] = cutout_by_sam_images
                content["description_images"] = description_images

            else:
                if "domeggook" in crawl_url:
                    images = ImageMaker.save_normal_images(
                        base_images, batch_id=batch_id, is_avif=is_avif
                    )
                    thumbnails = ImageMaker.save_normal_images(
                        base_thumbnails, batch_id=batch_id, is_avif=is_avif
                    )
                    images = ImageMaker.get_multiple_image_url_from_path(images)
                    thumbnails = ImageMaker.get_multiple_image_url_from_path(thumbnails)
                else:
                    images = base_images
                    thumbnails = base_thumbnails

                content["images"] = images

            data_update_batch = {
                "thumbnail": thumbnails[0] if thumbnails else batch_detail.thumbnail,
                "thumbnails": json.dumps(thumbnails),
                "content": json.dumps(content),
            }
            BatchService.update_batch(batch_id, **data_update_batch)
            return batch_id

        except Exception as e:
            traceback = e.__traceback__
            if traceback:
                log_create_content_message(
                    f"Error creating create_images Traceback: {str(e)} at line {traceback.tb_lineno} at file {traceback.tb_frame.f_code.co_filename}"
                )

            log_create_content_message(f"Error in create_images: {e}")
            return None

    def create_posts(self, batch_id):
        try:
            batch = BatchService.find_batch(batch_id)
            if not batch:
                return None
            posts = PostService.get_posts__by_batch_id(batch_id)
            if not posts:
                return None

            async def run_create_single_post(batch_id, post_id, self_ref, app):
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self_ref.create_single_post, batch_id, post_id, app
                )

            async def run_all_create_single_post(batch_id, posts, self_ref, app):
                tasks = [
                    run_create_single_post(batch_id, post.id, self_ref, app)
                    for post in posts[:3]
                ]
                return await asyncio.gather(*tasks)

            app = self.app

            asyncio.run(run_all_create_single_post(batch_id, posts, self, app))
            return batch_id

        except Exception as e:
            traceback = e.__traceback__
            if traceback:
                log_create_content_message(
                    f"Error finding batch Traceback: {str(e)} at line {traceback.tb_lineno} at file {traceback.tb_frame.f_code.co_filename}"
                )

            log_create_content_message(f"Error finding batch: {e}")
            return None

    def create_single_post(self, batch_id, post_id, app):
        with app.app_context():
            batch = BatchService.find_batch(batch_id)
            post = PostService.find_post(post_id)
            if not batch or not post:
                log_create_content_message(
                    f"Batch or Post not found for batch_id={batch_id}, post_id={post_id}"
                )
                return None

            kwargs = {"process_status": const.POST_PROCESSING_STATUS["PROCESSING"]}
            PostService.update_post(post.id, **kwargs)

            is_paid_advertisements = batch.is_paid_advertisements
            template_info = json.loads(batch.template_info)
            data = json.loads(batch.content)
            images = data.get("images", [])
            thumbnails = batch.thumbnails
            url = batch.url

            type = post.type

            try:
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

                response = None
                render_id = ""
                hooking = []
                maker_images = []
                captions = []
                thumbnail = batch.thumbnail
                file_size = 0
                mime_type = ""
                docx_url = ""
                title = ""
                subtitle = ""
                content = ""
                video_url = ""
                hashtag = ""
                description = ""

                if type == "video":
                    result = process_create_post_video(
                        process_images, data, batch, post
                    )
                    if result is None:
                        return None
                    (
                        response,
                        render_id,
                        hooking,
                        maker_images,
                        captions,
                    ) = result

                elif type == "image":
                    result = process_create_post_image(
                        process_images, data, batch, post
                    )
                    if result is None:
                        return None
                    (
                        response,
                        maker_images,
                        captions,
                        file_size,
                        mime_type,
                    ) = result
                elif type == "blog":
                    result = process_create_post_blog(process_images, data, batch, post)
                    if result is None:
                        return None
                    (
                        response,
                        docx_url,
                        file_size,
                        mime_type,
                        maker_images,
                        title,
                        content,
                    ) = result

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

                        for index, image_url in enumerate(process_images):
                            content = content.replace(f"IMAGE_URL_{index}", image_url)
                else:
                    message_error = {
                        "video": MessageError.CREATE_POST_VIDEO.value,
                        "image": MessageError.CREATE_POST_IMAGE.value,
                        "blog": MessageError.CREATE_POST_BLOG.value,
                    }

                    kwargs = {
                        "process_status": const.POST_PROCESSING_STATUS["FAILED"],
                        "error_message": message_error.get(type, ""),
                    }
                    PostService.update_post(post.id, **kwargs)

                    return None

                url = batch.url
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

                batch = BatchService.update_batch(
                    batch.id, done_post=current_done_post + 1
                )
                # push

                if batch.done_post == batch.count_post:
                    BatchService.update_batch(batch.id, status=1)

                if type == "video":
                    message = MessageSuccess.CREATE_POST_VIDEO.value
                elif type == "image":
                    message = MessageSuccess.CREATE_POST_IMAGE.value
                    NotificationServices.create_notification(
                        user_id=post.user_id,
                        batch_id=batch.id,
                        title=message,
                        post_id=post.id,
                        notification_type="image",
                    )

                elif type == "blog":
                    message = MessageSuccess.CREATE_POST_BLOG.value
                    NotificationServices.create_notification(
                        user_id=post.user_id,
                        batch_id=batch.id,
                        title=message,
                        post_id=post.id,
                        notification_type="blog",
                    )

                kwargs = {"process_status": const.POST_PROCESSING_STATUS["COMPLETED"]}
                PostService.update_post(post.id, **kwargs)

                return post.id
            except Exception as e:
                if type == "video":
                    message = MessageError.CREATE_POST_VIDEO.value
                elif type == "image":
                    message = MessageError.CREATE_POST_IMAGE.value
                    NotificationServices.create_notification(
                        user_id=post.user_id,
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
                        user_id=post.user_id,
                        status=const.NOTIFICATION_FALSE,
                        batch_id=batch.id,
                        title=message,
                        post_id=post.id,
                        notification_type="blog",
                        description=f"Create Blog False {str(e)}",
                    )
                traceback = e.__traceback__
                if traceback:
                    log_create_content_message(
                        f"Error make_single_post Traceback: {str(e)} at line {traceback.tb_lineno} at file {traceback.tb_frame.f_code.co_filename}"
                    )
                log_create_content_message(f"Error in make_single_post: {e}")

                kwargs = {
                    "process_status": const.POST_PROCESSING_STATUS["FAILED"],
                    "error_message": f"Create Post False {str(e)}",
                }
                PostService.update_post(post.id, **kwargs)

                return None


def check_is_avif(data):
    is_avif = False
    crawl_url = data.get("domain", "")
    if "aliexpress" in crawl_url:
        is_avif = True
    return is_avif


def process_create_post_blog(process_images, data, batch, post):
    log_create_content_message(
        f"Creating blog post for batch_id={batch.id}, post_id={post.id}"
    )
    response = None
    docx_url = ""
    file_size = 0
    mime_type = ""
    docx_title = ""
    docx_content = ""
    url = batch.url
    batch_id = batch.id
    try:
        response = call_chatgpt_create_blog(process_images, data, post.id)
        if response:
            parse_caption = json.loads(response)
            parse_response = parse_caption.get("response", {})
            docx_title = parse_response.get("title", "")
            docx_content = parse_response.get("docx_content", "")

            ads_text = get_ads_content(url)

            res_txt = DocxMaker().make_txt(
                docx_title,
                ads_text,
                docx_content,
                process_images,
                batch_id=batch_id,
            )

            txt_path = res_txt.get("txt_path", "")
            docx_url = res_txt.get("docx_url", "")
            file_size = res_txt.get("file_size", 0)
            mime_type = res_txt.get("mime_type", "")
        else:
            message_error = MessageError.CREATE_POST_BLOG.value
            log_create_content_message(f"Error creating blog post: {message_error}")

            kwargs = {
                "process_status": const.POST_PROCESSING_STATUS["FAILED"],
                "error_message": message_error,
            }
            PostService.update_post(post.id, **kwargs)

            return None

        return (
            response,
            docx_url,
            file_size,
            mime_type,
            process_images,
            docx_title,
            docx_content,
        )
    except Exception as e:
        traceback = e.__traceback__
        if traceback:
            log_create_content_message(
                f"Error in process_create_post_blog: {str(e)} at line {traceback.tb_lineno} at file {traceback.tb_frame.f_code.co_filename}"
            )
        logger.error(f"Error in process_create_post_blog: {e}")

        kwargs = {
            "process_status": const.POST_PROCESSING_STATUS["FAILED"],
            "error_message": str(e),
        }
        PostService.update_post(post.id, **kwargs)
        return None


def process_create_post_image(process_images, data, batch, post):
    log_create_content_message(
        f"Creating image post for batch_id={batch.id}, post_id={post.id}"
    )
    response = None
    maker_images = []
    captions = []
    file_size = 0
    mime_type = ""

    try:
        template_info = json.loads(batch.template_info)
        image_template_id = template_info.get("image_template_id", "")
        if image_template_id == "":
            kwargs = {
                "process_status": const.POST_PROCESSING_STATUS["FAILED"],
                "error_message": "Image template ID is required for image post creation.",
            }
            PostService.update_post(post.id, **kwargs)

            return None

        is_avif = check_is_avif(data)

        response = call_chatgpt_create_social(process_images, data, post.id)
        if response:
            parse_caption = json.loads(response)
            parse_response = parse_caption.get("response", {})
            captions = parse_response.get("caption", "")
            image_template = ImageTemplateService.find_image_template(image_template_id)
            if not image_template:
                return None

            img_res = ImageTemplateService.create_image_by_template(
                template=image_template,
                captions=captions,
                process_images=process_images,
                post=post,
                is_avif=is_avif,
            )
            image_urls = img_res.get("image_urls", [])
            file_size = img_res.get("file_size", 0)
            mime_type = img_res.get("mime_type", "")
            maker_images = image_urls
        else:
            message_error = MessageError.CREATE_POST_IMAGE.value
            log_create_content_message(f"Error creating image post: {message_error}")

            kwargs = {
                "process_status": const.POST_PROCESSING_STATUS["FAILED"],
                "error_message": message_error,
            }
            PostService.update_post(post.id, **kwargs)

            return None

        return response, maker_images, captions, file_size, mime_type
    except Exception as e:
        traceback = e.__traceback__
        if traceback:
            log_create_content_message(
                f"process_create_post_image Traceback: {str(e)} at line {traceback.tb_lineno} at file {traceback.tb_frame.f_code.co_filename}"
            )
        logger.error(f"Error in process_create_post_image: {e}")

        kwargs = {
            "process_status": const.POST_PROCESSING_STATUS["FAILED"],
            "error_message": str(e),
        }
        PostService.update_post(post.id, **kwargs)

        return None


def process_create_post_video(process_images, data, batch, post):
    log_create_content_message(
        f"Creating video post for batch_id={batch.id}, post_id={post.id}"
    )
    response = None
    maker_images = []
    render_id = ""
    hooking = []
    captions = []

    try:
        batch_id = batch.id
        is_avif = check_is_avif(data)
        response = call_chatgpt_create_caption(process_images, data, post.id)
        if response:
            parse_caption = json.loads(response)
            parse_response = parse_caption.get("response", {})

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
                image_renders_sliders = maker_images[:10]  # Lấy tối đa 10 Ảnh đầu tiên
                gifs = data.get("gifs", [])
                if gifs:
                    image_renders_sliders = gifs + image_renders_sliders

                product_name = data["name"]

                voice_google = batch.voice_google or 1
                voice_typecast = batch.voice_typecast or ""

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
                    "voice_typecast": voice_typecast,
                    "origin_caption": origin_caption,
                    "images_url": image_renders,
                    "images_slider_url": image_renders_sliders,
                    "product_video_url": product_video_url,
                }
                result = ShotStackService.create_video_from_images_v2(data_make_video)

                logger.info(
                    f"ShotStackService.create_video_from_images_v2 result: {result}"
                )

                if result["status_code"] == 200:
                    render_id = result["response"]["id"]

                    VideoService.create_create_video(
                        render_id=render_id,
                        user_id=post.user_id,
                        product_name=product_name,
                        images_url=json.dumps(image_renders),
                        description="",
                        origin_caption=origin_caption,
                        post_id=post.id,
                    )

                else:
                    render_id = ""
                    hooking = []
                    maker_images = []
                    captions = []
                    log_create_content_message(f"Error creating video post, {result}")

                    kwargs = {
                        "process_status": const.POST_PROCESSING_STATUS["FAILED"],
                        "error_message": result.get("message", "Unknown error"),
                    }
                    PostService.update_post(post.id, **kwargs)

                    return None

            else:
                render_id = ""
                hooking = []
                maker_images = []
                captions = []

                message_error = MessageError.CREATE_POST_VIDEO.value

                kwargs = {
                    "process_status": const.POST_PROCESSING_STATUS["FAILED"],
                    "error_message": message_error,
                }
                PostService.update_post(post.id, **kwargs)

                return None

        else:
            message_error = MessageError.CREATE_POST_VIDEO.value

            kwargs = {
                "process_status": const.POST_PROCESSING_STATUS["FAILED"],
                "error_message": message_error,
            }
            PostService.update_post(post.id, **kwargs)

            log_create_content_message(
                f"Error creating video post {post.id}: {message_error} ------ CHATGPT"
            )
            return None

        return response, render_id, hooking, maker_images, captions
    except Exception as e:
        traceback = e.__traceback__
        if traceback:
            log_create_content_message(
                f"process_create_post_video Traceback: {str(e)} at line {traceback.tb_lineno} at file {traceback.tb_frame.f_code.co_filename}"
            )
        logger.error(f"Error in process_create_post_video: {e}")

        kwargs = {
            "process_status": const.POST_PROCESSING_STATUS["FAILED"],
            "error_message": str(e),
        }
        PostService.update_post(post.id, **kwargs)

        return None
