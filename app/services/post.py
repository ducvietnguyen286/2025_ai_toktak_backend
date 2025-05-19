from app.models.user import User
from app.models.post import Post
from app.models.user_video_templates import UserVideoTemplates
from app.models.link import Link
from app.models.social_post import SocialPost
from app.extensions import db
from sqlalchemy import and_, func, or_
from flask import jsonify
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased
from app.services.image_template import ImageTemplateService
import os
import json
import const
from app.lib.query import (
    select_with_filter,
    select_by_id,
    select_with_pagination,
    select_with_filter_one,
)
from sqlalchemy import update, delete


class PostService:

    @staticmethod
    def create_post(*args, **kwargs):
        post = Post(*args, **kwargs)
        post.save()
        return post

    @staticmethod
    def find_post(id):
        post = select_by_id(Post, id)
        return post

    @staticmethod
    def get_posts():
        posts = select_with_filter(
            Post, order_by=[Post.id.desc()], filters=[Post.status == 1]
        )
        return [post._to_json() for post in posts]

    @staticmethod
    def get_posts__by_ids(ids):
        posts = select_with_filter(
            Post,
            order_by=[Post.id.desc()],
            filters=[Post.id.in_(ids), Post.status.in_([1, 99])],
        )
        return posts

    @staticmethod
    def update_posts_by_ids(ids, *args, **kwargs):
        stmt = update(Post).where(Post.id.in_(ids)).values(**kwargs)
        db.session.execute(stmt)
        db.session.commit()
        return True

    def get_posts_by_batch(batch_id):
        posts = select_with_filter(
            Post,
            order_by=[Post.id.desc()],
            filters=[Post.batch_id == batch_id],
        )
        return posts

    @staticmethod
    def update_post(id, *args, **kwargs):
        post = select_by_id(Post, id)
        if not post:
            return None
        post.update(**kwargs)
        return post

    @staticmethod
    def delete_post(id):
        post = select_by_id(Post, id)
        if not post:
            return None
        post.delete()
        return True

    @staticmethod
    def get_posts_by_batch_id(batch_id):
        posts = select_with_filter(
            Post,
            order_by=[Post.id.desc()],
            filters=[Post.batch_id == batch_id],
        )
        return [post._to_json() for post in posts]

    @staticmethod
    def get_posts__by_batch_id(batch_id):
        posts = select_with_filter(
            Post,
            order_by=[Post.id.desc()],
            filters=[Post.batch_id == batch_id],
        )
        return posts

    @staticmethod
    def update_post_by_batch_id(batch_id, *args, **kwargs):
        stmt = update(Post).where(Post.batch_id == batch_id).values(**kwargs)
        db.session.execute(stmt)
        db.session.commit()
        return True

    @staticmethod
    def get_latest_social_post_by_post_ids(post_ids):
        subq = (
            db.session.query(func.max(SocialPost.created_at).label("max_created"))
            .filter(SocialPost.post_id.in_(post_ids))
            .group_by(SocialPost.post_id)
            .subquery()
        )
        query = db.session.query(SocialPost).join(
            subq,
            and_(
                SocialPost.post_id == subq.c.post_id,
                SocialPost.created_at == subq.c.max_created,
            ),
        )
        results = query.all()
        return results

    @staticmethod
    def get_social_post(post_id):

        results = (
            db.session.query(SocialPost, Link.title)
            .select_from(Link)
            .outerjoin(
                SocialPost,
                and_(SocialPost.link_id == Link.id, SocialPost.post_id == post_id),
            )
            .all()
        )

        # Chuyển đổi kết quả thành danh sách dict
        data = []
        for social_post, title in results:
            # Nếu không có SocialPost tương ứng thì social_post sẽ là None
            post_data = (
                {
                    "id": social_post.id,
                    "title": title,
                    "status": social_post.status,
                    "link_id": social_post.link_id,
                    "post_id": social_post.post_id,
                    "process_number": social_post.process_number,
                }
                if social_post
                else None
            )

            data.append(post_data)

        return data

    @staticmethod
    def get_posts_upload(data_search):
        filters = [
            Post.user_id == data_search["user_id"],
        ]
        if data_search["status"] == 1:
            filters.append(
                or_(
                    Post.social_sns_description.like("%PUBLISHED%"),
                    Post.status_sns == 1,
                )
            )
        elif data_search["status"] == 99:
            filters.append(
                or_(
                    Post.social_sns_description.like("%ERRORED%"),
                    Post.status == const.DRAFT_STATUS,
                )
            )

        search_text = data_search.get("search_text", "")
        if search_text != "":
            search_pattern = f"%{search_text}%"
            filters.append(
                or_(
                    Post.title.ilike(search_pattern),
                    Post.description.ilike(search_pattern),
                    Post.user.has(User.email.ilike(search_pattern)),
                )
            )

        if data_search["type_order"] == "id_asc":
            order_by = Post.id.asc()
        elif data_search["type_order"] == "id_desc":
            order_by = Post.id.desc()
        else:
            order_by = Post.id.desc()

        # Xử lý type_post
        if data_search["type_post"] == "video":
            filters.append(Post.type == "video")
        elif data_search["type_post"] == "image":
            filters.append(Post.type == "image")
        elif data_search["type_post"] == "blog":
            filters.append(Post.type == "blog")
        elif data_search["type_post"] == "error_blog":
            filters.append(Post.social_sns_description.like("%ERRORED%"))

        time_range = data_search.get("time_range")  # Thêm biến time_range
        # Lọc theo khoảng thời gian
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            filters.append(Post.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            filters.append(Post.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            filters.append(Post.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            filters.append(Post.created_at >= start_date)

        pagination = select_with_pagination(
            Post,
            page=data_search["page"],
            per_page=data_search["per_page"],
            filters=filters,
            order_by=[order_by],
        )
        return pagination

    @staticmethod
    def delete_posts_by_ids(post_ids):
        try:
            delete_stmt = delete(Post).where(Post.id.in_(post_ids))
            db.session.execute(delete_stmt)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1

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
    def admin_get_posts_upload(data_search):
        # Query cơ bản với các điều kiện
        # Aliases for the User table to include email
        query = Post.query.filter(
            Post.status == data_search["status"],
        )

        if data_search["status"] == 1:
            # query = query.filter(Post.status_sns == 1)
            query = query.filter(
                (Post.social_sns_description.like("%PUBLISHED%"))
                | (Post.status_sns == data_search["status"])
            )
        elif data_search["status"] == 99:
            query = query.filter(
                (Post.social_sns_description.like("%ERRORED%"))
                | (Post.status == data_search["status"])
            )

        search_text = data_search.get("search_text", "")

        if search_text != "":
            search_pattern = f"%{search_text}%"
            query = query.filter(
                or_(
                    Post.title.ilike(search_pattern),
                    Post.description.ilike(search_pattern),
                    Post.user.has(User.email.ilike(search_pattern)),
                )
            )

        # Xử lý type_order
        if data_search["type_order"] == "id_asc":
            query = query.order_by(Post.id.asc())
        elif data_search["type_order"] == "id_desc":
            query = query.order_by(Post.id.desc())
        else:
            query = query.order_by(Post.id.desc())

        # Xử lý type_post
        if data_search["type_post"] == "video":
            query = query.filter(Post.type == "video")
        elif data_search["type_post"] == "image":
            query = query.filter(Post.type == "image")
        elif data_search["type_post"] == "blog":
            query = query.filter(Post.type == "blog")

        elif data_search["type_post"] == "error_blog":
            query = query.filter(Post.social_sns_description.like("%ERRORED%"))

        time_range = data_search.get("time_range")  # Thêm biến time_range
        # Lọc theo khoảng thời gian
        if time_range == "today":
            start_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            query = query.filter(Post.created_at >= start_date)

        elif time_range == "last_week":
            start_date = datetime.now() - timedelta(days=7)
            query = query.filter(Post.created_at >= start_date)

        elif time_range == "last_month":
            start_date = datetime.now() - timedelta(days=30)
            query = query.filter(Post.created_at >= start_date)

        elif time_range == "last_year":
            start_date = datetime.now() - timedelta(days=365)
            query = query.filter(Post.created_at >= start_date)

        pagination = query.paginate(
            page=data_search["page"], per_page=data_search["per_page"], error_out=False
        )
        return pagination

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

    @staticmethod
    def get_post_schedule(data_search):
        query = Post.query.filter(Post.type != "blog")
        if "user_id" in data_search and data_search["user_id"]:
            query = query.filter(Post.user_id == data_search["user_id"])

        if "start_date" in data_search and data_search["start_date"]:
            query = query.filter(Post.schedule_date >= data_search["start_date"])

        if "end_date" in data_search and data_search["end_date"]:
            query = query.filter(Post.schedule_date <= data_search["end_date"])

        if "status" in data_search and data_search["status"]:
            query = query.filter(Post.status == data_search["status"])

        posts = query.all()

        return [post_detail.to_dict() for post_detail in posts]
