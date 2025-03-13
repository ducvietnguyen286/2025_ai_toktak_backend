from app.models.post import Post
from app.models.link import Link
from app.models.social_post import SocialPost
from app.extensions import db
from sqlalchemy import and_, func
from flask import jsonify
from datetime import datetime, timedelta


class PostService:

    @staticmethod
    def create_post(*args, **kwargs):
        post = Post(*args, **kwargs)
        post.save()
        return post

    @staticmethod
    def find_post(id):
        return Post.query.get(id)

    @staticmethod
    def get_posts():
        posts = Post.query.where(Post.status == 1).all()
        return [post._to_json() for post in posts]

    @staticmethod
    def get_posts__by_ids(ids):
        posts = Post.query.where(Post.id.in_(ids)).where(Post.status == 1).all()
        return posts

    def get_posts_by_batch(batch_id):
        posts = Post.query.where(Post.batch_id == batch_id).all()
        return posts

    @staticmethod
    def update_post(id, *args, **kwargs):
        post = Post.query.get(id)
        post.update(**kwargs)
        return post

    @staticmethod
    def delete_post(id):
        return Post.query.get(id).delete()

    @staticmethod
    def get_posts_by_batch_id(batch_id):
        posts = Post.query.where(Post.batch_id == batch_id).all()
        return [post._to_json() for post in posts]

    @staticmethod
    def get_posts__by_batch_id(batch_id):
        posts = Post.query.where(Post.batch_id == batch_id).all()
        return posts

    @staticmethod
    def update_post_by_batch_id(batch_id, *args, **kwargs):
        updated_rows = Post.query.filter_by(batch_id=batch_id).update(
            kwargs
        )  # Cập nhật trực tiếp
        db.session.commit()  # Lưu vào database
        return updated_rows

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
        # Query cơ bản với các điều kiện
        query = Post.query.filter(
            Post.user_id == data_search["user_id"],
            Post.status == data_search["status"],
        )
        
        # NHững thằng bắn lên SNS thì có status_sns = 1
        if data_search["status"] == 1:
            query = query.filter(Post.status_sns == 1)

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
    def delete_posts_by_ids(post_ids):
        try:
            Post.query.filter(Post.id.in_(post_ids)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            return 0
        return 1
