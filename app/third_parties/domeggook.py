import requests


class DomeggookService:

    @staticmethod
    def call_ocr(image_path: str):
        try:
            access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJkb21lZ2dvb2siLCJleHAiOjExNzM3Njk1MzQ1fQ.UGuivTw2VD3G7tRhcz4tJSe9deaqtSxnCyXxlDgpsaY"
            url = "https://ocr.domeggook.com/api/v1/ocr/items/[도매꾹상품번호]"
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                data={"isRefresh": "N"},
            )
            return "Extracted text from image"
        except Exception as e:
            return None
