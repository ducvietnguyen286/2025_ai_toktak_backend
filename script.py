import datetime
import os
import time
from dotenv import load_dotenv
import logging
from flask import Flask
from werkzeug.exceptions import default_exceptions

from app.models.month_text import MonthText
from app.models.youtube_client import YoutubeClient
from app.services.link import LinkService
from app.services.notification import NotificationServices
from app.services.user import UserService
from sqlalchemy import text

load_dotenv(override=False)

from app.errors.handler import api_error_handler
from app.extensions import redis_client, db
from app.config import configs as config
import json
from app.models.image_template import ImageTemplate


def __config_logging(app):
    print("Start TEST...")


def __init_app(app):
    db.init_app(app)
    redis_client.init_app(app)


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
    import_image_template()
    import_month_text()
    import_youtube_client()


def import_image_template():
    app = create_app()
    with app.app_context():
        print("Start Script...")
        json_path = os.path.join(
            os.path.dirname(__file__), "data_scripts", "toktak.image_templates.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            it = ImageTemplate(
                created_at=datetime.fromisoformat(
                    item["created_at"]["$date"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    item["updated_at"]["$date"].replace("Z", "+00:00")
                ),
                template_name=item.get("template_name"),
                template_code=item.get("template_code"),
                template_image=item.get("template_image"),
                font=item.get("font"),
                font_name=item.get("font_name"),
                font_path=item.get("font_path"),
                font_size=item.get("font_size"),
                main_text_color=item.get("main_text_color"),
                text_color=item.get("text_color"),
                stroke_color=item.get("stroke_color"),
                stroke_width=item.get("stroke_width"),
                text_shadow=item.get("text_shadow"),
                text_align=item.get("text_align"),
                text_position=item.get("text_position"),
                text_position_x=item.get("text_position_x"),
                text_position_y=item.get("text_position_y"),
                background=item.get("background"),
                background_color=item.get("background_color"),
                background_image=item.get("background_image"),
                padding=item.get("padding"),
                margin=item.get("margin"),
                type=item.get("type"),
                created_by=item.get("created_by"),
                sort=item.get("sort"),
                status=item.get("status"),
            )
            db.session.add(it)

        db.session.commit()
        db.session.close()
        print("End Script...")


def import_month_text():
    app = create_app()
    with app.app_context():
        print("Start Script...")
        json_path = os.path.join(
            os.path.dirname(__file__), "data_scripts", "toktak.month_texts.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            it = MonthText(
                created_at=datetime.fromisoformat(
                    item["created_at"]["$date"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    item["updated_at"]["$date"].replace("Z", "+00:00")
                ),
                keyword=item.get("keyword"),
                hashtag=item.get("hashtag"),
                month=item.get("month"),
                status=item.get("status"),
            )
            db.session.add(it)

        db.session.commit()
        db.session.close()
        print("End Script...")


def import_youtube_client():
    app = create_app()
    with app.app_context():
        print("Start Script...")
        json_path = os.path.join(
            os.path.dirname(__file__), "data_scripts", "toktak.youtube_clients.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            it = YoutubeClient(
                created_at=datetime.fromisoformat(
                    item["created_at"]["$date"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    item["updated_at"]["$date"].replace("Z", "+00:00")
                ),
                user_ids=json.dumps(item.get("user_ids", [])),
                member_count=item.get("member_count"),
                project_name=item.get("project_name"),
                client_id=item.get("client_id"),
                client_secret=item.get("client_secret"),
            )
            db.session.add(it)

        db.session.commit()
        db.session.close()
        print("End Script...")


def logout_x():
    app = create_app()
    with app.app_context():
        print("Start Script...")
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
        print("End Script...")


if __name__ == "__main__":
    main()
