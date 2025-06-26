from app.enums.voices import Voices
from app.models.voice import Voice
from app.lib.query import (
    delete_by_id,
    select_with_filter,
    select_by_id,
    select_with_filter_one,
)


class VoiceService:

    @staticmethod
    def create_voice(*args, **kwargs):
        voice = Voice(*args, **kwargs)
        voice.save()
        return voice

    @staticmethod
    def find_voice(id):
        voice = select_by_id(Voice, id)
        return voice

    @staticmethod
    def find_one_voice_by_filter(**kwargs):
        filters = []
        for key, value in kwargs.items():
            if hasattr(Voice, key):
                filters.append(getattr(Voice, key) == value)
        voice = select_with_filter_one(
            Voice, filters=filters, order_by=[Voice.id.desc()]
        )
        return voice

    @staticmethod
    def get_default_voice():
        return VoiceService.find_one_voice_by_filter(string_id="3")

    @staticmethod
    def get_voices():
        voices = select_with_filter(
            Voice,
            order_by=[Voice.id.desc()],
            filters=[],
        )
        return [voice._to_json() for voice in voices]

    @staticmethod
    def get_frontend_voices():
        voices = select_with_filter(
            Voice,
            order_by=[Voice.order.asc()],
            filters=[],
        )
        return [voice.to_dict() for voice in voices]

    @staticmethod
    def update_voice(id, *args, **kwargs):
        voice = Voice.query.get(id)
        voice.update(**kwargs)
        return voice

    @staticmethod
    def delete_voice(id):
        delete_by_id(Voice, id)
        return True
