import traceback
from app.models.link import Link
from app.models.post import Post
from app.models.social_post import SocialPost
from app.models.social_sync import SocialSync
from app.models.user_link import UserLink


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
                "post_id": social_post.post_id,
                "session_key": social_post.session_key,
                "process_number": social_post.process_number,
                "error_message": social_post.error_message,
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

            posts = Post.query.filter(Post.id.in_(post_ids)).all()

            data = {}
            post_dict = {post.id: post for post in posts}

            for social_post in social_posts:
                post = post_dict.get(social_post.post_id)
                if not post:
                    continue
                post = post._to_json()
                link = link_dict.get(social_post.link_id)

                post_social = {
                    "id": str(social_post.id),
                    "title": link.title,
                    "status": social_post.status,
                    "social_link": social_post.social_link,
                    "link_id": social_post.link_id,
                    "post_id": social_post.post_id,
                    "session_key": social_post.session_key,
                    "process_number": social_post.process_number,
                    "error_message": social_post.error_message,
                }

                if "social_posts" not in post:
                    post["social_posts"] = []
                post["social_posts"].append(post_social)
                data[post.get("id")] = post

            post_data = []
            for key in data:
                post_data.append(data[key])

            social_sync_data = social_sync.to_json()
            social_sync_data["posts"] = post_data
            return social_sync_data
        except Exception as e:
            traceback.print_exc()
            print(e)
            return {}
