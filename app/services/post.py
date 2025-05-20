from bson import ObjectId
from app.lib.logger import logger
from app.models.post import Post
from app.models.user_video_templates import UserVideoTemplates
from app.extensions import db
from datetime import datetime, timedelta
from app.services.image_template import ImageTemplateService
import os
import json
import const
from app.lib.query import (
    select_by_id,
    select_with_filter_one,
)
from mongoengine import Q


class PostService:

    @staticmethod
    def create_post(*args, **kwargs):
        try:
            post = Post.objects.creeate(*args, **kwargs)
            logger.info(
                f"Saved Post id={post.id} vào collection: {post._get_collection_name()}"
            )
            return post
        except Exception as ex:
            logger.error(f"Error creating post: {ex}")
            return None

    @staticmethod
    def find_post(id):
        try:
            return Post.objects.get(id=ObjectId(id))
        except Post.DoesNotExist:
            return None

    @staticmethod
    def get_posts():
        posts = Post.objects(status=1)
        return posts

    @staticmethod
    def get_posts__by_ids(ids):
        posts = Post.objects(id__in=ids, status__in=[1, 99])
        return posts

    @staticmethod
    def update_posts_by_ids(ids, *args, **kwargs):
        posts = Post.objects(id__in=ids)
        for post in posts:
            for key, value in kwargs.items():
                setattr(post, key, value)
            post.save()

        return True

    def get_posts_by_batch(batch_id):
        posts = Post.objects(
            batch_id=ObjectId(batch_id),
            status__in=[1, 99],
        )
        return posts

    @staticmethod
    def update_post(id, *args, **kwargs):
        post = Post.objects.get(id=ObjectId(id))
        post.update(**kwargs)
        return post

    @staticmethod
    def delete_post(id):
        return Post.objects.get(id=ObjectId(id)).delete()

    @staticmethod
    def get_posts_by_batch_id(batch_id):
        posts = Post.objects(
            batch_id=ObjectId(batch_id),
        )
        return [post.to_json() for post in posts]

    @staticmethod
    def get_posts__by_batch_id(batch_id):
        posts = Post.objects(
            batch_id=ObjectId(batch_id),
        )
        return posts

    @staticmethod
    def update_post_by_batch_id(batch_id, *args, **kwargs):
        posts = Post.objects(batch_id=ObjectId(batch_id))
        for post in posts:
            for key, value in kwargs.items():
                setattr(post, key, value)
            post.save()

        return True

    @staticmethod
    def get_posts_upload(data_search):
        query = Post.objects(user_id=data_search["user_id"])

        status = data_search.get("status")
        if status == 1:
            query = query.filter(
                Q(social_sns_description__icontains="PUBLISHED") | Q(status_sns=1)
            )
        elif status == 99:
            query = query.filter(
                Q(social_sns_description__icontains="ERRORED")
                | Q(status=const.DRAFT_STATUS)
            )

        search_text = data_search.get("search_text", "")
        if search_text:
            query = query.filter(
                Q(title__icontains=search_text)
                | Q(description__icontains=search_text)
                | Q(user__email__icontains=search_text)
            )

        type_post = data_search.get("type_post")
        if type_post == "video":
            query = query.filter(type="video")
        elif type_post == "image":
            query = query.filter(type="image")
        elif type_post == "blog":
            query = query.filter(type="blog")
        elif type_post == "error_blog":
            query = query.filter(social_sns_description__icontains="ERRORED")

        time_range = data_search.get("time_range")
        if time_range:
            now = datetime.now()
            if time_range == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == "last_week":
                start_date = now - timedelta(days=7)
            elif time_range == "last_month":
                start_date = now - timedelta(days=30)
            elif time_range == "last_year":
                start_date = now - timedelta(days=365)
            else:
                start_date = None

            if start_date:
                query = query.filter(created_at__gte=start_date)

        type_order = data_search.get("type_order", "id_desc")
        if type_order == "id_asc":
            query = query.order_by("id")
        else:
            query = query.order_by("-id")

        page = data_search.get("page", 1)
        per_page = data_search.get("per_page", 10)
        skip = (page - 1) * per_page

        total = query.count()
        items = query.skip(skip).limit(per_page)

        total_pages = (total + per_page - 1) // per_page

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": total_pages,
            "items": list(items),
        }

    @staticmethod
    def delete_posts_by_ids(post_ids):
        try:
            deleted_count = Post.objects(id__in=post_ids).delete()
            return deleted_count
        except Exception as ex:
            return 0

    @staticmethod
    def admin_get_posts_upload(data_search):
        query = Post.objects(user_id=data_search["user_id"])

        status = data_search.get("status")
        if status == 1:
            query = query.filter(
                Q(social_sns_description__icontains="PUBLISHED") | Q(status_sns=1)
            )
        elif status == 99:
            query = query.filter(
                Q(social_sns_description__icontains="ERRORED")
                | Q(status=const.DRAFT_STATUS)
            )

        search_text = data_search.get("search_text", "")
        if search_text:
            query = query.filter(
                Q(title__icontains=search_text)
                | Q(description__icontains=search_text)
                | Q(user__email__icontains=search_text)
            )

        type_post = data_search.get("type_post")
        if type_post == "video":
            query = query.filter(type="video")
        elif type_post == "image":
            query = query.filter(type="image")
        elif type_post == "blog":
            query = query.filter(type="blog")
        elif type_post == "error_blog":
            query = query.filter(social_sns_description__icontains="ERRORED")

        time_range = data_search.get("time_range")
        if time_range:
            now = datetime.now()
            if time_range == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == "last_week":
                start_date = now - timedelta(days=7)
            elif time_range == "last_month":
                start_date = now - timedelta(days=30)
            elif time_range == "last_year":
                start_date = now - timedelta(days=365)
            else:
                start_date = None

            if start_date:
                query = query.filter(created_at__gte=start_date)

        type_order = data_search.get("type_order", "id_desc")
        if type_order == "id_asc":
            query = query.order_by("id")
        else:
            query = query.order_by("-id")

        page = data_search.get("page", 1)
        per_page = data_search.get("per_page", 10)
        skip = (page - 1) * per_page

        total = query.count()
        items = query.skip(skip).limit(per_page)

        total_pages = (total + per_page - 1) // per_page

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": total_pages,
            "items": list(items),
        }

    @staticmethod
    def get_post_schedule(data_search):
        filters = Q(type__ne="blog")
        if data_search.get("user_id"):
            filters &= Q(user_id=data_search["user_id"])

        if data_search.get("start_date"):
            filters &= Q(schedule_date__gte=data_search["start_date"])

        if data_search.get("end_date"):
            filters &= Q(schedule_date__lte=data_search["end_date"])

        if data_search.get("status") is not None:
            filters &= Q(status=data_search["status"])

        posts = Post.objects(filters)

        return [post.to_mongo().to_dict() for post in posts]

    @staticmethod
    def get_template_video_by_user_id(user_id):
        try:
            user_template = select_with_filter_one(
                UserVideoTemplates,
                filters=[UserVideoTemplates.user_id == user_id],
                order_by=[UserVideoTemplates.id.desc()],
            )
        except Exception as ex:
            return None
        return user_template

    @staticmethod
    def create_user_template(*args, **kwargs):
        user_template = UserVideoTemplates(*args, **kwargs)
        user_template.save()
        return user_template

    @staticmethod
    def update_template(id, *args, **kwargs):
        user_template = select_by_id(UserVideoTemplates, id)
        user_template.update(**kwargs)
        return user_template

    @staticmethod
    def create_user_template_make_video(user_id):
        image_templates = ImageTemplateService.get_image_templates()
        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"
        video_hooks = [
            {
                "video_name": "NViral Video_41.mp4",
                "video_url": f"{current_domain}/voice/advance/1_advance.mp4",
                "duration": 2.9,
            },
            {
                "video_name": "Video_67.mp4",
                "video_url": f"{current_domain}/voice/advance/2_advance.mp4",
                "duration": 2.42,
            },
            {
                "video_name": "Video_16.mp4",
                "video_url": f"{current_domain}/voice/advance/3_advance.mp4",
                "duration": 4.04,
            },
        ]
        viral_messages = [
            {
                "video_name": "",
                "video_url": f"{current_domain}/voice/advance/viral_message1.gif",
                "duration": 2.42,
            },
            {
                "video_name": "",
                "video_url": f"{current_domain}/voice/advance/viral_message2.gif",
                "duration": 4.04,
            },
            {
                "video_name": "",
                "video_url": f"{current_domain}/voice/advance/viral_message3.gif",
                "duration": 2.42,
            },
            {
                "video_name": "",
                "video_url": f"{current_domain}/voice/advance/viral_message4.gif",
                "duration": 4.04,
            },
            {
                "video_name": "",
                "video_url": f"{current_domain}/voice/advance/viral_message5.gif",
                "duration": 4.04,
            },
        ]
        subscribe_video = f"{current_domain}/voice/advance/subscribe_video.mp4"

        user_template = PostService.create_user_template(
            user_id=user_id,
            video_hooks=json.dumps(video_hooks),
            image_template_id=image_templates[0]["id"],
            image_template=json.dumps(image_templates),
            viral_messages=json.dumps(viral_messages),
            subscribe_video=subscribe_video,
            voice_gender=1,
            voice_id=3,
        )
        return user_template

    @staticmethod
    def update_default_template(user_id, link_id):
        try:
            link_id = int(link_id)
            user_template = PostService.get_template_video_by_user_id(user_id)

            if user_template:
                link_sns = json.loads(user_template.link_sns)

                if (
                    not link_sns
                    or not isinstance(link_sns, dict)
                    or "video" not in link_sns
                    or "image" not in link_sns
                ):
                    link_sns = {"video": [], "image": []}

                if link_id not in link_sns["video"]:
                    link_sns["video"].append(link_id)

                if link_id not in link_sns["image"]:
                    link_sns["image"].append(link_id)

                data_update_template = {
                    "link_sns": json.dumps(link_sns),
                }

                user_template = PostService.update_template(
                    user_template.id, **data_update_template
                )
        except Exception as ex:
            return None
        return user_template
