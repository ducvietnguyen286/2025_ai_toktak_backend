import av
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os


class MakerVideo:
    def generate_video_moovly(images):
        access_token = os.environ.get("MOOVLY_ACCESS_TOKEN")
        template_id = os.environ.get("MOOVLY_TEMPLATE_ID")
        create_url = "https://api.moovly.com/generator/v1/jobs"
        body = {
            "quality": "1080p",
            "create_render": True,
            "create_project": False,
        }
