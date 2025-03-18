from app.models.base_mongo import BaseDocument
from mongoengine import StringField, IntField


class ImageTemplate(BaseDocument):
    meta = {
        "collection": "image_templates",
        "indexes": ["template_code", "type"],
    }
    template_name = StringField(default="")
    template_code = StringField(default="", max_length=50)
    font = StringField(default="")
    font_name = StringField(default="")
    font_path = StringField(default="")
    font_size = IntField(default="")
    main_text_color = StringField(default="random_color")
    text_color = StringField(default="random_color")
    stroke_color = StringField(default="0,0,0")
    stroke_width = IntField(default="5")
    text_shadow = StringField(default="")
    text_align = StringField(default="left")
    text_position = StringField(default="center")
    text_position_x = IntField(default=0)
    text_position_y = IntField(default=0)
    background = StringField(default="random_color")
    background_color = StringField(default="")
    background_image = StringField(default="")
    padding = StringField(default="")
    margin = StringField(default="30,30,30,30")
    type = StringField(default="TEMPLATE_IMAGE_1", max_length=50)
    created_by = IntField(default=0)
    status = StringField(required=True, max_length=50, default="ACTIVE")
