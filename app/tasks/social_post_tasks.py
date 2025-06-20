from app.tasks.celery_app import celery_app, make_celery_app
from app.models.social_post import SocialPost
from app.lib.query import select_by_id

app = make_celery_app()


@celery_app.task(bind=True, name="update_social_data")
def update_social_data(self, social_id, **kwargs):
    with app.app_context():
        try:
            post = select_by_id(SocialPost, social_id)
            if post:
                for key, value in kwargs.items():
                    if hasattr(post, key):
                        setattr(post, key, value)
                post.save()
        finally:
            # CRITICAL: Force cleanup database session to prevent connection leaks
            from app.extensions import db

            try:
                if db.session.is_active:
                    db.session.rollback()
                db.session.close()
                db.session.remove()
            except:
                pass
