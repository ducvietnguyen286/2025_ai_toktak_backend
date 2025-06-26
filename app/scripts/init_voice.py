#!/usr/bin/env python3
"""
Script to initialize voice data in the database
Run this script to create default voices from Google and Typecast
"""

import sys
import os

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path, override=True)

# Add project root to path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from app import create_app
from app.config import DevelopmentConfig
from app.extensions import db
from app.services.voice import VoiceService
from app.services.shotstack_services import get_typecast_voices
from app.enums.voices import Voices
import const


def create_voices_table():
    """Create voices table if it doesn't exist"""
    try:
        # Create all tables
        db.create_all()
        print("✅ Voices table created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False


def init_google_voices():
    """Initialize Google voices from SETUP_VOICES"""
    try:
        print("🎤 Initializing Google voices...")
        success_count = 0
        update_count = 0

        for voice in const.SETUP_VOICES:
            existing_voice = VoiceService.find_one_voice_by_filter(
                string_id=voice["id"], type=Voices.GOOGLE.value
            )

            if not existing_voice:
                VoiceService.create_voice(
                    string_id=voice["id"],
                    name=voice["name"],
                    name_en=voice["name_en"],
                    gender=voice["gender"],
                    audio_url=voice["audio_url"],
                    type=Voices.GOOGLE.value,
                )
                success_count += 1
            else:
                update_count += 1

        print(f"✅ Created {success_count} new Google voices")
        print(f"ℹ️ {update_count} Google voices already exist")
        return True

    except Exception as e:
        print(f"❌ Error initializing Google voices: {e}")
        return False


def init_typecast_voices():
    """Initialize voices from Typecast API"""
    try:
        print("🎙️ Initializing Typecast voices...")
        typecast_voices = get_typecast_voices(no_cache=True)
        success_count = 0
        update_count = 0

        for voice in typecast_voices:
            # Xác định giới tính
            sex = voice.get("sex", [])
            if "여성" in sex:  # Nữ
                gender = Voices.FEMALE.value
            else:  # Nam hoặc mặc định
                gender = Voices.MALE.value

            # Lấy thông tin style và model version
            style_label_v2 = voice.get("style_label_v2", [])
            style_data = {}
            model_version = "latest"

            for style_label in style_label_v2:
                display_name = style_label.get("display_name", "")
                if display_name == "SSFM-V2.1":
                    model_version = style_label.get("name", "latest")
                    style_data = style_label.get("data", {})

            if not style_data and style_label_v2:
                latest_style_label = style_label_v2[-1]
                style_data = latest_style_label.get("data", {})

            # Xác định emotion_tone_preset
            emotion_tone_preset = ""
            if style_data:
                if "normal" in style_data:
                    normal = style_data.get("normal", "")
                    emotion_tone_preset = normal[0] if normal else ""

            existing_voice = VoiceService.find_one_voice_by_filter(
                string_id=voice["actor_id"], type=Voices.TYPECAST.value
            )

            voice_data = {
                "string_id": voice["actor_id"],
                "name": (
                    voice["name"]["ko"]
                    if voice["name"].get("ko")
                    else voice["name"].get("en", "")
                ),
                "name_en": (
                    voice["name"]["en"]
                    if voice["name"].get("en")
                    else voice["name"].get("ko", "")
                ),
                "gender": gender,
                "audio_url": voice.get("audio_url", ""),
                "type": Voices.TYPECAST.value,
                "volumn": 100,
                "speed_x": 0.7,
                "tempo": 1.5,
                "emotion_tone_preset": emotion_tone_preset,
                "model_version": model_version,
                "xapi_audio_format": "mp3",
                "xapi_hd": True,
            }

            if existing_voice:
                VoiceService.update_voice(existing_voice.id, **voice_data)
                update_count += 1
            else:
                VoiceService.create_voice(**voice_data)
                success_count += 1

        print(f"✅ Created {success_count} new Typecast voices")
        print(f"🔄 Updated {update_count} existing Typecast voices")
        return True

    except Exception as e:
        print(f"❌ Error initializing Typecast voices: {e}")
        return False


def show_voice_usage_example():
    """Show how to use voices in the application"""
    print("\n📖 Voice Usage Example:")
    print("=" * 50)

    example_code = """
# Example: Using Voice Service

from app.services.voice import VoiceService
from app.services.shotstack_services import text_to_speech_kr, get_korean_typecast_voice

# Get all voices
voices = VoiceService.get_voices()

# Get voice by ID
voice = VoiceService.find_voice(voice_id)

# Get voice by filter
voice = VoiceService.find_one_voice_by_filter(
    string_id="voice_string_id",
    type="typecast"  # or "google"
)

# Text to speech with Typecast voice
korean_voice = get_korean_typecast_voice(voice_id)
if korean_voice:
    mp3_file, audio_duration = text_to_speech_kr(
        korean_voice=korean_voice,
        text="텍스트를 음성으로 변환",
        disk_path="output/path",
        config={
            "volumn": 100,
            "speed_x": 0.7,
            "tempo": 1.5
        }
    )
"""

    print(example_code)


def main():
    """Main initialization function"""
    print("🎤 Voice Data Initialization")
    print("=" * 50)

    # Create Flask app context
    app = create_app(DevelopmentConfig)

    with app.app_context():
        # Step 1: Create table
        if not create_voices_table():
            return False

        # Step 2: Initialize Google voices
        if not init_google_voices():
            return False

        # Step 3: Initialize Typecast voices
        if not init_typecast_voices():
            return False

        # Step 4: Show usage example
        show_voice_usage_example()

        print("\n🎉 Voice initialization completed successfully!")
        print("\n💡 Next steps:")
        print("  1. Use VoiceService to access voice data")
        print("  2. Configure voice settings in admin interface")
        print("  3. Use text_to_speech_kr for Typecast voices")
        print("  4. Monitor voice usage and performance")

        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
