from app.tasks.celery_app import celery_app, make_celery_app

app = make_celery_app()

from app.services.notification import NotificationServices


@celery_app.task(bind=True, name="send_notification")
def send_notification(
    self,
    **kwargs,
):
    """
    kwargs = {
      "user_id": …,
      "status": …,
      "title": …,
      "description": …,
      "description_korea": …,
      "hashtag": …,
      "video_url": …,
      "thumbnail": …,
      "captions": …,
      "images": …,
      "notification_type": …,
    }
    """
    with app.app_context():
        try:
            NotificationServices.create_notification(kwargs)
        finally:
            # CRITICAL: Cleanup database session to prevent connection leaks
            from app.extensions import db

            try:
                db.session.remove()
            except:
                pass
