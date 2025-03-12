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

bp = Blueprint("api", __name__, url_prefix="/api/v1")

api = Api(bp, version="1.0", title="Flask API", description="Flask API", doc="/docs/")

api.add_namespace(ns=ns_post)
api.add_namespace(ns=maker_ns)
api.add_namespace(ns=auth_ns)
api.add_namespace(ns=user_ns)
api.add_namespace(ns=link_ns)
api.add_namespace(ns=video_maker_ns)
api.add_namespace(ns=setting_ns)
