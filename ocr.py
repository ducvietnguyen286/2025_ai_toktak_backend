from fastapi import FastAPI, Request
from paddleocr import PaddleOCR

app = FastAPI()
ocr = PaddleOCR(use_gpu=True, lang="korean")


@app.post("/check_text")
async def check_text(request: Request):
    data = await request.json()
    image_path = data["image_path"]
    result = ocr.ocr(image_path)
    text = "".join([item[1] for item in result]).strip()
    return {"text": text}
