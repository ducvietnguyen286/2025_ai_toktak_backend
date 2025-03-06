# coding: utf8
from flask import Flask
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_mongoengine import MongoEngine


redis_client = FlaskRedis()
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
socketio = SocketIO(async_mode="gevent", cors_allowed_origins="*")
db_mongo = MongoEngine()
