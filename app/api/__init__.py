# coding: utf8
from flask import Blueprint
from flask_restx import Api

from app.api.post import ns_post
from app.api.maker import ns as maker_ns
from app.api.auth import ns as auth_ns
from app.api.user import ns as user_ns
from app.api.link import ns as link_ns
from app.api.video_maker import ns as video_maker_ns
from app.api.setting import ns as setting_ns
from app.api.month_text import ns as month_text_ns
from app.api.image_template import ns as image_template_ns
from .shorten import ns as shorten_ns  # Thêm module shorten
from app.api.shorten import ns as shorten_ns
from app.api.notification import ns as notification_ns
from app.api.coupon import ns as coupon_ns
from app.api.admin import ns as admin_ns
from app.api.youtube_client import ns as youtube_client_ns
from app.api.profile import ns as profile_ns
from app.api.product import ns as product_ns
from app.api.schedule import ns as schedule_ns
from app.api.payment import ns as payment_ns

bp = Blueprint("api", __name__, url_prefix="/api/v1")

api = Api(bp, version="1.0", title="Flask API", description="Flask API", doc="/docs/")


api.add_namespace(ns=ns_post)
api.add_namespace(ns=maker_ns)
api.add_namespace(ns=auth_ns)
api.add_namespace(ns=user_ns)
api.add_namespace(ns=link_ns)
api.add_namespace(ns=video_maker_ns)
api.add_namespace(ns=setting_ns)
api.add_namespace(ns=month_text_ns)
api.add_namespace(ns=shorten_ns)
api.add_namespace(ns=image_template_ns)
api.add_namespace(ns=notification_ns)
api.add_namespace(ns=coupon_ns)
api.add_namespace(ns=admin_ns)
api.add_namespace(ns=youtube_client_ns)
api.add_namespace(ns=profile_ns)
api.add_namespace(ns=product_ns)
api.add_namespace(ns=schedule_ns)
api.add_namespace(ns=payment_ns)
