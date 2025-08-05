from app.models.setting import Setting
from datetime import datetime, timedelta
from app.extensions import db, redis_client
import json
import const


class SettingService:
    @staticmethod
    def get_settings():
        cache_data = redis_client.get(const.REDIS_KEY_ALL_SETTINGS)
        if cache_data:
            return json.loads(cache_data)
        # Nếu chưa có cache thì query DB
        settings = Setting.query.all()
        settings_dict = {
            setting.setting_name: setting.setting_value for setting in settings
        }

        # Lưu cache vào Redis
        redis_client.setex(
            const.REDIS_KEY_ALL_SETTINGS, 3600, json.dumps(settings_dict)
        )
        return settings_dict
    
    @staticmethod
    def clear_settings_cache():
        redis_client.delete(const.REDIS_KEY_ALL_SETTINGS)