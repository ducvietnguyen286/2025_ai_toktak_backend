from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db


class Voice(db.Model, BaseModel):
    __tablename__ = "voices"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    string_id = db.Column(db.String(255), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False, default="")
    name_en = db.Column(db.String(255), nullable=False, default="")
    name_google = db.Column(db.String(255), default="")
    gender = db.Column(db.String(10), nullable=False, default="male")
    image_url = db.Column(db.String(1024), nullable=False, default="")
    audio_url = db.Column(db.String(1024), nullable=False, default="")
    type = db.Column(db.String(20), nullable=False, default="typecast")
    styles = db.Column(db.Text, default="[]")
    volumn = db.Column(db.Float, nullable=False, default=100)
    speed_x = db.Column(db.Float, nullable=False, default=1)
    tempo = db.Column(db.Float, nullable=False, default=1)
    emotion_tone_preset = db.Column(db.String(255), nullable=False, default="normal-1")
    model_version = db.Column(db.String(255), nullable=False, default="latest")
    xapi_audio_format = db.Column(db.String(255), nullable=False, default="mp3")
    xapi_hd = db.Column(db.Boolean, nullable=False, default=True)
    order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    to_json_parse = ("styles",)

    def to_dict(self):
        return {
            "id": self.string_id,
            "int_id": self.id,
            "name": self.name,
            "name_en": self.name_en,
            "name_google": self.name_google,
            "gender": self.gender,
            "image_url": self.image_url,
            "audio_url": self.audio_url,
            "type": self.type,
            "volumn": self.volumn,
            "speed_x": self.speed_x,
            "tempo": self.tempo,
            "emotion_tone_preset": self.emotion_tone_preset,
            "model_version": self.model_version,
            "xapi_audio_format": self.xapi_audio_format,
            "xapi_hd": self.xapi_hd,
            "order": self.order,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
