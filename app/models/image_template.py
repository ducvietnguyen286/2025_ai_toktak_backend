from app.extensions import db
from app.models.base import BaseModel


class ImageTemplate(db.Model, BaseModel):
    __tablename__ = "image_templates"

    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(255))
    template_code = db.Column(db.String(50))
    template_image = db.Column(db.String(255))
    font = db.Column(db.String(255))
    font_name = db.Column(db.String(255))
    font_path = db.Column(db.String(255))
    font_size = db.Column(db.Integer, default=50)
    main_text_color = db.Column(db.String(255), default="random_color")
    text_color = db.Column(db.String(255), default="#FFFFFF")
    stroke_color = db.Column(db.String(255), default="#000000")
    stroke_width = db.Column(db.Integer, default=5)
    text_shadow = db.Column(db.String(255), default="")
    text_align = db.Column(db.String(255), default="left")
    text_position = db.Column(db.String(255), default="center")
    text_position_x = db.Column(db.Integer, default=0)
    text_position_y = db.Column(db.Integer, default=0)
    background = db.Column(db.String(255), default="random_color")
    background_color = db.Column(db.String(255), default="")
    background_image = db.Column(db.String(255), default="")
    padding = db.Column(db.String(255), default="")
    margin = db.Column(db.String(255), default="30,30,30,30")
    type = db.Column(db.String(50), default="TEMPLATE_IMAGE_1")
    created_by = db.Column(db.Integer, default=0)
    sort = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default="ACTIVE", nullable=False)

    to_json_filter = (
        "font",
        "font_path",
        "font_name",
        "font_size",
        "main_text_color",
        "text_color",
        "stroke_color",
        "stroke_width",
        "text_shadow",
        "text_align",
        "text_position",
        "text_position_x",
        "text_position_y",
        "background",
        "background_color",
        "background_image",
        "padding",
        "margin",
        "created_by",
        "status",
    )
