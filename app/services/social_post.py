from app.models.social_post import SocialPost


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

    @staticmethod
    def update_social_post(id, *args):
        social_post = SocialPost.query.get(id)
        social_post.update(*args)
        return social_post

    @staticmethod
    def delete_social_post(id):
        return SocialPost.query.get(id).delete()
