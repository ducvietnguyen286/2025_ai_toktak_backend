import av
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os


class MakerVideo:
    def __init__(self):
        # Cấu hình
        self.video_size = (1080, 1920)  # (width, height)
        self.duration_per_image = 5  # giây
        self.fps = 25
        self.total_frames = self.duration_per_image * self.fps
        pass

    def make_video(images=[], captions=[], audio=None):
        pass

    def make_image(image_url, text, font_size, font_color, background_color):
        pass

    def make_video_from_images(images):
        UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
        pass
