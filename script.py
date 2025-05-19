import os
import time
from dotenv import load_dotenv
import logging
from flask import Flask
from werkzeug.exceptions import default_exceptions

from app.services.batch import BatchService
from app.services.link import LinkService
from app.services.notification import NotificationServices
from app.services.post import PostService
from app.services.user import UserService
from app.models.shorten import ShortenURL
from sqlalchemy import text

load_dotenv(override=False)

from app.errors.handler import api_error_handler
from app.extensions import redis_client, db, db_mongo
from app.config import configs as config
from threading import Thread


def __config_logging(app):
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Start TEST...")


def __init_app(app):
    db.init_app(app)
    redis_client.init_app(app)
    db_mongo.init_app(app)


def __config_error_handlers(app):
    for exp in default_exceptions:
        app.register_error_handler(exp, api_error_handler)
    app.register_error_handler(Exception, api_error_handler)


def create_app():
    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = Flask(__name__)
    app.config.from_object(config_app)
    __init_app(app)
    __config_logging(app)
    __config_error_handlers(app)
    return app


def main():
    migrate_from_mysql_to_mongo_shotenlink()
    migrate_from_mysql_to_mongo_batch_and_posts()


def migrate_from_mysql_to_mongo_batch_and_posts():
    app = create_app()
    with app.app_context():
        app.logger.info("Start Script...")
        offset = 0
        limit = 200
        while True:
            print("Batch and Posts")
            print("=====================================")
            print(f"offset: {offset}")
            print(f"limit: {limit}")
            mysql_batchs = db.session.execute(
                text("SELECT * FROM batchs LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            ).fetchall()
            if not mysql_batchs:
                break
            for batch in mysql_batchs:
                batch_id = batch.id
                batch_data = {
                    "user_id": batch.user_id,
                    "url": batch.url,
                    "shorten_link": batch.shorten_link,
                    "thumbnail": batch.thumbnail,
                    "thumbnails": batch.thumbnails,
                    "content": batch.content,
                    "type": batch.type,
                    "count_post": batch.count_post,
                    "done_post": batch.done_post,
                    "status": batch.status,
                    "process_status": batch.process_status,
                    "voice_google": batch.voice_google,
                    "is_paid_advertisements": batch.is_paid_advertisements,
                    "template_info": batch.template_info,
                    "created_at": batch.created_at,
                    "updated_at": batch.updated_at,
                }
                new_batch = BatchService.create_batch(**batch_data)
                posts = db.session.execute(
                    text("SELECT * FROM posts WHERE batch_id = :batch_id"),
                    {"batch_id": batch_id},
                ).fetchall()
                for post in posts:
                    post_data = {
                        "user_id": post.user_id,
                        "batch_id": new_batch.id,
                        "thumbnail": post.thumbnail,
                        "captions": post.captions,
                        "images": post.images,
                        "title": post.title,
                        "subtitle": post.subtitle,
                        "content": post.content,
                        "description": post.description,
                        "hashtag": post.hashtag,
                        "video_url": post.video_url,
                        "docx_url": post.docx_url,
                        "file_size": (
                            int(post.file_size)
                            if post.file_size and post.file_size != ""
                            else 0
                        ),
                        "mime_type": post.mime_type,
                        "type": post.type,
                        "status": post.status,
                        "status_sns": post.status_sns,
                        "process_number": post.process_number,
                        "render_id": post.render_id,
                        "video_path": post.video_path,
                    }
                    PostService.create_post(**post_data)
            offset += limit
        app.logger.info("End Script...")


def migrate_from_mysql_to_mongo_shotenlink():
    app = create_app()
    with app.app_context():
        app.logger.info("Start Script...")
        offset = 0
        limit = 200
        while True:
            print("Shorten Links")
            print("=====================================")
            print(f"offset: {offset}")
            print(f"limit: {limit}")
            mysql_shorten_links = db.session.execute(
                text("SELECT * FROM shorten_url LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            ).fetchall()

            if not mysql_shorten_links:
                break

            for link in mysql_shorten_links:
                shorten = ShortenURL(
                    original_url=link.original_url,
                    original_url_hash=link.original_url_hash or "",
                    short_code=link.short_code,
                    status=link.status,
                )
                shorten.save()
            offset += limit

        app.logger.info("End Script...")


def logout_x():
    app = create_app()
    with app.app_context():
        app.logger.info("Start Script...")
        users = UserService.all_users()
        links = LinkService.get_all_links()
        x_link = None
        for link in links:
            if link.get("type") == "X":
                x_link = link
                break
        for user in users:
            user_id = user.get("id")
            x_link_id = x_link.get("id")
            user_link = UserService.find_user_link(user_id=user_id, link_id=x_link_id)
            if user_link:
                UserService.delete_user_link(user_link_id=user_link.id)
                NotificationServices.create_notification(
                    user_id=user.get("id"),
                    title=f"🔒 X 계정의 토큰이 만료됐어요!",
                    description="🔗 계속 사용하시려면 X 계정을 다시 연결해 주세요. 😊",
                    description_korea="🔗 계속 사용하시려면 X 계정을 다시 연결해 주세요. 😊",
                )
        app.logger.info("End Script...")


if __name__ == "__main__":
    main()
