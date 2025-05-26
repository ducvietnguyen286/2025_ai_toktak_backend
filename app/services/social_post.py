import json
import traceback
from app.lib.logger import logger
from app.models.link import Link
from app.models.post import Post
from app.models.social_post import SocialPost
from app.models.social_sync import SocialSync
from app.models.user_link import UserLink

from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db

from app.lib.query import (
    select_with_filter,
    select_by_id,
    update_multiple_by_ids,
    select_with_filter_one,
    update_by_id,
)


class SocialPostService:

    @staticmethod
    def create_social_post(*args, **kwargs):
        social_post = SocialPost(*args, **kwargs)
        social_post.save()
        return social_post

    @staticmethod
    def find_social_post(id):
        return select_by_id(SocialPost, id)

    def get_all_by_post_ids(post_ids):
        return select_with_filter(
            SocialPost, filters=[SocialPost.post_id.in_(post_ids)]
        )

    @staticmethod
    def by_post_id_get_latest_social_posts(post_id):
        latest_post = select_with_filter_one(
            SocialPost,
            filters=[
                SocialPost.post_id == post_id,
            ],
            order_by=SocialPost.created_at.desc(),
        )
        if not latest_post:
            return []
        session_key = latest_post.session_key
        results = select_with_filter(
            SocialPost,
            filters=[
                SocialPost.session_key == session_key,
                SocialPost.post_id == post_id,
            ],
            order_by=SocialPost.created_at.desc(),
        )
        if not results:
            return []

        link_ids = [result.link_id for result in results]
        links = Link.query.filter(Link.id.in_(link_ids)).all()
        link_dict = {link.id: link for link in links}

        data = []
        for social_post in results:
            link = link_dict.get(social_post.link_id)
            post_data = {
                "id": social_post.id,
                "title": link.title,
                "status": social_post.status,
                "social_link": social_post.social_link,
                "link_id": social_post.link_id,
                "link_type": link.type,
                "post_id": social_post.post_id,
                "session_key": social_post.session_key,
                "process_number": social_post.process_number,
                "error_message": social_post.error_message,
            }
            data.append(post_data)

        return data

    @staticmethod
    def update_social_post(id, **kwargs):
        return update_by_id(SocialPost, id, kwargs)

    @staticmethod
    def update_multple_social_post_by__ids(ids, **args):
        return update_multiple_by_ids(SocialPost, ids, args)

    @staticmethod
    def delete_social_post(id):
        post = select_by_id(SocialPost, id)
        if post:
            post.delete()
            return True
        return False

    @staticmethod
    def create_social_sync(*args, **kwargs):
        social_sync = SocialSync(*args, **kwargs)
        social_sync.save()
        return social_sync

    @staticmethod
    def find_social_sync(id):
        return select_by_id(SocialSync, id)

    @staticmethod
    def update_social_sync(id, **kwargs):
        return update_by_id(SocialSync, id, kwargs)

    @staticmethod
    def delete_social_sync(id):
        sync = select_by_id(SocialSync, id)
        if sync:
            sync.delete()
            return True
        return False

    @staticmethod
    def get_social_syncs():
        return select_with_filter(SocialSync)

    @staticmethod
    def get_status_social_sycns__by_id(id):
        try:
            sync = select_by_id(SocialSync, id)
            if not sync:
                return {}

            social_posts = select_with_filter(
                SocialPost,
                filters=[
                    SocialPost.sync_id == sync.id,
                ],
                order_by=SocialPost.created_at.desc(),
            )

            sync_post_ids = sync.post_ids
            sync_post_ids = json.loads(sync_post_ids) if sync_post_ids else []

            post_ids = [pid for pid in sync_post_ids]

            user_links = select_with_filter(
                UserLink,
                filters=[UserLink.user_id == sync.user_id],
            )
            link_ids = [user_link.link_id for user_link in user_links]

            links = select_with_filter(
                Link,
                filters=[Link.id.in_(link_ids)],
            )
            link_dict = {link.id: link for link in links}

            posts = select_with_filter(
                Post,
                filters=[
                    Post.id.in_(post_ids),
                ],
                order_by=Post.created_at.desc(),
            )

            data = {}
            post_dict = {post.id: post for post in posts}

            for social_post in social_posts:
                social_post_id = social_post.post_id
                post = data.get(social_post_id)
                if not post:
                    post = post_dict.get(social_post_id)
                    if not post:
                        continue
                    post = post._to_json()
                link = link_dict.get(social_post.link_id)

                post_social = {
                    "id": social_post.id,
                    "title": link.title,
                    "status": social_post.status,
                    "social_link": social_post.social_link,
                    "link_id": social_post.link_id,
                    "link_type": link.type,
                    "post_id": social_post.post_id,
                    "session_key": social_post.session_key,
                    "process_number": social_post.process_number,
                    "error_message": social_post.error_message,
                }

                if "social_posts" not in post:
                    post["social_posts"] = []
                post["social_posts"].append(post_social)
                data[social_post.post_id] = post

            social_sync_data = sync._to_json()
            social_sync_data["posts"] = list(data.values())

            return social_sync_data
        except Exception as e:
            traceback.print_exc()
            logger.error(f"get_status_social_sycns__by_id: {e}")
            print(e)
            return {}

    @staticmethod
    def getTotalRunning(filters=None):
        filters = filters or {}
        query = db.session.query(SocialPost.status, func.count().label("count"))

        if "from_date" in filters:
            from_date = datetime.strptime(filters["from_date"], "%Y-%m-%d")
            query = query.filter(SocialPost.created_at >= from_date)
        if "to_date" in filters:
            to_date = datetime.strptime(filters["to_date"], "%Y-%m-%d") + timedelta(
                days=1
            )
            query = query.filter(SocialPost.created_at < to_date)

        query = query.group_by(SocialPost.status).order_by(SocialPost.status)
        result = query.all()

        fixed_statuses = ["ERRORED", "PROCESSING", "PUBLISHED", "UPLOADING"]
        result_dict = {status: 0 for status in fixed_statuses}
        for row in result:
            if row.status in result_dict:
                result_dict[row.status] = row.count

        return [{"status": s, "count": result_dict[s]} for s in fixed_statuses]
