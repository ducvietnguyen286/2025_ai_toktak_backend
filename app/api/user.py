# coding: utf8
import datetime
import json
import os
import random
import time
import traceback
from urllib.parse import urlencode
import uuid
from flask import redirect
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
import jwt
import requests
from app.decorators import parameters
from app.enums.messages import MessageError
from app.lib.logger import logger
from app.lib.response import Response
from app.extensions import redis_client
import secrets

from app.models.youtube_client import YoutubeClient
from app.services.auth import AuthService
from app.services.batch import BatchService
from app.services.post import PostService
from app.services.request_social_log import RequestSocialLogService
from app.services.social_post import SocialPostService
from app.services.tiktok_callback import TiktokCallbackService
from app.services.notification import NotificationServices
from app.services.user import UserService
from app.services.link import LinkService
from app.services.user_link import UserLinkService
from app.services.youtube_client import YoutubeClientService
from app.third_parties.aliexpress import TokenAliExpress
from app.third_parties.facebook import FacebookTokenService
from app.third_parties.tiktok import TiktokTokenService
from app.third_parties.twitter import TwitterTokenService
from app.rabbitmq.producer import (
    send_facebook_message,
    send_instagram_message,
    send_thread_message,
    send_tiktok_message,
    send_twitter_message,
    send_youtube_message,
)
from app.third_parties.youtube import YoutubeTokenService
import const

ns = Namespace(name="user", description="User API")


