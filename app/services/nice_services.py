from app.lib.logger import logger
import subprocess
import os
from app.services.user import UserService
from app.services.referral_service import ReferralService
from app.services.notification import NotificationServices
import re
import base64
from datetime import datetime
import json
import urllib.parse
import traceback

from dateutil.relativedelta import relativedelta
from const import PACKAGE_CONFIG, MAX_REFERRAL_USAGE


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
            reqseq = NiceAuthService.run_command([cb_encode_path, "SEQ", sitecode])

            # Lưu thông tin người dùng nếu có
            user_data = UserService.find_user(user_id)
            if user_data:
                UserService.update_user(user_id, password_certificate=reqseq)

            returnurl = url_verify_result
            errorurl = url_verify_result
            logger.info("---------------------------------------")
            # Tạo plain data
            plaindata = (
                f"7:REQ_SEQ{len(reqseq)}:{reqseq}"
                f"8:SITECODE{len(sitecode)}:{sitecode}"
                f"9:AUTH_TYPE{len(authtype)}:{authtype}"
                f"7:RTN_URL{len(returnurl)}:{returnurl}"
                f"7:ERR_URL{len(errorurl)}:{errorurl}"
                f"9:CUSTOMIZE{len(customize)}:{customize}"
            )
            logger.info(plaindata)

            # Mã hóa dữ liệu

            enc_data = NiceAuthService.run_command(
                [cb_encode_path, "ENC", sitecode, sitepasswd, plaindata]
            )

            # Chỉ xử lý nếu là mã lỗi (-1, -2, -3, -9)
            if enc_data in ["-1", "-2", "-3", "-9"]:
                return_msg, enc_data = NiceAuthService.interpret_error_code(enc_data)

            result_item = {
                "m": "checkplusService",
                "EncodeData": enc_data,
                "endpoint": "https://nice.checkplus.co.kr/CheckPlusSafeModel/checkplus.cb",
            }
            logger.info("---------------------------------------")
            logger.info(result_item)

            return {"code": result_code, "message": return_msg, "data": result_item}

        except subprocess.CalledProcessError as e:
            return_msg = f"Command execution error: {e.output.decode()}"
        except Exception as e:
            return_msg = str(e)

        return {"code": 500, "message": return_msg, "data": result_item}

    @staticmethod
    def checkplus_success(user_id, data_search):
        sitecode = os.environ.get("SITE_CODE", "")
        sitepasswd = os.environ.get("SITE_PASSWORD", "")
        cb_encode_path = os.environ.get("ENCODE_PATH", "")

        result_code = 200
        return_msg = ""
        result_item = {}

        try:
            enc_data = data_search.get("EncodeData", "")
            if re.search(r"[^0-9a-zA-Z+/=]", enc_data):
                return {
                    "code": 404,
                    "message": "입력 값 확인이 필요합니다",
                    "data": {},
                }

            try:
                decoded = base64.b64decode(enc_data)
                if base64.b64encode(decoded).decode() != enc_data:
                    return {
                        "code": 404,
                        "message": "Invalid base64",
                        "data": {"enc_data": enc_data},
                    }
            except Exception:
                return {
                    "code": 404,
                    "message": "입력 값 확인이 필요합니다",
                    "data": {"enc_data": enc_data},
                }

            # Decrypt
            plaindata = NiceAuthService.run_command(
                [cb_encode_path, "DEC", sitecode, sitepasswd, enc_data]
            )

            # Check decrypt result
            if plaindata in ["-1", "-4", "-5", "-6", "-9", "-12"]:
                error_map = {
                    "-1": "암/복호화 시스템 오류",
                    "-4": "복호화 처리 오류",
                    "-5": "HASH값 불일치",
                    "-6": "복호화 데이터 오류",
                    "-9": "입력값 오류",
                    "-12": "사이트 비밀번호 오류",
                }
                return {
                    "code": 500,
                    "message": error_map.get(plaindata, "복호화 실패"),
                    "data": {},
                }

            utf8_name_raw = NiceAuthService.get_value(plaindata, "UTF8_NAME")
            if utf8_name_raw:
                name = urllib.parse.unquote(utf8_name_raw)
            else:
                # fallback EUC-KR 방식
                name_raw = NiceAuthService.get_value(plaindata, "NAME")
                name = name_raw.encode("latin1").decode("euc-kr", errors="ignore")

            logger.info(name)

            result_item = {
                "user_id": user_id,
                "requestnumber": NiceAuthService.get_value(plaindata, "REQ_SEQ"),
                "responsenumber": NiceAuthService.get_value(plaindata, "RES_SEQ"),
                "authtype": NiceAuthService.get_value(plaindata, "AUTH_TYPE"),
                "name": name,
                "birthdate": NiceAuthService.get_value(plaindata, "BIRTHDATE"),
                "gender": NiceAuthService.get_value(plaindata, "GENDER"),
                "nationalinfo": NiceAuthService.get_value(plaindata, "NATIONALINFO"),
                "dupinfo": NiceAuthService.get_value(plaindata, "DI"),
                "conninfo": NiceAuthService.get_value(plaindata, "CI"),
                "mobileno": NiceAuthService.get_value(plaindata, "MOBILE_NO"),
                "mobileco": NiceAuthService.get_value(plaindata, "MOBILE_CO"),
            }

            # Validate user session
            user_data = UserService.find_user(user_id)

            if not user_data:
                logger.warning("Not found User Verify")
                return {
                    "code": 403,
                    "message": "사용자 로그인을 해주세요",
                    "data": result_item,
                }

            if user_data.password_certificate != result_item["requestnumber"]:
                logger.warning(
                    f"Session mismatch: cert={user_data.password_certificate} req={result_item['requestnumber']}"
                )
                return {
                    "code": 403,
                    "message": "세션값이 다릅니다. 올바른 경로로 접근하시기 바랍니다.",
                    "data": result_item,
                }

            mobileno = result_item["mobileno"]
            verify_detail = UserService.check_phone_verify_nice(mobileno)

            if not verify_detail:
                datetime_now = datetime.now()
                data_update = {
                    "phone": mobileno,
                    "auth_nice_result": json.dumps(result_item),
                    "is_auth_nice": 1,
                    "is_verify_email": 1,
                    "name": name,
                    "gender": "M" if result_item["gender"] == "1" else "F",
                }
                UserService.update_user(user_id, **data_update)
                # Tìm theo người được giới thiệu khi xác thực thành công
                referral_history_detail = ReferralService.find_by_referred_user_id(
                    user_id
                )
                # nếu có giới thiệu
                if referral_history_detail:
                    #kiểm tra tối đa số lần
                    referrer_user_id = referral_history_detail.referrer_user_id
                    usage_count = ReferralService.find_by_referred_user_id_done(referrer_user_id)
                    if usage_count >= MAX_REFERRAL_USAGE:
                        return {"code": 200, "message": "인증 성공", "data": result_item}
        
        
                    # người được giới thiệu =  user_id hiện tại
                    referred_user_id = referral_history_detail.referred_user_id
                    # Gia hạn 7 ngày cho người được mời
                    basic_package = PACKAGE_CONFIG["BASIC"]
                    reward_duration = relativedelta(days=7)

                    expire_date = datetime_now + reward_duration
                    referred_update_data = {
                        "subscription_expired": expire_date,
                        "subscription": "BASIC",
                        "batch_total": min(
                            basic_package["batch_total"], user_data.batch_total
                        ),
                        "batch_remain": min(
                            basic_package["batch_remain"], user_data.batch_remain
                        ),
                        "total_link_active": max(
                            basic_package["total_link_active"],
                            user_data.total_link_active,
                        ),
                    }

                    UserService.update_user(referred_user_id, **referred_update_data)

                    message = f"링크 초대로 가입이 완료되었습니다. 계정이 BASIC 요금제로 업그레이드되었으며, 사용 기간은 {datetime_now.strftime('%Y-%m-%d')}부터 {expire_date.strftime('%Y-%m-%d')}까지입니다."
                    NotificationServices.create_notification(
                        user_id=referred_user_id,
                        title=message,
                        notification_type="referral",
                    )

                    # Ghi Log History
                    data_user_history = {
                        "user_id": referred_user_id,
                        "type": "referral",
                        "object_id": referral_history_detail.id,
                        "object_start_time": datetime_now,
                        "object_end_time": expire_date,
                        "title": basic_package["pack_name"],
                        "description": basic_package["pack_description"],
                        "value": basic_package["batch_total"],
                        "num_days": basic_package["batch_remain"],
                    }
                    UserService.create_user_history(**data_user_history)

                    # -------------------------------
                    # 3. Cập nhật cho người giới thiệu
                    # -------------------------------

                    # người giới thiệu
                    referrer_user_id = referral_history_detail.referrer_user_id
                    referrer_user_data = UserService.find_user(referrer_user_id)
                    subscription = referrer_user_data.subscription

                    if subscription in ["FREE", "BASIC"]:
                        if subscription == "BASIC":
                            # Trường hợp người giới thiệu đang dùng gói BASIC
                            # Kiểm tra xem subscription_expired hiện tại còn hiệu lực hay đã hết hạn
                            if referrer_user_data.subscription_expired > datetime_now:
                                # Nếu còn hiệu lực → cộng thêm reward_duration vào thời hạn cũ
                                old_exp = referrer_user_data.subscription_expired
                            else:
                                # Nếu đã hết hạn hoặc không có → bắt đầu từ thời điểm hiện tại
                                old_exp = datetime_now
                            subscription_expired = old_exp + reward_duration
                        else:
                            subscription_expired = datetime_now + reward_duration

                        referrer_update_data = {
                            "subscription_expired": subscription_expired,
                            "subscription": "BASIC",
                            "batch_total": min(
                                basic_package["batch_total"],
                                referrer_user_data.batch_total,
                            ),
                            "batch_remain": min(
                                basic_package["batch_remain"],
                                referrer_user_data.batch_remain,
                            ),
                            "total_link_active": max(
                                basic_package["total_link_active"],
                                referrer_user_data.total_link_active,
                            ),
                        }
                        UserService.update_user(
                            referrer_user_id, **referrer_update_data
                        )

                        message = f"추천이 완료되었습니다. 계정이 BASIC 요금제로 업그레이드되었으며, 사용 기간은 {datetime_now.strftime('%Y-%m-%d')}부터 {expire_date.strftime('%Y-%m-%d')}까지입니다."
                        NotificationServices.create_notification(
                            user_id=referrer_user_id,
                            title=message,
                            notification_type="referral",
                        )

                        data_user_history = {
                            "user_id": referrer_user_id,
                            "type": "referral",
                            "object_id": referral_history_detail.id,
                            "object_start_time": datetime_now,
                            "object_end_time": expire_date,
                            "title": basic_package["pack_name"],
                            "description": basic_package["pack_description"],
                            "value": basic_package["batch_total"],
                            "num_days": basic_package["batch_remain"],
                        }
                        UserService.create_user_history(**data_user_history)

                    referral_history_detail.expired_at = datetime_now + relativedelta(
                        days=7
                    )
                    referral_history_detail.status = "DONE"
                    referral_history_detail.save()

                return {"code": 200, "message": "인증 성공", "data": result_item}
            else:
                return {
                    "code": 403,
                    "message": "⚠️ 이 전화번호는 이미 다른 계정의 인증에 사용되었습니다.",
                    "data": result_item,
                }

        except Exception as e:
            logger.error("===== NiceAuthService checkplus_success Error =====")
            logger.error(f"EncodeData: {enc_data}")
            logger.error(f"Error: {str(e)}")
            logger.error("Traceback:")
            logger.error(traceback.format_exc())  # Ghi log traceback để biết dòng lỗi
            return {"code": 500, "message": str(e), "data": result_item}

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

    @staticmethod
    def run_command(cmd: list) -> str:
        try:
            # 인증결과 암호화 데이터 복호화 처리
            #  plaindata = subprocess.check_output([cb_encode_path, 'DEC', sitecode, sitepasswd, enc_data])
            plaindata = subprocess.run(
                cmd, capture_output=True, encoding="euc-kr"
            ).stdout
        except subprocess.CalledProcessError as e:
            # check_output 함수 이용하는 경우 1 이외의 결과는 에러로 처리됨
            plaindata = e.output.decode("euc-kr")
            logger.error("===== NiceAuthService run_command Error =====")
            logger.error(f"cmd: {cmd}")
            logger.error(f"Error: {e.output}")
            logger.error("Traceback:")
            logger.error(traceback.format_exc())  # Ghi log traceback để biết dòng lỗi
        return plaindata

    @staticmethod
    def get_value(plaindata, key) -> str:
        value = ""
        keyIndex = -1
        valLen = 0

        # 복호화 데이터 분할
        arrData = plaindata.split(":")
        cnt = len(arrData)
        for i in range(cnt):
            item = arrData[i]
            itemKey = re.sub("[\d]+$", "", item)

            # 키값 검색
            if itemKey == key:
                keyIndex = i

                # 데이터 길이값 추출
                valLen = int(item.replace(key, "", 1))

                if key != "NAME":
                    # 실제 데이터 추출
                    value = arrData[keyIndex + 1][:valLen]
                else:
                    # 이름 데이터 추출 (한글 깨짐 대응)
                    value = re.sub("[\d]+$", "", arrData[keyIndex + 1])

                break

        return value
