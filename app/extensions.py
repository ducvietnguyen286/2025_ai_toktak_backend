# coding: utf8
from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

redis_client = FlaskRedis()
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()