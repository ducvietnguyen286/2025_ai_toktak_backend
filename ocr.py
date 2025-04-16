from app.lib.logger import logger
from fastapi import FastAPI, Request
from paddleocr import PaddleOCR

app = FastAPI()
ocr = PaddleOCR(use_gpu=True, lang="korean")


@app.post("/check_text")
async def check_text(request: Request):
    try:
        logger.info("Step 1: Received request")
        data = await request.json()
        image_path = data["image_path"]
        logger.info(f"Step 2: Image path: {image_path}")

        logger.info("Step 3: Running OCR")
        result = ocr.ocr(image_path)
        logger.info(f"Step 4: OCR result: {result}")

        text = "".join([item[1] for item in result]).strip()
        logger.info(f"Step 5: Extracted text: {text}")

        return {"text": text}
    except Exception as e:
        logger.error(f"Error during OCR processing: {e}")
        return {"error": str(e)}