@ns.route("/links")
class APIUserLinks(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={},
        required=[],
    )
    def get(self, args):
        current_user = AuthService.get_current_identity()
        if not current_user:
            return Response(
                status=401,
                message="Can't User login",
            ).to_dict()
        links = UserService.get_user_links(current_user.id)
        return Response(
            data=links,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/link/<int:id>")
class APIFindUserLink(Resource):

    @jwt_required()
    def get(self, id):
        current_user = AuthService.get_current_identity()
        link = UserService.find_user_link(id, current_user.id)
        if not link:
            return Response(
                message="Không tìm thấy link",
                status=400,
            ).to_dict()

        return Response(
            data=link._to_json(),
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/new-link")
class APINewLink(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={"link_id": {"type": "integer"}},
        required=["link_id"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            link_id = args.get("link_id", 0)
            link = LinkService.find_link(link_id)

            if not link:
                return Response(
                    message="Không tìm thấy link",
                    status=400,
                ).to_dict()

            link_need_info = link.need_info
            info = {}
            if link_need_info:
                link_need_info = json.loads(link_need_info)
                for key in link_need_info:
                    if key not in args:
                        return Response(
                            message=f"Thiếu thông tin cần thiết: {key}",
                            status=400,
                        ).to_dict()
                    info[key] = args[key]
            else:
                return Response(
                    message="Link chưa setup thông tin cần thiết",
                    status=400,
                ).to_dict()

            user_link = UserService.find_user_link_exist(link_id, current_user.id)
            is_active = True
            if not user_link:
                user_link = UserService.create_user_link(
                    user_id=current_user.id,
                    link_id=link_id,
                    meta=json.dumps(info),
                    status=1,
                )

                is_active = UserLinkService.update_user_link(link, user_link, args)

            else:
                user_link.meta = json.dumps(info)
                user_link.status = 1
                user_link.save()

                is_active = UserLinkService.update_user_link(link, user_link, args)

            if not is_active:
                NotificationServices.create_notification(
                    user_id=current_user.id,
                    status=const.NOTIFICATION_FALSE,
                    title=f"{link.type} 연결에 실패했습니다. 계정 정보를 확인해주세요.",
                )

                return Response(
                    message=MessageError.CANT_CONNECT_SNS.value["message"],
                    data={
                        "error_message": MessageError.CANT_CONNECT_SNS.value[
                            "error_message"
                        ]
                    },
                    code=201,
                ).to_dict()

            NotificationServices.create_notification(
                user_id=current_user.id,
                title=f"{link.type} 연결이 완료되었습니다.",
            )

            PostService.update_default_template(current_user.id, link_id)

            return Response(
                data=user_link._to_json(),
                message="Thêm link thành công",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Lỗi kết nối",
                status=400,
            ).to_dict()


@ns.route("/send-posts")
class APISendPosts(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "post_ids": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "is_all": {"type": "integer"},
                        "link_ids": {
                            "type": "array",
                            "items": {"type": ["string", "null", "integer"]},
                        },
                    },
                },
            },
            "disable_comment": {"type": "boolean"},
            "disable_duet": {"type": "boolean"},
            "disable_stitch": {"type": "boolean"},
            "privacy_level": {
                "type": "string",
                "enum": [
                    "PUBLIC_TO_EVERYONE",
                    "MUTUAL_FOLLOW_FRIENDS",
                    "FOLLOWER_OF_CREATOR",
                    "SELF_ONLY",
                ],
            },
            "auto_add_music": {"type": "boolean"},
        },
        required=["post_ids"],
    )
    def post(self, args):
        current_user = AuthService.get_current_identity()
        current_user_id = current_user.id
        redis_user_batch_key = f"toktak:users:batch_sns_remain:{current_user_id}"

        current_time = int(time.time())
        unique_id = uuid.uuid4().hex
        unique_key = f"{current_time}_{unique_id}"
        redis_unique_key = f"toktak:users:batch_sns_count:{unique_key}"

        try:
            id_posts = args.get("post_ids", [])
            disable_comment = args.get("disable_comment", False)
            privacy_level = args.get("privacy_level", "SELF_ONLY")
            auto_add_music = args.get("auto_add_music", False)
            disable_duet = args.get("disable_duet", False)
            disable_stitch = args.get("disable_stitch", False)

            user_links = UserService.get_original_user_links(current_user.id)
            active_links = [link.link_id for link in user_links if link.status == 1]

            if not active_links:
                return Response(
                    message="Không có link nào được kích hoạt",
                    status=400,
                ).to_dict()

            link_ids = {}
            is_all = {}
            ids = []
            for post in id_posts:
                post_id = post.get("id", 0)
                id_links = post.get("link_ids", [])

                ids.append(post_id)
                push_links = []
                for link_id in id_links:
                    if not link_id:
                        continue
                    if link_id in active_links:
                        push_links.append(link_id)
                link_ids[post_id] = push_links
                is_all[post_id] = post.get("is_all", 0)

            posts = PostService.get_posts__by_ids(ids)
            if not posts:
                return Response(
                    message="Không tìm thấy bài viết",
                    status=400,
                ).to_dict()
            links = LinkService.get_not_json_links()
            link_pluck_by_id = {link.id: link for link in links}

            post_ids = []
            count_images = 0
            count_videos = 0
            for post in posts:
                post_ids.append(post.id)
                if post.type == "image":
                    count_images += 1
                if post.type == "video":
                    count_videos += 1

            total_sns_content = 0
            if current_user.batch_no_limit_sns == 0:
                total_sns_content = count_images + count_videos
                if current_user.batch_sns_remain < total_sns_content:
                    return Response(
                        message=MessageError.REQUIRED_COUPON.value["message"],
                        data={
                            "error_message": MessageError.REQUIRED_COUPON.value[
                                "error_message"
                            ],
                        },
                        code=201,
                    ).to_dict()

                redis_client.set(redis_unique_key, total_sns_content, ex=180)

                current_remain = redis_client.get(redis_user_batch_key)
                if current_remain:
                    current_remain = int(current_remain)
                    if current_remain < total_sns_content:
                        return Response(
                            message=MessageError.REQUIRED_COUPON.value["message"],
                            data={
                                "error_message": MessageError.REQUIRED_COUPON.value[
                                    "error_message"
                                ],
                            },
                            code=201,
                        ).to_dict()

                if current_remain is None:
                    current_remain = current_user.batch_sns_remain

                redis_client.set(
                    redis_user_batch_key, current_remain - total_sns_content, ex=180
                )

            social_sync = SocialPostService.create_social_sync(
                user_id=current_user.id,
                in_post_ids=id_posts,
                post_ids=post_ids,
                status="PROCESSING",
            )

            sync_id = str(social_sync.id)

            social_post_ids = []
            upload = []
            for post in posts:
                batch_id = post.batch_id
                timestamp = int(time.time())
                unique_id = uuid.uuid4().hex

                session_key = f"{timestamp}_{unique_id}"

                check_is_all = is_all.get(post.id, 0)
                check_links = link_ids.get(post.id, [])

                if check_is_all == 1:
                    check_links = active_links

                for link_id in check_links:
                    link = link_pluck_by_id.get(link_id)
                    if not link:
                        continue
                    if post.type == "blog" and link.social_type != "BLOG":
                        continue
                    if (
                        post.type == "image" or post.type == "video"
                    ) and link.social_type != "SOCIAL":
                        continue
                    if post.type == "image" and link.type == "YOUTUBE":
                        continue

                    social_post = SocialPostService.create_social_post(
                        link_id=link_id,
                        user_id=current_user.id,
                        post_id=post.id,
                        batch_id=batch_id,
                        session_key=session_key,
                        sync_id=sync_id,
                        status="PROCESSING",
                        disable_comment=disable_comment,
                        privacy_level=privacy_level,
                        auto_add_music=auto_add_music,
                        disable_duet=disable_duet,
                        disable_stitch=disable_stitch,
                    )

                    social_post_ids.append(social_post.id)

                    upload.append(
                        {
                            "title": link.title,
                            "link_id": link_id,
                            "post_id": post.id,
                            "status": "PROCESSING",
                            "social_link": "",
                            "value": 0,
                            "self_value": 0,
                        }
                    )

                    message = {
                        "action": "SEND_POST_TO_LINK",
                        "message": {
                            "sync_id": sync_id,
                            "link_id": link_id,
                            "post_id": post.id,
                            "user_id": current_user.id,
                            "social_post_id": str(social_post.id),
                            "page_id": "",
                            "is_all": 1,
                        },
                    }

                    if link.type == "FACEBOOK":
                        send_facebook_message(message)
                    if link.type == "TIKTOK":
                        send_tiktok_message(message)
                    if link.type == "X":
                        send_twitter_message(message)
                    if link.type == "YOUTUBE":
                        send_youtube_message(message)
                    if link.type == "THREAD":
                        send_thread_message(message)
                    if link.type == "INSTAGRAM":
                        send_instagram_message(message)

            progress = {
                "sync_id": sync_id,
                "post_ids": post_ids,
                "user_id": current_user.id,
                "total_post": len(posts),
                "total_percent": 0,
                "status": "PROCESSING",
                "upload": upload,
            }

            social_sync.social_post_ids = social_post_ids
            social_sync.save()
            redis_client.set(
                f"toktak:progress-sync:{sync_id}", json.dumps(progress), ex=1800
            )

            if current_user.batch_no_limit_sns == 0:
                current_user.batch_sns_remain -= total_sns_content
                current_user.save()

            return Response(
                data={
                    "sync_id": sync_id,
                    "upload": upload,
                },
                message="Tạo bài viết thành công. Vui lòng đợi trong giây lát",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            if current_user.batch_no_limit_sns == 0:
                current_remain = redis_client.get(redis_user_batch_key)
                total_sns = redis_client.get(redis_unique_key)
                redis_client.set(
                    redis_user_batch_key, current_remain + int(total_sns), ex=180
                )
            return Response(
                message="Tạo bài viết that bai",
                status=400,
            ).to_dict()


@ns.route("/post-to-links")
class APIPostToLinks(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "is_all": {"type": "integer"},
            "link_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "uniqueItems": True,
            },
            "post_id": {"type": "integer"},
            "page_id": {"type": "string"},
            "disable_comment": {"type": "boolean"},
            "disable_duet": {"type": "boolean"},
            "disable_stitch": {"type": "boolean"},
            "privacy_level": {
                "type": "string",
                "enum": [
                    "PUBLIC_TO_EVERYONE",
                    "MUTUAL_FOLLOW_FRIENDS",
                    "FOLLOWER_OF_CREATOR",
                    "SELF_ONLY",
                ],
            },
            "auto_add_music": {"type": "boolean"},
        },
        required=["post_id"],
    )
    def post(self, args):
        current_user = AuthService.get_current_identity()
        current_user_id = current_user.id
        redis_user_batch_key = f"toktak:users:batch_sns_remain:{current_user_id}"

        current_time = int(time.time())
        unique_id = uuid.uuid4().hex
        unique_key = f"{current_time}_{unique_id}"
        redis_unique_key = f"toktak:users:batch_sns_type:{unique_key}"
        try:
            is_all = args.get("is_all", 0)
            post_id = args.get("post_id", 0)
            page_id = args.get("page_id", "")
            link_ids = args.get("link_ids", [])
            disable_comment = args.get("disable_comment", False)
            privacy_level = args.get("privacy_level", "SELF_ONLY")
            auto_add_music = args.get("auto_add_music", False)
            disable_duet = args.get("disable_duet", False)
            disable_stitch = args.get("disable_stitch", False)

            redis_check_posting = f"toktak:posts:{post_id}:posting_sns"
            is_posting = redis_client.get(redis_check_posting)
            if is_posting:
                return Response(
                    message="Bài viết đang được gửi đi",
                    status=400,
                ).to_dict()

            redis_client.set(redis_check_posting, 1, ex=180)

            if not link_ids and is_all == 0:
                return Response(
                    message="Thiếu thông tin link",
                    status=400,
                ).to_dict()

            active_links = []
            if is_all == 0 and len(link_ids) > 0:
                for link_id in link_ids:
                    user_link = UserService.find_user_link(link_id, current_user.id)
                    if not user_link:
                        continue
                    if user_link.status == 0:
                        continue
                    active_links.append(link_id)

            if is_all == 1:
                user_links = UserService.get_original_user_links(current_user.id)
                active_links = [link.link_id for link in user_links if link.status == 1]

            if not active_links:
                return Response(
                    message="Không có link nào được kích hoạt",
                    status=400,
                ).to_dict()

            post = PostService.find_post(post_id)
            if not post:
                return Response(
                    message="Không tìm thấy bài viết",
                    status=400,
                ).to_dict()

            redis_client.set(redis_unique_key, post.type, ex=180)

            if current_user.batch_no_limit_sns == 0 and (
                post.type == "video" or post.type == "image"
            ):
                if current_user.batch_sns_remain < 1:
                    return Response(
                        message=MessageError.REQUIRED_COUPON.value["message"],
                        data={
                            "error_message": MessageError.REQUIRED_COUPON.value[
                                "error_message"
                            ],
                        },
                        status=400,
                    ).to_dict()

                current_remain = redis_client.get(redis_user_batch_key)
                if current_remain:
                    current_remain = int(current_remain)
                    if current_remain < 1:
                        return Response(
                            message=MessageError.REQUIRED_COUPON.value["message"],
                            data={
                                "error_message": MessageError.REQUIRED_COUPON.value[
                                    "error_message"
                                ],
                            },
                            status=400,
                        ).to_dict()

                if current_remain is None:
                    current_remain = current_user.batch_sns_remain

                redis_client.set(redis_user_batch_key, current_remain - 1, ex=180)

            # Update to Uploads
            PostService.update_post(post_id, status=const.DRAFT_STATUS)

            batch_id = post.batch_id

            batch_detail = BatchService.find_batch(batch_id)
            if batch_detail:
                BatchService.update_batch(batch_id, process_status="UPLOAD_SNS")

            links = LinkService.get_not_json_links()
            link_pluck_by_id = {link.id: link for link in links}

            posts = PostService.get_posts__by_batch_id(batch_id)

            total_post = 0
            post_checked = {}
            for post_to_check in posts:
                for link_id in active_links:
                    if post_checked.get(post_to_check.id):
                        continue
                    link = link_pluck_by_id.get(link_id)
                    if not link:
                        continue
                    if post_to_check.type == "blog" and link.social_type != "BLOG":
                        continue
                    if (
                        post_to_check.type == "image" or post_to_check.type == "video"
                    ) and link.social_type != "SOCIAL":
                        continue
                    if post_to_check.type == "image" and link.type == "YOUTUBE":
                        continue
                    post_checked[post_to_check.id] = post_to_check
                    total_post += 1

            total_link = 0
            for link_id in active_links:
                link = link_pluck_by_id.get(link_id)
                if not link:
                    continue
                if post.type == "blog" and link.social_type != "BLOG":
                    continue
                if (
                    post.type == "image" or post.type == "video"
                ) and link.social_type != "SOCIAL":
                    continue
                if post.type == "image" and link.type == "YOUTUBE":
                    continue
                total_link += 1

            progress = {
                "batch_id": batch_id,
                "post_id": post.id,
                "user_id": current_user.id,
                "total_link": total_link,
                "total_post": total_post,
                "total_percent": 0,
                "status": "PROCESSING",
                "upload": [],
            }

            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex

            session_key = f"{timestamp}_{unique_id}"

            for link_id in active_links:
                link = link_pluck_by_id.get(link_id)
                if not link:
                    continue
                if post.type == "blog" and link.social_type != "BLOG":
                    continue
                if (
                    post.type == "image" or post.type == "video"
                ) and link.social_type != "SOCIAL":
                    continue

                if post.type == "image" and link.type == "YOUTUBE":
                    continue

                social_post = SocialPostService.create_social_post(
                    link_id=link_id,
                    user_id=current_user.id,
                    post_id=post.id,
                    batch_id=batch_id,
                    session_key=session_key,
                    disable_comment=disable_comment,
                    privacy_level=privacy_level,
                    auto_add_music=auto_add_music,
                    disable_duet=disable_duet,
                    disable_stitch=disable_stitch,
                    status="PROCESSING",
                )

                progress["upload"].append(
                    {
                        "title": link.title,
                        "link_id": link_id,
                        "post_id": post.id,
                        "status": "PROCESSING",
                        "social_link": "",
                        "value": 0,
                    }
                )

                message = {
                    "action": "SEND_POST_TO_LINK",
                    "message": {
                        "sync_id": "",
                        "link_id": link_id,
                        "post_id": post.id,
                        "user_id": current_user.id,
                        "social_post_id": str(social_post.id),
                        "page_id": page_id,
                        "is_all": is_all,
                    },
                }

                if link.type == "FACEBOOK":
                    send_facebook_message(message)
                if link.type == "TIKTOK":
                    send_tiktok_message(message)
                if link.type == "X":
                    send_twitter_message(message)
                if link.type == "YOUTUBE":
                    send_youtube_message(message)
                if link.type == "THREAD":
                    send_thread_message(message)
                if link.type == "INSTAGRAM":
                    send_instagram_message(message)

            key_progress = f"{batch_id}_{current_user.id}"

            redis_client.set(
                f"toktak:progress:{key_progress}:{post_id}",
                json.dumps(progress),
                ex=1800,
            )

            return Response(
                message="Tạo bài viết thành công. Vui lòng đợi trong giây lát",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            current_type = redis_client.get(redis_unique_key)
            if current_user.batch_no_limit_sns == 0 and (
                current_type == "video" or current_type == "image"
            ):
                current_remain = redis_client.get(redis_user_batch_key)
                redis_client.set(redis_user_batch_key, int(current_remain) + 1, ex=180)
            return Response(
                message="Tạo bài viết that bai",
                status=400,
            ).to_dict()


@ns.route("/get-facebook-page")
class APIGetFacebookPage(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={},
        required=[],
    )
    def get(self, args):
        current_user = AuthService.get_current_identity()
        user_links = UserService.get_original_user_links(current_user.id)
        link = LinkService.find_link_by_type("FACEBOOK")
        if not link:
            return Response(
                message="Không tìm thấy link Facebook",
                status=400,
            ).to_dict()
        facebook_links = []
        for user_link in user_links:
            if user_link.link_id == link.id:
                facebook_links.append(user_link)
        if not facebook_links:
            return Response(
                message="Không có link Facebook",
                status=400,
            ).to_dict()
        list_pages = []
        for link in facebook_links:
            token_pages = FacebookTokenService().fetch_page_token(link)
            if not token_pages:
                continue
            for page in token_pages:
                list_pages.append(
                    {
                        "id": page.get("id"),
                        "name": page.get("name"),
                        "picture": page.get("picture"),
                    }
                )
        return Response(
            data=list_pages,
            message="Lấy link Facebook thành công",
        ).to_dict()


TIKTOK_REDIRECT_URL = (
    os.environ.get("CURRENT_DOMAIN") + "/api/v1/user/oauth/tiktok-callback"
)
TIKTOK_AUTHORIZATION_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY") or ""
TIKTOK_CLIENT_SECRET_KEY = os.environ.get("TIKTOK_CLIENT_SECRET") or ""


@ns.route("/oauth/tiktok-login")
class APITiktokLogin(Resource):

    @parameters(
        type="object",
        properties={
            "user_id": {"type": "string"},
            "link_id": {"type": "string"},
        },
        required=["user_id", "link_id"],
    )
    def get(self, args):
        try:
            user_id = args.get("user_id")
            link_id = args.get("link_id")

            state_token = self.generate_state_token(user_id, link_id)
            scope = "user.info.basic,user.info.profile,video.publish,video.upload"

            params = {
                "client_key": TIKTOK_CLIENT_KEY,
                "scope": scope,
                "redirect_uri": TIKTOK_REDIRECT_URL,
                "state": state_token,
                "response_type": "code",
                "disable_auto_auth": 1,
            }
            url = f"{TIKTOK_AUTHORIZATION_URL}?{urlencode(params)}"

            return redirect(url)
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error send post to link: {str(e)}")
            return False

    def generate_state_token(self, user_id, link_id):

        nonce = secrets.token_urlsafe(16)
        payload = {
            "nonce": nonce,
            "user_id": user_id,
            "link_id": link_id,
            "exp": (datetime.datetime.now() + datetime.timedelta(days=30)).timestamp(),
        }
        token = jwt.encode(payload, TIKTOK_CLIENT_SECRET_KEY, algorithm="HS256")
        return token


@ns.route("/oauth/tiktok-callback")
class APIGetCallbackTiktok(Resource):

    @parameters(
        type="object",
        properties={
            "code": {"type": "string"},
            "state": {"type": "string"},
            "error": {"type": "string"},
            "error_description": {"type": "string"},
        },
        required=["code", "state"],
    )
    def get(self, args):
        try:
            code = args.get("code")
            state = args.get("state")
            error = args.get("error") or ""
            error_description = args.get("error_description") or ""
            PAGE_PROFILE = (
                os.environ.get("TIKTOK_REDIRECT_TO_PROFILE")
                or "https://toktak.ai/profile"
            )

            if not state:
                return Response(
                    message="Invalid or expired state token 1",
                    status=400,
                ).to_dict()

            payload = self.verify_state_token(state)

            if not payload:
                return Response(
                    message="Invalid or expired state token 2",
                    status=400,
                ).to_dict()

            if error:
                return Response(
                    message=error_description,
                    status=400,
                ).to_dict()

            TiktokCallbackService().create_tiktok_callback(
                code=code,
                state=state,
                response="{}",
                error=error,
                error_description=error_description,
            )

            TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

            r_data = {
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET_KEY,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": TIKTOK_REDIRECT_URL,
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(TOKEN_URL, data=r_data, headers=headers)

            try:
                token_data = response.json()
            except Exception as e:
                return f"Error parsing response: {e}", 500

            user_id = payload.get("user_id")
            link_id = payload.get("link_id")
            int_user_id = int(user_id)
            int_link_id = int(link_id)
            user_link = UserService.find_user_link_exist(int_link_id, int_user_id)

            RequestSocialLogService.create_request_social_log(
                social="TIKTOK",
                user_id=int_user_id,
                type="authorization_code",
                request=json.dumps(r_data),
                response=json.dumps(token_data),
            )

            message = token_data.get("message")

            if message and message == "error":
                error_data = token_data.get("data")
                error = error_data.get("error_code")
                error_description = error_data.get("description")
                return redirect(
                    PAGE_PROFILE
                    + "?error="
                    + error
                    + "&error_description="
                    + error_description
                )

            token = token_data.get("data")
            if not token:
                token = token_data

            if not user_link:
                user_link = UserService.create_user_link(
                    user_id=int_user_id,
                    link_id=int_link_id,
                    status=1,
                    meta=json.dumps(token),
                )
            else:
                user_link.meta = json.dumps(token)
                user_link.status = 1
                user_link.save()

                NotificationServices.create_notification(
                    user_id=int_user_id,
                    title="TIKTOK 연결이 완료되었습니다.",
                )

                PostService.update_default_template(int_user_id, link_id)

            user_info = TiktokTokenService().fetch_user_info(user_link)
            logger.info(f"-----------TIKTOK DATA: {user_info}-------------")
            if user_info:
                social_id = user_info.get("id") or ""
                username = user_info.get("username") or ""
                name = user_info.get("name") or ""
                avatar = user_info.get("avatar") or ""
                url = user_info.get("url") or ""

                user_link.social_id = social_id
                user_link.username = username
                user_link.name = name
                user_link.avatar = avatar
                user_link.url = url
                user_link.save()

            return redirect(PAGE_PROFILE + "?tabIndex=2&success=1")
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error send post to link: {str(e)}")
            return "Can't connect to Tiktok", 500

    def verify_state_token(self, token):
        try:
            payload = jwt.decode(token, TIKTOK_CLIENT_SECRET_KEY, algorithms=["HS256"])
            return payload
        except Exception as e:
            print(f"Error verify state token: {str(e)}")
            return None


@ns.route("/oauth/tiktok-refresh-token")
class APIRefreshTiktokToken(Resource):

    @jwt_required()
    @parameters(
        type="object",
        properties={
            "link_id": {"type": "integer"},
        },
        required=["link_id"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            link_id = args.get("link_id")
            link = LinkService.find_link(link_id)
            if not link:
                return Response(
                    message="Không tìm thấy link",
                    status=400,
                ).to_dict()

            refresh_token = TiktokTokenService().refresh_token(link, current_user)
            print("Refresh token:", refresh_token)
            if not refresh_token:
                return Response(
                    message="Không tìm thấy refresh token",
                    status=400,
                ).to_dict()

            return Response(data=refresh_token, message="Refresh token").to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Lỗi kết nối",
                status=400,
            ).to_dict()


YOUTUBE_REDIRECT_URL = (
    os.environ.get("CURRENT_DOMAIN") + "/api/v1/user/oauth/youtube-callback"
)
YOUTUBE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/auth"
STATE_SECRET_KEY = "zSmXIs9UmLkfyADvWKazaiVzAk2gFwFe"


@ns.route("/oauth/youtube-login")
class APIYoutubeLogin(Resource):

    @parameters(
        type="object",
        properties={
            "user_id": {"type": "string"},
            "link_id": {"type": "string"},
        },
        required=["user_id", "link_id"],
    )
    def get(self, args):
        try:
            user_id = args.get("user_id")
            link_id = args.get("link_id")

            client = YoutubeClientService.get_client_by_user_id(user_id)
            if not client:
                # all_clients = redis_client.get("toktak:all_clients")
                # if all_clients:
                #     all_clients = json.loads(all_clients)
                #     client = random.choice(all_clients) if all_clients else None
                # else:
                client = YoutubeClientService.get_random_client()
                client = client.to_json() if client else None

            if not client:
                PAGE_PROFILE = (
                    os.environ.get("TIKTOK_REDIRECT_TO_PROFILE")
                    or "https://toktak.ai/profile"
                )

                return redirect(PAGE_PROFILE + "?tabIndex=2&error=Not found client")

            state_token = self.generate_state_token(client, user_id, link_id)
            scope = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"

            params = {
                "client_id": (
                    client.client_id
                    if isinstance(client, YoutubeClient)
                    else client.get("client_id")
                ),
                "redirect_uri": YOUTUBE_REDIRECT_URL,
                "response_type": "code",
                "scope": scope,
                "state": state_token,
                "include_granted_scopes": "true",
                "access_type": "offline",
                "prompt": "consent",
            }
            url = f"{YOUTUBE_AUTHORIZATION_URL}?{urlencode(params)}"

            logger.info(f"Redirect to Youtube: {url}")

            return redirect(url)
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error redirect oauth youtube: {str(e)}")
            return False

    def generate_state_token(self, client, user_id, link_id):
        nonce = secrets.token_urlsafe(16)
        client_id = client.id if isinstance(client, YoutubeClient) else client.get("id")
        payload = {
            "nonce": nonce,
            "user_id": user_id,
            "link_id": link_id,
            "client_id": str(client_id),
            "exp": (datetime.datetime.now() + datetime.timedelta(days=30)).timestamp(),
        }
        token = jwt.encode(payload, STATE_SECRET_KEY, algorithm="HS256")
        return token


@ns.route("/oauth/youtube-callback")
class APIGetCallbackYoutube(Resource):

    @parameters(
        type="object",
        properties={
            "code": {"type": "string"},
            "state": {"type": "string"},
        },
        required=["code", "state"],
    )
    def get(self, args):
        try:
            code = args.get("code")
            state = args.get("state")
            PAGE_PROFILE = (
                os.environ.get("TIKTOK_REDIRECT_TO_PROFILE")
                or "https://toktak.ai/profile"
            )

            if not state:
                return Response(
                    message="Invalid or expired state token 1",
                    status=400,
                ).to_dict()

            payload = self.verify_state_token(state)

            if not payload:
                return Response(
                    message="Invalid or expired state token 2",
                    status=400,
                ).to_dict()

            client_id = payload.get("client_id")
            client = YoutubeClientService.find_client_by_id(client_id)
            user_id = payload.get("user_id")
            link_id = payload.get("link_id")
            int_user_id = int(user_id)
            int_link_id = int(link_id)

            if not client:
                NotificationServices.create_notification(
                    user_id=user_id,
                    status=const.NOTIFICATION_FALSE,
                    title="Youtube 연결에 실패했습니다. 계정 정보를 확인해주세요.",
                )
                return Response(
                    message="Invalid client",
                    status=400,
                ).to_dict()

            user_link = UserService.find_user_link_exist(int_link_id, int_user_id)
            if not user_link:
                user_link = UserService.create_user_link(
                    user_id=int_user_id,
                    link_id=int_link_id,
                    status=1,
                    meta=json.dumps({}),
                )
                NotificationServices.create_notification(
                    user_id=int_user_id,
                    title="Youtube 연결이 완료되었습니다.",
                )
                PostService.update_default_template(int_user_id, link_id)

            response = YoutubeTokenService().exchange_code_for_token(
                code=code,
                user_link=user_link,
                client=client,
            )
            if not response:
                NotificationServices.create_notification(
                    user_id=user_id,
                    status=const.NOTIFICATION_FALSE,
                    title="Youtube 연결에 실패했습니다. 계정 정보를 확인해주세요.",
                )
                return Response(
                    message="Lỗi kết nối",
                    status=400,
                ).to_dict()

            user_info = YoutubeTokenService().fetch_channel_info(user_link)
            if user_info:
                social_id = user_info.get("id") or ""
                username = user_info.get("username") or ""
                name = user_info.get("name") or ""
                avatar = user_info.get("avatar") or ""
                url = user_info.get("url") or ""

                user_link.social_id = social_id
                user_link.username = username
                user_link.name = name
                user_link.avatar = avatar
                user_link.url = url
                user_link.youtube_client = json.dumps(client.to_json())
                user_link.status = 1
                user_link.save()

                client.user_ids.append(user_id)
                client.member_count += 1
                client.save()
            else:
                user_link.status = 0
                user_link.save()
                return redirect(
                    PAGE_PROFILE
                    + "?tabIndex=2&error=ERROR_FETCHING_CHANNEL&error_message=Can't fetch channel info"
                )

            return redirect(PAGE_PROFILE + "?tabIndex=2&success=1")
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error send post to link: {str(e)}")
            return "Can't connect to Youtube", 500

    def verify_state_token(self, token):
        try:
            payload = jwt.decode(token, STATE_SECRET_KEY, algorithms=["HS256"])
            return payload
        except Exception as e:
            print(f"Error verify state token: {str(e)}")
            return None


@ns.route("/oauth/ali-login")
class APITiktokLogin(Resource):

    @parameters(
        type="object",
        properties={
            "user_id": {"type": "string"},
        },
        required=["user_id"],
    )
    def get(self, args):
        try:
            user_id = args.get("user_id")
            state_token = self.generate_state_token(user_id)

            ALI_APP_KEY = os.environ.get("ALI_APP_KEY") or ""
            ALI_REDIRECT_URL = os.environ.get("ALI_REDIRECT_URL") or ""

            params = {
                "client_id": ALI_APP_KEY,
                "redirect_uri": ALI_REDIRECT_URL,
                "state": state_token,
                "response_type": "code",
            }
            url = f"https://api-sg.aliexpress.com/oauth/authorize?{urlencode(params)}"

            logger.info(f"Redirect to Ali: {url}")

            return redirect(url)
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            print(f"Error send post to link: {str(e)}")
            return False

    def generate_state_token(self, user_id):
        nonce = secrets.token_urlsafe(16)
        ALI_APP_SECRET = os.environ.get("ALI_APP_SECRET") or ""
        payload = {
            "nonce": nonce,
            "user_id": user_id,
            "exp": (datetime.datetime.now() + datetime.timedelta(days=7)).timestamp(),
        }
        token = jwt.encode(payload, ALI_APP_SECRET, algorithm="HS256")
        return token


@ns.route("/oauth/ali-callback")
class APIAliCallback(Resource):

    @parameters(
        type="object",
        properties={
            "code": {"type": "string"},
            "state": {"type": "string"},
        },
        required=["code", "state"],
    )
    def get(self, args):
        try:
            code = args.get("code")
            state = args.get("state")

            PAGE_PROFILE = "https://voda-play.com/profile"

            if not state:
                return Response(
                    message="Invalid or expired state token 1",
                    status=400,
                ).to_dict()

            payload = self.verify_state_token(state)

            if not payload:
                return Response(
                    message="Invalid or expired state token 2",
                    status=400,
                ).to_dict()

            user_id = payload.get("user_id")
            user = UserService.find_user(user_id)
            if not user:
                return Response(
                    message="Không tìm thấy người dùng",
                    status=400,
                ).to_dict()

            access_response = TokenAliExpress().get_access_token(code)
            if not access_response:
                return Response(
                    message="Lỗi kết nối",
                    status=400,
                ).to_dict()

            user.ali_express_info = json.dumps(access_response)
            user.ali_express_active = 1
            user.save()

            # return Response(
            #     data=access_response,
            #     message="AliExpress login success",
            # ).to_dict()

            return redirect(PAGE_PROFILE + "?success=1")
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Lỗi kết nối",
                status=400,
            ).to_dict()

    def verify_state_token(self, token):
        try:
            ALI_APP_SECRET = os.environ.get("ALI_APP_SECRET") or ""
            payload = jwt.decode(token, ALI_APP_SECRET, algorithms=["HS256"])
            return payload
        except Exception as e:
            print(f"Error verify state token: {str(e)}")
            return None


@ns.route("/check-sns-link")
class APICheckSNSLink(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "batchId": {"type": ["string", "null"]},
        },
        required=[],
    )
    def post(self, args):
        try:
            batchId = args.get("batchId", None)
            current_user = AuthService.get_current_identity()
            if not current_user:
                return Response(
                    message="로그인하여 계속 진행하십시오.",
                    code=201,
                ).to_dict()

            if current_user.subscription == "FREE":
                return Response(
                    message=MessageError.REQUIRED_COUPON.value["message"],
                    data={
                        "error_message": MessageError.REQUIRED_COUPON.value[
                            "error_message"
                        ]
                    },
                    code=201,
                ).to_dict()

            if batchId:
                if current_user.batch_remain == 0:
                    return Response(
                        message=MessageError.NO_BATCH_REMAINING.value["message"],
                        data={
                            "error_message": MessageError.NO_BATCH_REMAINING.value[
                                "error_message"
                            ]
                        },
                        code=201,
                    ).to_dict()
                if (
                    current_user.batch_sns_remain < 2
                    and current_user.batch_no_limit_sns == 0
                ):
                    return Response(
                        message=MessageError.REQUIRED_COUPON.value["message"],
                        data={
                            "error_message": MessageError.REQUIRED_COUPON.value[
                                "error_message"
                            ]
                        },
                        code=201,
                    ).to_dict()

                current_batch_sns = redis_client.get(
                    f"toktak:users:batch_sns_remain:{current_user.id}"
                )
                if current_batch_sns and int(current_batch_sns) < 2:
                    return Response(
                        message=MessageError.REQUIRED_COUPON.value["message"],
                        data={
                            "error_message": MessageError.REQUIRED_COUPON.value[
                                "error_message"
                            ]
                        },
                        code=201,
                    ).to_dict()

                BatchService.update_batch(batchId, user_id=current_user.id)
                PostService.update_post_by_batch_id(batchId, user_id=current_user.id)

                user_links = UserService.get_original_user_links(current_user.id)
                links = LinkService.get_not_json_links()
                link_pluck_by_id = {link.id: link for link in links}

                active_links = []
                for user_link in user_links:
                    if user_link.link_id not in link_pluck_by_id:
                        continue
                    if user_link.status == 0:
                        continue
                    link = link_pluck_by_id.get(user_link.link_id)
                    if link.type != "BLOG_NAVER":
                        active_links.append(user_link.link_id)

                if not active_links:
                    return Response(
                        message=MessageError.REQUIRE_LINK.value["message"],
                        data={
                            "error_message": MessageError.REQUIRE_LINK.value[
                                "error_message"
                            ]
                        },
                        code=202,
                    ).to_dict()

                batch_detail = BatchService.find_batch(batchId)
                if not batch_detail:
                    return Response(
                        message="Batch not found",
                        code=201,
                    ).to_dict()
                is_valid_video = False
                is_valid_images = False
                posts = PostService.get_posts_by_batch(batchId)
                for post in posts:
                    if post.type == "video":
                        video_url = post.video_url
                        video_path = post.video_path
                        if (
                            video_url
                            and video_url != ""
                            and video_path
                            and video_path != ""
                        ):
                            is_valid_video = True
                    if post.type == "image":
                        images = post.images
                        images = json.loads(images) if images else []
                        if images and len(images) > 0:
                            is_valid_images = True

                if not is_valid_video:
                    return Response(
                        message=MessageError.CHECK_CREATE_POST_VIDEO.value["message"],
                        data={
                            "error_message": MessageError.CHECK_CREATE_POST_VIDEO.value[
                                "error_message"
                            ]
                        },
                        code=201,
                    ).to_dict()
                if not is_valid_images:
                    return Response(
                        message=MessageError.CHECK_CREATE_POST_IMAGE.value["message"],
                        data={
                            "error_message": MessageError.CHECK_CREATE_POST_IMAGE.value[
                                "error_message"
                            ]
                        },
                        code=201,
                    ).to_dict()

            return Response(
                message="Check Active Link Success",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Check Active",
                code=201,
            ).to_dict()


@ns.route("/user_detail")
class APIUserDetail(Resource):
    @jwt_required()
    def post(self):
        try:
            current_user = AuthService.get_current_identity()
            if not current_user:
                return Response(
                    message="Please login",
                    code=201,
                ).to_dict()

            return Response(
                data=current_user.to_dict(),
                message="Check User Success",
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(e)))
            return Response(
                message="Check Active",
                code=201,
            ).to_dict()


