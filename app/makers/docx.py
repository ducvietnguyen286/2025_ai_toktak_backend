import datetime
from io import BytesIO
import os
import re
import time
import uuid
from docx import Document
from docx.shared import Inches ,Pt
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls  # Fix namespace lỗi
import requests

from app.lib.header import generate_desktop_user_agent

date_create = datetime.datetime.now().strftime("%Y_%m_%d")
UPLOAD_FOLDER = os.path.join(os.getcwd(), f"uploads/{date_create}")
CURRENT_DOMAIN = os.environ.get("CURRENT_DOMAIN") or "http://localhost:5000"


class DocxMaker:
    def make(self, title , ads_text , description, images=[], batch_id=0):
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex
        file_name = f"{timestamp}_{unique_id}.docx"

        docx_path = f"{UPLOAD_FOLDER}/{batch_id}/{file_name}"

        doc = Document()
        url_pattern = re.compile(r"https?://\S+")

        doc.add_heading(title, level=1)
        
        if ads_text != "":
            notice_para = doc.add_paragraph()
            notice_run = notice_para.add_run(ads_text)
            notice_run.font.size = Pt(8)  



        user_agent = generate_desktop_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en,vi;q=0.9,es;q=0.8,vi-VN;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
        }

        for item in description:
            if item.startswith("IMAGE_URL_"):
                index = int(item.split("_")[-1])
                if 0 <= index < len(images):
                    image_url = images[index]
                    try:
                        response = requests.get(image_url, headers=headers)
                        if response.status_code == 200:
                            image_stream = BytesIO(response.content)
                            doc.add_picture(
                                image_stream, width=Inches(6.5)
                            )  # Full width
                    except Exception as e:
                        print(f"⚠️ Lỗi tải ảnh: {e}")
            else:
                # paragraph = doc.add_paragraph()
                # last_pos = 0
                # for match in url_pattern.finditer(item):
                #     paragraph.add_run(item[last_pos : match.start()])
                #     # self.add_hyperlink(paragraph, match.group())  # Thêm hyperlink
                #     last_pos = match.end()
                # paragraph.add_run(item[last_pos:])
                doc.add_paragraph(item)

        doc.save(docx_path)

        file_size = os.path.getsize(docx_path)
        mime_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        docx_url = f"{CURRENT_DOMAIN}/files/{date_create}/{batch_id}/{file_name}"
        return {
            "file_size": file_size,
            "mime_type": mime_type,
            "docx_url": docx_url,
        }

    def add_hyperlink(self, paragraph, url, text=None):
        """Chèn hyperlink vào đoạn văn bản"""
        text = text or url  # Nếu không có text, dùng URL làm text

        part = paragraph.part
        r_id = part.relate_to(
            url,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
            is_external=True,
        )

        # XML chuẩn (Loại bỏ nsdecls gây lỗi)
        hyperlink_xml = f"""
        <w:hyperlink r:id="{r_id}" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" 
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
            <w:r>
                <w:rPr>
                    <w:color w:val="0000FF"/>
                    <w:u w:val="single"/>
                </w:rPr>
                <w:t>{text}</w:t>
            </w:r>
        </w:hyperlink>
        """

        # Thêm Hyperlink vào đoạn văn bản
        hyperlink = parse_xml(hyperlink_xml)
        paragraph._element.append(hyperlink)
