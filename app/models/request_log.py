from app.extensions import db
from app.models.base import BaseModel


class RequestLog(db.Model, BaseModel):
    __tablename__ = "request_logs"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, index=True, nullable=False)
    ai_type = db.Column(db.String(10), nullable=False, index=True)
    request = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    prompt_tokens = db.Column(db.Integer, nullable=False, default=0)
    prompt_cache_tokens = db.Column(db.Integer, nullable=False, default=0)
    prompt_audio_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_reasoning_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_audio_tokens = db.Column(db.Integer, nullable=False, default=0)
    completion_accepted_prediction_tokens = db.Column(
        db.Integer, nullable=False, default=0
    )
    completion_rejected_prediction_tokens = db.Column(
        db.Integer, nullable=False, default=0
    )
    total_tokens = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "ai_type": self.ai_type,
            "request": self.request,
            "response": self.response,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