@ns.route("/delete-link-sns")
class APIDeleteLink(Resource):
    @jwt_required()
    @parameters(
        type="object",
        properties={
            "link_id": {"type": "integer"},
        },
        required=["link_id"],
    )
    def post(self, args):
        try:
            current_user = AuthService.get_current_identity()
            link_id = args.get("link_id", 0)

            user_link = UserService.find_user_link(link_id, current_user.id)
            if not user_link:
                return Response(
                    message="링크 삭제에 실패했습니다.",
                    data={"user_id": current_user.id},
                    code=201,
                ).to_dict()
            else:
                user_link.delete()
                user_template = PostService.get_template_video_by_user_id(
                    current_user.id
                )

                if user_template:
                    link_sns = json.loads(user_template.link_sns)
                    if link_id in link_sns["video"]:
                        link_sns["video"].remove(link_id)
                    if link_id in link_sns["image"]:
                        link_sns["image"].remove(link_id)

                    data_update_template = {
                        "link_sns": json.dumps(link_sns),
                    }

                    user_template = PostService.update_template(
                        user_template.id, **data_update_template
                    )

            return Response(
                data={},
                message="링크 삭제에 성공했습니다.",
            ).to_dict()
        except Exception as ex:
            traceback.print_exc()
            logger.error("Exception: {0}".format(str(ex)))
            return Response(
                message="링크 삭제에 실패했습니다.",
                code=202,
            ).to_dict()


