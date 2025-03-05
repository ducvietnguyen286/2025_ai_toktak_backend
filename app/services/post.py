from app.models.post import Post
from app.models.link import Link
from app.models.social_post import SocialPost
from app.extensions import db
from sqlalchemy import and_, func
from flask import jsonify


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
        print(batch_id)
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
