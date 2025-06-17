from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Product(db.Model, BaseModel):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups_product.id"), nullable=True, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_name = db.Column(db.String(500), nullable=False, default="")
    product_url = db.Column(db.String(500), nullable=False, default="")
    product_image = db.Column(db.String(500), nullable=False, default="")
    price = db.Column(db.String(500), nullable=False, default="")
    shorten_link = db.Column(db.String(500), nullable=False, default="")
    content = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, default="")
    order_no = db.Column(db.Integer, default=0)
    
    product_url_hash = db.Column(db.String(255), index=True, nullable=False)

    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)  # Ngày tạo
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now
    )  #

    user = db.relationship("User", lazy="joined")
    group = db.relationship("GroupProduct", lazy="joined")

    to_json_parse = "content"
    # to_json_filter = "captions"

    def to_dict(self):
        return {
            "group_id": self.group_id,
            "group_name": self.group.name if self.group else None,
            "id": self.id,
            "user_id": self.user_id,
            "product_name": self.product_name,
            "product_url": self.product_url,
            "product_image": self.product_image,
            "shorten_link": self.shorten_link,
            "price": self.price,
            "content": self.content,
            "description": self.description,
            "status": self.status,
            "order_no": self.order_no,
            "product_url_hash": self.product_url_hash,
            "user_email": self.user.email if self.user else None,
            "created_at": (
                self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                if self.updated_at
                else None
            ),
        }
