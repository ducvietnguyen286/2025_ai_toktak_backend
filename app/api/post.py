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
from app.services.shotstack_services import ShotStackService
from flask import request

from flask_jwt_extended import jwt_required
from app.services.auth import AuthService
import const

ns_post = Namespace(name="post", description="Post API")


@ns_post.route("/edit_post")
class APIEditPost(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "post_id": {"type": ["string", "number", "null"]},
            "title": {"type": ["string", "null"]},
            "description": {"type": ["string", "null"]},
            "content": {"type": ["string", "null"]},
            "hashtag": {"type": ["string", "null"]},
            "subtitle": {"type": ["string", "null"]},
        },
        required=["post_id"],
    )
    def post(self, args):
        try:
            post_id = args.get("post_id", 0)
            post_id = int(post_id) if post_id else 0
            description = args.get("description", "")
            title = args.get("title", "")
            hashtag = args.get("hashtag", "")
            content = args.get("content", "")
            subtitle = args.get("subtitle", "")

            post_detail = PostService.find_post(post_id)
            if not post_detail:
                return Response(
                    message="선택할 대상이 없습니다.",
                    code=201,
                ).to_dict()

            update_data = {
                k: v
                for k, v in {
                    "title": title,
                    "description": description,
                    "content": content,
                    "hashtag": hashtag,
                    "subtitle": subtitle,
                }.items()
                if v is not None
            }
            if update_data:
                post_detail = PostService.update_post(post_id, **update_data)
                return Response(
                    data=post_detail._to_json(),
                    message="성공적으로 업데이트되었습니다.",
                    code=200,
                ).to_dict()
            else:
                return Response(
                    message="업데이트할 데이터가 없습니다.",
                    code=201,
                ).to_dict()

        except Exception as e:
            logger.error(f"Exception: 업데이트에 실패했습니다.  :  {str(e)}")
            return Response(
                message="업데이트에 실패했습니다.",
                code=201,
            ).to_dict()
