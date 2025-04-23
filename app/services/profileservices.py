from app.models.user import User
from app.models.memberprofile import MemberProfile
from app.models.user_video_templates import UserVideoTemplates
from app.models.link import Link
from app.models.social_post import SocialPost
from app.extensions import db
from sqlalchemy import and_, func, or_
from flask import jsonify
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased
from app.services.image_template import ImageTemplateService
import os
import json
import const


class ProfileServices:

    @staticmethod
    def create_profile(*args, **kwargs):
        profile = MemberProfile(*args, **kwargs)
        profile.save()
        return profile

    @staticmethod
    def profile_by_user_id(user_id):
        return MemberProfile.query.filter_by(user_id=user_id).first()

    @staticmethod
    def find_profile(id):
        return MemberProfile.query.get(id)

    @staticmethod
    def update_profile(id, *args, **kwargs):
        profile = MemberProfile.query.get(id)
        if not profile:
            return None
        profile.update(**kwargs)
        return profile

    @staticmethod
    def find_by_nick_name(nick_name):
        return MemberProfile.query.filter(MemberProfile.nick_name == nick_name).first()

    @staticmethod
    def find_by_nick_name_exclude_user(nick_name, exclude_user_id):
        return MemberProfile.query.filter(
            MemberProfile.nick_name == nick_name,
            MemberProfile.user_id != exclude_user_id,
        ).first()
        
    @staticmethod    
    def update_profile_by_user_id(user_id, *args, **kwargs):
        profile = MemberProfile.query.filter(MemberProfile.user_id == user_id).first()
        if not profile:
            return None
        profile.update(**kwargs)
        return profile
