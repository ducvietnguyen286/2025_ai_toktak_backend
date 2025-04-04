from app.extensions import db
from app.models.base import BaseModel


class Payment(db.Model, BaseModel):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Integer, default=1)
