import traceback
from app.lib.logger import logger
from app.models.link import Link
from app.models.post import Post
from app.models.social_post import SocialPost
from app.models.social_sync import SocialSync
from app.models.user_link import UserLink
from datetime import datetime, timedelta
from bson import ObjectId


class SocialPostService:

    @staticmethod
    def create_social_post(*args, **kwargs):
        social_post = SocialPost(*args, **kwargs)
        social_post.save()
        return social_post

    @staticmethod
    def find_social_post(id):
        return SocialPost.objects.get(id=id)

    def get_all_by_post_ids(post_ids):
        social_posts = SocialPost.objects(post_id__in=post_ids)
        return social_posts

    @staticmethod
    def by_post_id_get_latest_social_posts(post_id):
        social_post = (
            SocialPost.objects(post_id=post_id).order_by("-created_at").first()
        )
        if not social_post:
            return []
        session_key = social_post.session_key
        results = SocialPost.objects(session_key=session_key)

        link_ids = [result.link_id for result in results]
        links = Link.query.filter(Link.id.in_(link_ids)).all()
        link_dict = {link.id: link for link in links}

        data = []
        for social_post in results:
            link = link_dict.get(social_post.link_id)
            post_data = {
                "id": str(social_post.id),
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
    def update_social_post(id, **args):
        social_post = SocialPost.objects.get(id=id)
        social_post.update(**args)
        return social_post

    @staticmethod
    def update_multple_social_post_by__ids(ids, **args):
        converted_ids = [ObjectId(id) for id in ids]
        social_post = SocialPost.objects(id__in=converted_ids)
        social_post.update(**args)
        return social_post

    @staticmethod
    def delete_social_post(id):
        return SocialPost.objects.get(id=id).delete()

    @staticmethod
    def create_social_sync(*args, **kwargs):
        social_sync = SocialSync(*args, **kwargs)
        social_sync.save()
        return social_sync

    @staticmethod
    def find_social_sync(id):
        return SocialSync.objects.get(id=id)

    @staticmethod
    def update_social_sync(id, *args):
        social_sync = SocialSync.query.get(id)
        social_sync.update(*args)
        return social_sync

    @staticmethod
    def delete_social_sync(id):
        return SocialSync.query.get(id).delete()

    @staticmethod
    def get_social_syncs():
        return SocialSync.objects.all()

    @staticmethod
    def get_status_social_sycns__by_id(id):
        try:
            social_sync = SocialSync.objects.get(id=id)
            if not social_sync:
                return {}
            social_posts = SocialPost.objects(sync_id=str(id))

            post_ids = social_sync.post_ids

            user_links = UserLink.query.filter(
                UserLink.user_id == social_sync.user_id
            ).all()
            link_ids = [user_link.link_id for user_link in user_links]

            links = Link.query.filter(Link.id.in_(link_ids)).all()
            link_dict = {link.id: link for link in links}

            post_ids = [ObjectId(post_id) for post_id in post_ids]

            posts = Post.objects(id__in=post_ids)

            data = {}
            post_dict = {str(post.id): post for post in posts}

            logger.info(f"post_dict: {post_dict}")
            logger.info(f"data: {data}")

            for social_post in social_posts:
                social_post_id = str(social_post.post_id)
                logger.info(f"social_post.post_id: {social_post_id}")
                post = data.get(social_post_id)
                if not post:
                    post = post_dict.get(social_post_id)
                    if not post:
                        continue
                    post = post.to_json()

                logger.info(f"post: {post}")
                link = link_dict.get(social_post.link_id)

                post_social = {
                    "id": str(social_post.id),
                    "title": link.title,
                    "status": social_post.status,
                    "social_link": social_post.social_link,
                    "link_id": social_post.link_id,
                    "link_type": link.type,
                    "post_id": str(social_post.post_id),
                    "session_key": social_post.session_key,
                    "process_number": social_post.process_number,
                    "error_message": social_post.error_message,
                }

                if "social_posts" not in post:
                    post["social_posts"] = []
                post["social_posts"].append(post_social)
                data[str(social_post.post_id)] = post

            logger.info(f"data: {data}")

            post_data = []
            for key in data:
                post_data.append(data[key])

            social_sync_data = social_sync.to_json()
            social_sync_data["posts"] = post_data
            return social_sync_data
        except Exception as e:
            traceback.print_exc()
            logger.error(f"get_status_social_sycns__by_id: {e}")
            print(e)
            return {}

    @staticmethod
    def getTotalRunning(filters=None):
        filters = filters or {}
        match_stage = {}

        # Xử lý khoảng thời gian
        from_date_str = filters.get("from_date")
        to_date_str = filters.get("to_date")

        if from_date_str or to_date_str:
            created_at_filter = {}
            try:
                if from_date_str:
                    from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
                    created_at_filter["$gte"] = from_date
                if to_date_str:
                    # Thêm 1 ngày để lấy hết to_date trong ngày đó
                    to_date = datetime.strptime(to_date_str, "%Y-%m-%d") + timedelta(
                        days=1
                    )
                    created_at_filter["$lt"] = to_date
            except ValueError:
                raise ValueError(
                    "from_date hoặc to_date không đúng định dạng YYYY-MM-DD"
                )

            match_stage["created_at"] = created_at_filter

        # Xử lý các filter khác ngoài ngày
        for key, value in filters.items():
            if key in ("from_date", "to_date"):
                continue
            # match_stage[key] = value

        # Build pipeline
        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})

        pipeline.append({"$group": {"_id": "$status", "count": {"$sum": 1}}})

        pipeline.append({"$sort": {"_id": 1}})

        result = SocialPost._get_collection().aggregate(pipeline)
        fixed_statuses = ["ERRORED", "PROCESSING", "PUBLISHED", "UPLOADING"]

        # Tạo dict tạm để tra cứu
        result_dict = {item["_id"]: item["count"] for item in result}

        # Đảm bảo kết quả luôn có đủ 4 loại
        formatted_result = [
            {"status": status, "count": result_dict.get(status, 0)}
            for status in fixed_statuses
        ]

        return formatted_result
