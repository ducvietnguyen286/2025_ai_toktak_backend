from app.models.post import Post
from app.tasks.celery_app import celery_app, make_celery_app
from app.models.social_post import SocialPost
from app.lib.query import select_by_id, update_by_id

app = make_celery_app()


@celery_app.task(bind=True, name="update_social_data")
def update_social_data(self, social_id, **kwargs):
    with app.app_context():
        post = select_by_id(SocialPost, social_id)
        if post:
            update_by_id(Post, post.id, kwargs)
