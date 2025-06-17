from app.extensions import db
from app.models.base import BaseModel


class YoutubeClient(db.Model, BaseModel):
    __tablename__ = "youtube_clients"

    id = db.Column(db.Integer, primary_key=True)
    user_ids = db.Column(db.Text, default="")
    member_count = db.Column(db.Integer, default=0)
    project_name = db.Column(db.String(100), default="")
    client_id = db.Column(db.String(150), nullable=False)
    client_secret = db.Column(db.String(150), nullable=False)
    status = db.Column(db.Integer, default=1)
