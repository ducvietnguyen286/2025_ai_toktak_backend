import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from jinja2 import Environment, FileSystemLoader
from app.lib.logger import logger
from app.third_parties.telegram import send_slack_message

import traceback

# === Load config ===
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Toktak")
EMAIL_ENCRYPTION = os.getenv("EMAIL_ENCRYPTION", "tls").lower()

EMAIL_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(EMAIL_TEMPLATE_DIR))


def send_email(to_email: str, subject: str, template_name: str, context: dict = {}):
    try:
        # Load template
        template = jinja_env.get_template(template_name)
        html_content = template.render(**context)

        # Tạo email MIME
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((EMAIL_FROM_NAME, EMAIL_HOST_USER))
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        # Gửi email tùy theo encryption
        if EMAIL_ENCRYPTION == "ssl":
            server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)
        else:  # mặc định là TLS
            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            if EMAIL_ENCRYPTION == "tls":
                server.starttls()

        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.sendmail(EMAIL_HOST_USER, to_email, msg.as_string())
        server.quit()

        logger.info(f"✅ Gửi email đến {to_email} thành công: {subject}")

        # Gửi alert Slack
        alert_msg = (
            f"✅ Email sent\n"
            f"- To: {to_email}\n"
            f"- Subject: {subject}\n"
            f"- VI: Đã gửi email đến khách hàng thành công.\n"
            f"- EN: Email sent to customer successfully.\n"
            f"- KO: 고객에게 이메일이 성공적으로 전송되었습니다."
        )
        send_slack_message(alert_msg)
        return True

    except Exception as ex:

        error_trace = traceback.format_exc()
        logger.error(f"❌ Lỗi khi gửi email đến {to_email}: {ex}\n{error_trace}")

        alert_msg = (
            f"❌ Email FAILED\n"
            f"- To: {to_email}\n"
            f"- Subject: {subject}\n"
            f"- VI: Gửi email thất bại.\n"
            f"- EN: Failed to send email.\n"
            f"- KO: 이메일 전송 실패.\n"
            f"```{error_trace}```"
        )
        send_slack_message(alert_msg)
        return False
