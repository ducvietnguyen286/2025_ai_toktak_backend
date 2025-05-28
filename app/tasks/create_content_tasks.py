import json
import os

from celery import group
from app.ais.chatgpt import (
    call_chatgpt_clear_product_name,
    call_chatgpt_create_blog,
    call_chatgpt_create_caption,
    call_chatgpt_create_social,
)
from app.enums.messages import MessageError, MessageSuccess
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
from app.services.shotstack_services import ShotStackService
from app.services.video_service import VideoService
from app.tasks.celery_app import celery_app, make_celery_app
import const

app = make_celery_app()


@celery_app.task(bind=True, name="create_batch_content")
def create_batch_content(self, batch_id, data):
    with app.app_context():
        try:
            url = data.get("input_url")
            shorten_link, is_shorted = ShortenServices.shorted_link(url)
            data["base_url"] = shorten_link
            data["shorten_link"] = shorten_link if is_shorted else ""

            product_name = data.get("name", "")
            product_name_cleared = call_chatgpt_clear_product_name(product_name)
            if product_name_cleared:
                data["name"] = product_name_cleared

            thumbnails = data.get("thumbnails", [])

            BatchService.update_batch(
                batch_id,
                base_url=shorten_link,
                shorten_link=shorten_link,
                content=json.dumps(data),
                thumbnails=thumbnails,
            )
            return batch_id
        except Exception as e:
            traceback = e.__traceback__
            if traceback:
                app.logger.error(
                    f"Error creating batch content: {e} at line {traceback.tb_lineno}"
                )
            app.logger.error(f"Error creating batch content: {e}")
            self.retry(exc=e, countdown=5, max_retries=3)
            return None


@celery_app.task(bind=True, name="create_images")
def create_images(self, batch_id):
    with app.app_context():
        try:
            batch_detail = BatchService.find_batch(batch_id)
            if not batch_detail:
                return None

            content = json.loads(batch_detail.content)
            batch_thumbnails = batch_detail.thumbnails
            crawl_url = content.get("url_crawl", "") or ""
            base_images = content.get("images", []) or []
            base_thumbnails = json.loads(batch_thumbnails) if batch_thumbnails else []
            images, thumbnails = [], []

            is_cut_out = os.environ.get("USE_CUT_OUT_IMAGE") == "true"
            is_ocr = os.environ.get("USE_OCR") == "true"
            is_avif = "aliexpress" in crawl_url

            if is_cut_out:
                if is_ocr:
                    images = ImageMaker.get_only_beauty_images(
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
                        image, batch_id=batch_id
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
                "thumbnails": json.dumps(thumbnails),
                "content": json.dumps(content),
            }
            BatchService.update_batch(batch_id, **data_update_batch)
            return batch_id

        except Exception as e:
            traceback = e.__traceback__
            if traceback:
                app.logger.error(
                    f"Error in create_images: {e} at line {traceback.tb_lineno}"
                )
            app.logger.error(f"Error in create_images: {e}")
            self.retry(exc=e, countdown=5, max_retries=3)
            return None


@celery_app.task(bind=True, name="make_post_data")
def make_post_data(self, batch_id):
    with app.app_context():
        try:
            batch = BatchService.find_batch(batch_id)
            if not batch:
                return None
            posts = PostService.get_posts__by_batch_id(batch_id)
            if not posts:
                return None
            job = group(make_single_post.s(batch, post) for post in posts)
            result = job.apply_async()
            result.join()
            if result.successful():
                return batch_id
            else:
                app.logger.error(f"Error in make_post_data for batch {batch_id}")
                return None

        except Exception as e:
            traceback = e.__traceback__
            if traceback:
                app.logger.error(
                    f"Error finding batch: {e} at line {traceback.tb_lineno}"
                )
            app.logger.error(f"Error finding batch: {e}")
            self.retry(exc=e, countdown=5, max_retries=3)
            return None


@celery_app.task(bind=True, name="make_single_post")
def make_single_post(self, batch, post):
    with app.app_context():
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

            if type == "video":
                response, render_id, hooking, maker_images, captions = (
                    process_create_post_video(process_images, data, batch, post)
                )
            elif type == "image":
                response, maker_images, captions, file_size, mime_type = (
                    process_create_post_image(process_images, data, batch, post)
                )
            elif type == "blog":
                (
                    response,
                    docx_url,
                    file_size,
                    mime_type,
                    maker_images,
                    title,
                    content,
                ) = process_create_post_blog(process_images, data, batch, post)

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

                    for index, image_url in enumerate(process_images):
                        content = content.replace(f"IMAGE_URL_{index}", image_url)
            else:
                message_error = {
                    "video": MessageError.CREATE_POST_VIDEO.value,
                    "image": MessageError.CREATE_POST_IMAGE.value,
                    "blog": MessageError.CREATE_POST_BLOG.value,
                }

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

            batch = BatchService.update_batch(batch.id, done_post=current_done_post + 1)

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
            app.logger.error(f"Error in make_single_post: {e}")
            self.retry(exc=e, countdown=5, max_retries=1)
            return None


def check_is_avif(data):
    is_avif = False
    crawl_url = data.get("domain", "")
    if "aliexpress" in crawl_url:
        is_avif = True
    return is_avif


def process_create_post_blog(process_images, data, batch, post):
    url = batch.url
    batch_id = batch.id
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
        docx_url = ""
        file_size = 0
        mime_type = ""
        docx_title = ""
        docx_content = ""
        message_error = MessageError.CREATE_POST_BLOG.value
        app.logger.error(f"Error creating blog post: {message_error}")
        return (
            None,
            docx_url,
            file_size,
            mime_type,
            process_images,
            docx_title,
            docx_content,
        )

    return (
        response,
        docx_url,
        file_size,
        mime_type,
        process_images,
        docx_title,
        docx_content,
    )


def process_create_post_image(process_images, data, batch, post):
    template_info = json.loads(batch.template_info)
    image_template_id = template_info.get("image_template_id", "")
    if image_template_id == "":
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
        file_size += img_res.get("file_size", 0)
        mime_type = img_res.get("mime_type", "")
        maker_images = image_urls
    else:
        maker_images = []
        captions = []
        file_size = 0
        mime_type = ""
        message_error = MessageError.CREATE_POST_IMAGE.value
        app.logger.error(f"Error creating image post: {message_error}")
        return None, maker_images, captions, file_size, mime_type

    return response, maker_images, captions, file_size, mime_type


def process_create_post_video(process_images, data, batch, post):
    batch_id = batch.id
    is_avif = check_is_avif(data)
    maker_images = []
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
            result = ShotStackService.create_video_from_images_v2(data_make_video)

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
                message_error = MessageError.CREATE_POST_VIDEO.value
                app.logger.error(f"Error creating video post: {message_error}")
                return None, render_id, hooking, maker_images, captions

        else:
            render_id = ""
            hooking = []
            maker_images = []
            captions = []
            message_error = MessageError.CREATE_POST_VIDEO.value
            app.logger.error(f"Error creating video post: {message_error}")
            return None, render_id, hooking, maker_images, captions

    else:
        render_id = ""
        hooking = []
        maker_images = []
        captions = []
        message_error = MessageError.CREATE_POST_VIDEO.value
        app.logger.error(f"Error creating video post: {message_error}")
        return None, render_id, hooking, maker_images, captions

    return response, render_id, hooking, maker_images, captions
