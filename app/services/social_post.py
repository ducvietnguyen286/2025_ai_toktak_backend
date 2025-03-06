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
                "link_id": social_post.link_id,
                "post_id": social_post.post_id,
                "session_key": social_post.session_key,
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
