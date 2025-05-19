from app.extensions import celery
from app.services.notification import NotificationServices


@celery.task(name="tasks.send_notification")
def send_notification(
    payload: dict,
):
    """
    payload = {
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
    NotificationServices.create_notification(**payload)
