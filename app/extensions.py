# coding: utf8
import os
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_mongoengine import MongoEngine
from ultralytics import FastSAM


redis_client = FlaskRedis()
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
socketio = SocketIO(async_mode="gevent", cors_allowed_origins="*")
db_mongo = MongoEngine()
sam_model = None


def init_sam_model(app):
    global sam_model

    model_path = os.path.join(os.getcwd(), "app/ais/models")
    fast_sam_path = os.path.join(model_path, "FastSAM-s.pt")
    # yolo_path = os.path.join(model_path, "yolov8s-seg.pt")

    with app.app_context():
        if sam_model is None:
            sam_model = FastSAM(fast_sam_path)
    return sam_model
