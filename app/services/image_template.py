from app.models.image_template import ImageTemplate


class ImageTemplateService:

    @staticmethod
    def create_image_template(*args, **kwargs):
        image_template = ImageTemplate(*args, **kwargs)
        image_template.save()
        return image_template

    @staticmethod
    def find_image_template(id):
        return ImageTemplate.objects.get(id=id)

    @staticmethod
    def find_image_template_by_template_code(template_code):
        return ImageTemplate.objects(template_code=template_code).first()

    @staticmethod
    def find_image_template_by_type(type):
        return ImageTemplate.objects(type=type).first()

    @staticmethod
    def get_image_templates():
        image_templates = ImageTemplate.objects(status="ACTIVE").all()
        return [image_template.to_json() for image_template in image_templates]

    @staticmethod
    def get_not_json_image_templates():
        image_templates = ImageTemplate.objects(status="ACTIVE").all()
        return image_templates

    @staticmethod
    def update_image_template(id, *args):
        image_template = ImageTemplate.objects.get(id=id)
        image_template.update(*args)
        return image_template

    @staticmethod
    def delete_image_template(id):
        return ImageTemplate.objects.get(id=id).delete()