@ns.route("/get-user-link-template")
class APIUserLinkTemplate(Resource):
    @jwt_required()
    def get(self):
        urrent_user = AuthService.get_current_identity()
        user_id = urrent_user.id
        all_links = LinkService.get_all_links()

        # Lấy template lưu trữ các lựa chọn
        user_template = PostService.get_template_video_by_user_id(user_id)

        link_sns_data = {"video": [], "image": []}

        if user_template and user_template.link_sns:
            try:
                link_sns_data = json.loads(user_template.link_sns)
            except Exception:
                pass

        # Hàm dựng danh sách link cho mỗi loại
        def build_link_array(selected_ids):
            return [
                {
                    "id": link["id"],
                    "avatar": link["avatar"],
                    "title": link["title"],
                    "type": link["type"],
                    "selected": 1 if link["id"] in selected_ids else 0,
                }
                for link in all_links
            ]

        result = {
            "video": build_link_array(link_sns_data.get("video", [])),
            "image": build_link_array(link_sns_data.get("image", [])),
        }

        return Response(
            data=result, message="SNS 정보를 성공적으로 가져왔습니다."
        ).to_dict()


@ns.route("/update-user-link-template")
class APIUpdateUserLinkTemplate(Resource):
    @jwt_required()
    def post(self):
        urrent_user = AuthService.get_current_identity()
        user_id = urrent_user.id

        payload = ns.payload or {}

        video_links = payload.get("video", [])
        image_links = payload.get("image", [])

        link_sns_json = json.dumps({"video": video_links, "image": image_links})

        data_update_template = {
            "link_sns": link_sns_json,
        }

        user_template = PostService.get_template_video_by_user_id(user_id)

        if user_template:
            user_template = PostService.update_template(
                user_template.id, **data_update_template
            )

        return Response(
            data={}, message="링크 선택이 성공적으로 업데이트되었습니다."
        ).to_dict()
