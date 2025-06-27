# coding: utf8
import datetime
import json
import os
import traceback
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from app.decorators import admin_required, parameters, required_admin
from app.enums.voices import Voices
from app.lib.response import Response
from app.services.shotstack_services import (
    ShotStackService,
    get_korean_typecast_voice,
    get_typecast_voices,
    text_to_speech_kr,
)
from app.services.voice import VoiceService
from app.extensions import redis_client

ns = Namespace(name="voice", description="Voice API")


@ns.route("/get-voices")
class GetVoices(Resource):

    @jwt_required()
    def get(self):
        try:
            voice_cache = redis_client.get("toktak:voices")
            if voice_cache:
                voices = json.loads(voice_cache)
            else:
                voices = VoiceService.get_frontend_voices()
                redis_client.set("toktak:voices", json.dumps(voices))
            return Response(
                message="Lấy danh sách voice thành công",
                data=voices,
                status=200,
            ).to_dict()
        except Exception as e:
            print(e)
            traceback.print_exc()
            return Response(
                message="Lấy danh sách voice thất bại",
                data={},
                status=500,
            ).to_dict()


@ns.route("/get-admin-voices")
class GetVoices(Resource):

    @jwt_required()
    @admin_required()
    def get(self):
        try:
            voices = VoiceService.get_voices()
            return Response(
                message="Lấy danh sách voice thành công",
                data=voices,
                status=200,
            ).to_dict()
        except Exception as e:
            print(e)
            traceback.print_exc()
            return Response(
                message="Lấy danh sách voice thất bại",
                data={},
                status=500,
            ).to_dict()


@ns.route("/update-voices")
class UpdateVoices(Resource):

    @jwt_required()
    @admin_required()
    @parameters(
        type="object",
        properties={
            "voice_id": {"type": "number"},
            "tempo": {"type": "number"},
            "speed_x": {"type": "number"},
            "volumn": {"type": "number"},
            "emotion_tone_preset": {"type": "string"},
            "model_version": {"type": "string"},
            "xapi_audio_format": {"type": "string"},
            "xapi_hd": {"type": "boolean"},
            "order": {"type": "number"},
        },
        required=["voice_id"],
    )
    def post(self, args):
        try:
            voice_id = args.get("voice_id", 0)
            update_data = {}
            if "tempo" in args:
                update_data["tempo"] = args.get("tempo")
            if "speed_x" in args:
                update_data["speed_x"] = args.get("speed_x")
            if "volumn" in args:
                update_data["volumn"] = args.get("volumn")
            if "emotion_tone_preset" in args:
                update_data["emotion_tone_preset"] = args.get("emotion_tone_preset")
            if "model_version" in args:
                update_data["model_version"] = args.get("model_version")
            if "xapi_audio_format" in args:
                update_data["xapi_audio_format"] = args.get("xapi_audio_format")
            if "xapi_hd" in args:
                update_data["xapi_hd"] = args.get("xapi_hd")
            if "order" in args:
                update_data["order"] = args.get("order")
            if update_data:
                VoiceService.update_voice(voice_id, **update_data)
                redis_client.delete("toktak:voices")

            return Response(
                message="Cập nhật voice thành công",
                data={},
                status=200,
            ).to_dict()
        except Exception as e:
            print(e)
            traceback.print_exc()
            return Response(
                message="Cập nhật voice thất bại",
                data={},
                status=500,
            ).to_dict()


