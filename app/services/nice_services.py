from app.lib.logger import logger
import subprocess
import os
from app.services.user import UserService


class NiceAuthService:

    @staticmethod
    def get_nice_auth(user_id):
        sitecode = os.environ.get("SITE_CODE") or ""
        sitepasswd = os.environ.get("SITE_PASSWORD") or ""
        cb_encode_path = os.environ.get("ENCODE_PATH") or ""
        url_verify_result = os.environ.get("URL_FE_VERIFY") or ""

        result_code = 200
        return_msg = ""
        result_item = {}

        if not all([sitecode, sitepasswd, cb_encode_path, url_verify_result]):
            return {
                "code": 400,
                "message": "Thiếu biến môi trường cấu hình.",
                "data": {},
            }

        try:
            authtype = "M"
            customize = ""

            # Gọi shell command để lấy reqseq
            result = subprocess.run(
                [cb_encode_path, "SEQ", sitecode],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # gộp stderr vào stdout
                text=True,
            )

            reqseq = result.stdout.strip()  # Lấy toàn bộ kết quả trả ra

            # Lưu thông tin người dùng nếu có
            user_data = UserService.find_user(user_id)
            if user_data:
                UserService.update_user(user_id, {"password_certificate": reqseq})

            returnurl = url_verify_result
            errorurl = url_verify_result

            # Tạo plain data
            plaindata = (
                f"7:REQ_SEQ{len(reqseq)}:{reqseq}"
                f"8:SITECODE{len(sitecode)}:{sitecode}"
                f"9:AUTH_TYPE{len(authtype)}:{authtype}"
                f"7:RTN_URL{len(returnurl)}:{returnurl}"
                f"7:ERR_URL{len(errorurl)}:{errorurl}"
                f"9:CUSTOMIZE{len(customize)}:{customize}"
            )

            # Mã hóa dữ liệu

            result_2 = subprocess.run(
                [cb_encode_path, "ENC", sitecode, sitepasswd, plaindata],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # gộp stderr vào stdout
                text=True,
            )

            enc_data = result_2.stdout.strip()  # Lấy toàn bộ kết quả trả ra

            logger.info(enc_data)

            # Chỉ xử lý nếu là mã lỗi (-1, -2, -3, -9)
            if enc_data in ["-1", "-2", "-3", "-9"]:
                return_msg, enc_data = NiceAuthService.interpret_error_code(enc_data)

            result_item = {
                "m": "checkplusService",
                "EncodeData": enc_data,
                "endpoint": "https://nice.checkplus.co.kr/CheckPlusSafeModel/checkplus.cb",
            }

            return {"code": result_code, "message": return_msg, "data": result_item}

        except subprocess.CalledProcessError as e:
            return_msg = f"Command execution error: {e.output.decode()}"
        except Exception as e:
            return_msg = str(e)

        return {"code": 500, "message": return_msg, "data": result_item}

    @staticmethod
    def interpret_error_code(enc_data):
        error_messages = {
            "-1": "암/복호화 시스템 오류입니다.",
            "-2": "암호화 처리 오류입니다.",
            "-3": "암호화 데이터 오류 입니다.",
            "-9": "입력값 오류 입니다.",
        }
        return error_messages.get(enc_data, ""), (
            "" if enc_data in error_messages else enc_data
        )
