# coding: utf8
import time
import json
import os
import uuid
from flask_restx import Namespace, Resource
import requests
from app.ais.chatgpt import (
    call_chatgpt_create_caption,
    call_chatgpt_create_blog,
    call_chatgpt_create_social,
)
from app.decorators import parameters
from app.lib.logger import logger
from app.lib.response import Response
from app.scraper import Scraper
import traceback

from app.services.batch import BatchService
from app.services.post import PostService
from app.services.video_service import VideoService

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
            url = args.get("url", "")
            current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
            UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
            max_count_image = os.environ.get("MAX_COUNT_IMAGE") or "8"
            max_count_image = int(max_count_image)

            data = Scraper().scraper({"url": url})

            logger.info("data: {0}".format(data))

            if not data:
                return Response(
                    message="Can't get data from url",
                    status=400,
                ).to_dict()

            images = data.get("images", [])
            thumbnail = data.get("image", "")

            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex

            thumbnail_ext = thumbnail.split(".")[-1]
            thumbnail_name = f"{timestamp}_{unique_id}.{thumbnail_ext}"

            thumbnail_path = f"{UPLOAD_FOLDER}/{thumbnail_name}"
            with open(thumbnail_path, "wb") as thumbnail_file:
                thumbnail_file.write(requests.get(thumbnail).content)
            thumbnail_url = f"{current_domain}/files/{thumbnail_name}"

            if images and len(images) > max_count_image:
                images = images[:max_count_image]

            image_paths = []
            for index, image_url in enumerate(images):
                timestamp = int(time.time())
                unique_id = uuid.uuid4().hex
                image_ext = image_url.split(".")[-1]

                file_name = f"{timestamp}_{unique_id}.{image_ext}"

                image_path = f"{UPLOAD_FOLDER}/{file_name}"
                with open(image_path, "wb") as image_file:
                    image_file.write(requests.get(image_url).content)
                image_paths.append(f"{current_domain}/files/{file_name}")
            data["images"] = image_paths

            post_types = ["video", "social", "blog"]

            batch = BatchService.create_batch(
                user_id=1,
                url=url,
                thumbnail=thumbnail_url,
                content=json.dumps(data),
                type=1,
                count_post=len(post_types),
                status=0,
            )

            posts = []
            for post_type in post_types:
                post = PostService.create_post(
                    user_id=1, batch_id=batch.id, type=post_type, status=0
                )

                post_res = post._to_json()
                post_res["url_run"] = (
                    f"{current_domain}/api/v1/maker/make-post/{post.id}"
                )
                posts.append(post_res)

            return Response(
                data={
                    "product_name": data.get("name"),
                    "posts": posts,
                    "images": image_paths,
                },
                message="Tạo batch thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Tạo batch that bai",
                status=400,
            ).to_dict()


@ns.route("/make-post/<int:id>")
class APIMakePost(Resource):

    def post(self, id):
        post = PostService.find_post(id)
        if not post:
            return Response(
                message="Post không tồn tại",
                status=404,
            ).to_dict()
        batch = BatchService.find_batch(post.batch_id)
        if not batch:
            return Response(
                message="Batch không tồn tại",
                status=404,
            ).to_dict()

        if batch.status == 1 or post.status == 1:
            return Response(
                message="Post đã được tạo",
                status=400,
            ).to_dict()

        data = json.loads(batch.content)
        images = data.get("images", [])
        type = post.type

        response = None
        render_id = ""

        if type == "video":
            response = call_chatgpt_create_caption(images, data, post.id)
            if response:
                parse_caption = json.loads(response)
                parse_response = parse_caption.get("response", {})

                captions = parse_response.get("captions", [])

                image_paths = []
                if len(images) == 0:
                    image_paths = [
                        "https://admin.lang.canvasee.com/storage/files/3305/ai/1.jpg",
                        "https://admin.lang.canvasee.com/storage/files/3305/ai/2.jpg",
                    ]

                if len(image_paths) > 0:
                    product_name = data["name"]

                    result = VideoService.create_video_from_images(
                        product_name, image_paths
                    )

                    if result["status_code"] == 200:
                        render_id = result["response"]["id"]

                        VideoService.create_create_video(
                            render_id=render_id,
                            user_id=1,
                            product_name=product_name,
                            images_url=json.dumps(image_paths),
                            description="",
                            post_id=post.id,
                        )

        elif type == "social":
            response = call_chatgpt_create_social(images, data, post.id)
        elif type == "image":
            pass
        elif type == "blog":
            response = call_chatgpt_create_blog(images, data, post.id)

        thumbnail = batch.thumbnail
        title = ""
        subtitle = ""
        content = ""
        video_path = ""
        hashtag = ""

        if response:
            parse_caption = json.loads(response)
            parse_response = parse_caption.get("response", {})

            if parse_response and "post" in parse_response:
                content = parse_response.get("post", "")
            if parse_response and "title" in parse_response:
                title = parse_response.get("title", "")
            if parse_response and "summarize" in parse_response:
                subtitle = parse_response.get("summarize", "")
            if parse_response and "content" in parse_response:
                content = parse_response.get("content", "")

                for index, image_url in enumerate(images):
                    content = content.replace(f"IMAGE_URL_{index}", image_url)

            if parse_response and "caption" in parse_response:
                content = parse_response.get("caption", "")
                content = json.dumps(content)

        else:
            return Response(
                message="Tạo post that bai",
                status=400,
            ).to_dict()

        post = PostService.update_post(
            post.id,
            thumbnail=thumbnail,
            title=title,
            subtitle=subtitle,
            content=content,
            video_path=video_path,
            hashtag=hashtag,
            render_id=render_id,
            status=1,
        )
        current_done_post = batch.done_post

        batch = BatchService.update_batch(batch.id, done_post=current_done_post + 1)

        if batch.done_post == batch.count_post:
            BatchService.update_batch(batch.id, status=1)

        return Response(
            data=post._to_json(),
            message="Tạo post thành công",
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
