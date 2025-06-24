from app.models.ocr_results import OCRResult
from app.lib.query import (
    delete_by_id,
    select_with_filter,
    select_by_id,
    select_with_filter_one,
)


class OCRResultService:

    @staticmethod
    def create_ocr_result(*args, **kwargs):
        ocr_result = OCRResult(*args, **kwargs)
        ocr_result.save()
        return ocr_result

    @staticmethod
    def find_ocr_result(id):
        ocr_result = select_by_id(OCRResult, id)
        return ocr_result

    @staticmethod
    def find_one_ocr_result_by_filter(**kwargs):
        filters = []
        for key, value in kwargs.items():
            if hasattr(OCRResult, key):
                filters.append(getattr(OCRResult, key) == value)
        ocr_result = select_with_filter_one(
            OCRResult, filters=filters, order_by=[OCRResult.id.desc()]
        )
        return ocr_result

    @staticmethod
    def get_ocr_results():
        ocr_results = select_with_filter(
            OCRResult,
            order_by=[OCRResult.id.desc()],
            filters=[OCRResult.status == 1],
        )
        return [ocr_result._to_json() for ocr_result in ocr_results]

    @staticmethod
    def update_ocr_result(id, *args, **kwargs):
        ocr_result = OCRResult.query.get(id)
        ocr_result.update(**kwargs)
        return ocr_result

    @staticmethod
    def delete_ocr_result(id):
        delete_by_id(OCRResult, id)
        return True
