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
from app.lib.response import Response
from app.scraper import Scraper
import traceback

from app.services.batch import BatchService
from app.services.post import PostService

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

            data = Scraper().scraper({"url": url})
            if not data:
                return Response(
                    message="Tạo batch that bai",
                    status=400,
                ).to_dict()

            images = data.get("images", [])
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

            batch = BatchService.create_batch(
                user_id=1, url=url, content=json.dumps(data), type=1, status=0
            )

            post_types = ["video", "social", "blog"]
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
                data={"posts": posts, "images": image_paths},
                message="Tạo batch thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
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

        data = json.loads(batch.content)
        images = data.get("images", [])
        type = post.type

        response = None

        if type == "video":
            response = call_chatgpt_create_caption(images)
        elif type == "social":
            response = call_chatgpt_create_social(images)
        elif type == "image":
            pass
        elif type == "blog":
            response = call_chatgpt_create_blog(images)

        thumbnail = data.get("image", "")
        title = ""
        subtitle = ""
        content = ""
        video_path = ""
        hashtag = ""

        if response:
            parse_caption = json.loads(response)
            parse_response = parse_caption.get("response", {})
            caption = parse_response.get("caption", {})
            caption_hashtag = parse_response.get("caption_hashtag", "")
            social_content = parse_response.get("social_content", "")
            blog_content = parse_response.get("blog_content", "")
            social_hashtag = parse_response.get("social_hashtag", "")
            if caption_hashtag != "" or social_hashtag != "":
                hashtag = caption_hashtag or social_hashtag
            if social_content != "" or blog_content != "":
                content = social_content or blog_content
            if (caption and "title" in caption) or (
                blog_content and "title" in blog_content
            ):
                title = caption.get("title", "") or blog_content.get("title", "")
            if blog_content and "summarize" in blog_content:
                subtitle = blog_content.get("summarize", "")
        else:
            return Response(
                message="Tạo post that bai 2222",
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
            status=1,
        )

        return Response(
            data=post._to_json(),
            message="Tạo post thành công",
        ).to_dict()
