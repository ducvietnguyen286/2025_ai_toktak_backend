import io
import os
import traceback
from google.cloud import vision
# from shapely import unary_union
# from shapely.geometry import Polygon
from PIL import Image, ImageEnhance

from app.lib.logger import logger


class GoogleVision:
    def initialize(self):
        key_path = os.path.join(
            os.getcwd(),
            "app",
            "third_parties",
            "crendentials",
            "google-cloud-vision.json",
        )
        client = vision.ImageAnnotatorClient.from_service_account_file(key_path)
        return client

    def preprocess_image(self, image_path, output_path=None, enhance_factor=1.7):
        image = Image.open(image_path)
        enhancer_brightness = ImageEnhance.Brightness(image)
        image = enhancer_brightness.enhance(enhance_factor)
        enhancer_contrast = ImageEnhance.Contrast(image)
        image = enhancer_contrast.enhance(enhance_factor)

        if output_path:
            image.save(output_path)
        return image

    def detect_objects(self, image_path):
        try:
            client = self.initialize()
            pil_image = self.preprocess_image(image_path)
            img_byte_arr = io.BytesIO()
            if pil_image.mode == "RGBA":
                pil_image = pil_image.convert("RGB")
            pil_image.save(img_byte_arr, format="JPEG")
            content = img_byte_arr.getvalue()

            vision_image = vision.Image(content=content)
            response = client.object_localization(image=vision_image)
            if response.error.message:
                return False, response.error.message
            objects = response.localized_object_annotations

            detected_objects = [
                {
                    "name": obj.name,
                    "confidence": obj.score,
                    "bounding_poly": [
                        (v.x, v.y) for v in obj.bounding_poly.normalized_vertices
                    ],
                }
                for obj in objects
            ]

            return detected_objects
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Error in detect_objects: {e}")
            return []

    def analyze_image(self, image_path, image_width=0, image_height=0):
        client = self.initialize()
        with open(image_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        if response.error.message:
            return False, response.error.message
        texts = response.text_annotations

        label_response = client.label_detection(image=image)
        if label_response.error.message:
            return False, label_response.error.message
        labels = label_response.label_annotations
        length_labels = len(labels)

        full_text = ""
        ratio = 0.0
        polygons = []

        if texts:
            full_text = texts[0].description

            # raw_polygons = [
            #     Polygon([(v.x, v.y) for v in text.bounding_poly.vertices])
            #     for text in texts[1:]
            #     if len(text.bounding_poly.vertices) >= 4
            # ]

            # for poly in raw_polygons:
            #     if not poly.is_valid:
            #         poly = poly.buffer(0)
            #     if poly.area > 0:
            #         polygons.append(poly)

            # if not polygons:
            #     ratio = 0.0
            # else:
            #     image_area = image_width * image_height
            #     merged_polygons = self.merge_close_polygons(
            #         polygons, distance_threshold=15
            #     )
            #     sum_text_area = sum(
            #         poly.area for poly in merged_polygons if not poly.is_empty
            #     )
            #     ratio = sum_text_area / image_area if image_area > 0 else 0.0

        return full_text, ratio, length_labels

    def merge_close_polygons(self, polygons, distance_threshold):
        buffered_polygons = [p.buffer(distance_threshold) for p in polygons]
        # merged = unary_union(buffered_polygons)
        # if merged.geom_type == "Polygon":
        #     return [merged]
        # elif merged.geom_type == "MultiPolygon":
        #     return list(merged.geoms)
        # else:
        #     return []
