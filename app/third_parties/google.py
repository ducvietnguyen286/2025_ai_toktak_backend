import os
from google.cloud import vision
from shapely import unary_union
from shapely.geometry import Polygon


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

    def analyze_image(self, image_path, image_width=0, image_height=0):
        client = self.initialize()
        with open(image_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        if response.error.message:
            return False, response.error.message
        texts = response.text_annotations

        full_text = ""
        ratio = 0.0
        polygons = []

        if texts:
            full_text = texts[0].description

            for text in texts[1:]:
                vertices = text.bounding_poly.vertices
                if len(vertices) < 4:
                    continue

                polygon = Polygon([(v.x, v.y) for v in vertices])
                if not polygon.is_valid:
                    polygon = polygon.buffer(0)

                if polygon.area > 0:
                    polygons.append(polygon)

            if not polygons:
                ratio = 0.0
            else:
                image_area = image_width * image_height
                merged_polygons = self.merge_close_polygons(
                    polygons, distance_threshold=15
                )
                sum_text_area = 0
                for poly in merged_polygons:
                    if poly.is_empty:
                        continue
                    sum_text_area += poly.area

                ratio = sum_text_area / image_area if image_area > 0 else 0.0

        return full_text, ratio

    def merge_close_polygons(self, polygons, distance_threshold):
        buffered_polygons = [p.buffer(distance_threshold) for p in polygons]
        merged = unary_union(buffered_polygons)
        if merged.geom_type == "Polygon":
            return [merged]
        elif merged.geom_type == "MultiPolygon":
            return list(merged.geoms)
        else:
            return []
