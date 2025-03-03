from sqlalchemy import and_, func
from app.models.link import Link
from app.models.social_post import SocialPost
from app.extensions import db


class SocialPostService:

    @staticmethod
    def create_social_post(*args, **kwargs):
        social_post = SocialPost(*args, **kwargs)
        social_post.save()
        return social_post

    @staticmethod
    def find_social_post(id):
        return SocialPost.query.get(id)

    @staticmethod
    def get_social_posts():
        social_posts = SocialPost.query.where(SocialPost.status == 1).all()
        return [social_post._to_json() for social_post in social_posts]

    def get_all_by_post_ids(post_ids):
        social_posts = SocialPost.query.where(SocialPost.post_id.in_(post_ids)).all()
        return social_posts

    @staticmethod
    def get_latest_social_post_by_post_ids(post_ids):
        subq = (
            db.session.query(
                SocialPost.post_id, func.max(SocialPost.created_at).label("max_created")
            )
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
    def by_post_id_get_latest_social_posts(post_id):
        subq = (
            db.session.query(
                SocialPost.post_id,
                SocialPost.link_id,
                func.max(SocialPost.created_at).label("max_created"),
            )
            .filter(SocialPost.post_id == post_id)
            .group_by(SocialPost.post_id, SocialPost.link_id)
            .subquery()
        )

        query = db.session.query(SocialPost).join(
            subq,
            and_(
                SocialPost.post_id == subq.c.post_id,
                SocialPost.link_id == subq.c.link_id,
                SocialPost.created_at == subq.c.max_created,
            ),
        )
        results = query.all()

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
                "link_id": social_post.link_id,
                "post_id": social_post.post_id,
                "process_number": social_post.process_number,
            }
            data.append(post_data)

        return data

    @staticmethod
    def update_social_post(id, *args):
        social_post = SocialPost.query.get(id)
        social_post.update(*args)
        return social_post

    @staticmethod
    def delete_social_post(id):
        return SocialPost.query.get(id).delete()
