from app.extensions import db, bcrypt
from app.models.base import BaseModel


class User(db.Model, BaseModel):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=True)
    name = db.Column(db.String(255), nullable=True, default="")
    avatar = db.Column(db.String(500), nullable=True, default="")
    username = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(200), nullable=True)
    status = db.Column(db.Integer, default=1)

    print_filter = ("password",)
    to_json_filter = ("password",)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar": self.avatar,
            "username": self.username,
            "status": self.status,
        }