@ns.route("/refresh-voice")
class RefreshVoice(Resource):

    @jwt_required()
    @admin_required()
    def post(self):
        try:
            voices = VoiceService.get_voices()
            current_voice_typecasts = get_typecast_voices(no_cache=True)
            current_voice_typecasts_dict = {
                voice["actor_id"]: voice for voice in current_voice_typecasts
            }

            print(current_voice_typecasts_dict)

            for voice in voices:
                if voice["type"] == "typecast":
                    if voice["string_id"] not in current_voice_typecasts_dict:
                        VoiceService.delete_voice(voice["id"])
                    else:
                        sex = current_voice_typecasts_dict[voice["string_id"]].get(
                            "sex", []
                        )
                        if "여성" in sex:
                            gender = Voices.FEMALE.value
                        else:
                            gender = Voices.MALE.value

                        styles = current_voice_typecasts_dict[voice["string_id"]][
                            "style_label_v2"
                        ]

                        update_data = {
                            "name": current_voice_typecasts_dict[voice["string_id"]][
                                "name"
                            ]["ko"],
                            "name_en": current_voice_typecasts_dict[voice["string_id"]][
                                "name"
                            ]["en"],
                            "gender": gender,
                            "image_url": current_voice_typecasts_dict[
                                voice["string_id"]
                            ]["img_url"],
                            "audio_url": current_voice_typecasts_dict[
                                voice["string_id"]
                            ]["audio_url"],
                            "styles": json.dumps(styles),
                        }

                        VoiceService.update_voice(
                            voice["id"],
                            **update_data,
                        )
                        current_voice_typecasts_dict.pop(voice["string_id"])

            for voice in current_voice_typecasts_dict.values():
                style_label_v2 = voice.get("style_label_v2", [])
                style_data = {}
                model_version = "latest"
                for style_label in style_label_v2:
                    display_name = style_label.get("display_name", "")
                    if display_name == "SSFM-V2.1":
                        model_version = style_label.get("name", "latest")
                        style_data = style_label.get("data", {})

                if not style_data:
                    latest_style_label = style_label_v2[-1]
                    style_data = latest_style_label.get("data", {})

                emotion_tone_preset = ""
                if style_data:
                    if "normal" in style_data:
                        normal = style_data.get("normal", "")
                        emotion_tone_preset = normal[0]
                    else:
                        emotion_tone_preset = ""

                VoiceService.create_voice(
                    string_id=voice["actor_id"],
                    name=voice["name"]["ko"] if voice["name"]["ko"] else "",
                    name_en=voice["name"]["en"] if voice["name"]["en"] else "",
                    gender=voice["gender"],
                    audio_url=voice["audio_url"],
                    image_url=voice["img_url"],
                    styles=json.dumps(style_label_v2),
                    type="typecast",
                    volumn=100,
                    speed_x=1,
                    tempo=1,
                    emotion_tone_preset=emotion_tone_preset,
                    model_version=model_version,
                    xapi_audio_format="mp3",
                    xapi_hd=True,
                )

            redis_client.delete("toktak:voices")

            return Response(
                message="Làm mới voice thành công",
                data={},
                status=200,
            ).to_dict()
        except Exception as e:
            print(e)
            traceback.print_exc()
            return Response(
                message="Làm mới voice thất bại",
                data={},
                status=500,
            ).to_dict()


@ns.route("/test-typecast")
class TestTypecast(Resource):

    @jwt_required()
    @admin_required()
    def post(self):
        from flask import request

        data = request.get_json()
        voice_typecast = data.get("voice_id", "65e96ab52564d1136ecb1d67")
        volumn = data.get("volumn", 100)
        speed_x = data.get("speed_x", 1)
        tempo = data.get("tempo", 1)
        batch_id = data.get("batch_id", 1)  # Get batch_id from request
        text = data.get(
            "text",
            "주방의 청소 도구가 항상 어지럽혀져 있다면, 누구나 한번쯤 고민해보셨을 거예요. 행주와 스폰지, 수세미까지 다양한 물건들이 자주 뒤섞이면서 찾아도 없고, 사용할 때마다 불편함이 커지기 마련입니다. 이런 일들이 자주 반복되면 집중력도 떨어지고, 주방을 사용할 때마다 스트레스를 받게 되죠.\\n이제 그 스트레스를 날려줄 수 있는 솔루션이 있습니다. 스테인레스 스틸로 만들어져 내구성이 뛰어난 주방 청소 도구 스토리지 랙을 사용해보세요. 이 랙은 다용도로 사용이 가능해 스폰지, 행주, 수세미 등 다양한 도구를 깔끔하게 정리해 줍니다. 특히, 구성품이 다공성 바닥으로 되어 있어 물이 쉽게 빠져나가면서 항상 건조한 상태를 유지할 수 있습니다. 이렇게 공간 효율이 높아지면, 주방에서 느끼는 불편함이 훨씬 줄어들겠죠. 매일 사용하는 도구가 정리되어 있으면 주방도 깔끔해져요.\\n이미 많은 분들이 만족하고 계십니다. 제품에 대한 후기가 수백 개 달리며 높은 평점을 기록하고 있어요. 일상생활에서 소소한 변화가 큰 차이를 만들어낼 수 있다는 점에서, 많은 사람들이 인정한 제품입니다.\\n주방에서의 불편함을 해소하고 싶으신 분이라면, 이 제품을 한 번 사용해보세요. 깔끔한 정리가 주는 편안함을 직접 느껴보시길 바랍니다.",
        )

        date_create = datetime.datetime.now().strftime("%Y_%m_%d")
        dir_path = f"static/voice/gtts_voice/{date_create}/{batch_id}"
        config = ShotStackService.get_settings()

        korean_voice = get_korean_typecast_voice(voice_typecast)
        if not korean_voice:
            return {"error": "Voice not found"}, 404

        config["volumn"] = volumn
        config["speed_x"] = speed_x
        config["tempo"] = tempo

        mp3_file, audio_duration, audio_files = text_to_speech_kr(
            korean_voice, text, dir_path, config, get_audios=True
        )

        current_domain = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"

        main_file_url = f"{current_domain}/{mp3_file.replace('static/', '')}"
        audio_files_url = [
            f"{current_domain}/{audio_file.replace('static/', '')}"
            for audio_file in audio_files
        ]

        return {
            "main_file": main_file_url,
            "audio_duration": audio_duration,
            "audio_files": audio_files_url,
        }
