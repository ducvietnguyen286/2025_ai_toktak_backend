# coding: utf8
from flask import Blueprint
from flask_restx import Api

from app.api.maker import ns as maker_ns

bp = Blueprint("api", __name__, url_prefix="/api/v1")

api = Api(bp, version="1.0", title="Flask API", description="Flask API", doc="/docs/")

api.add_namespace(ns=maker_ns)
