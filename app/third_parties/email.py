import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from jinja2 import Environment, FileSystemLoader
from app.lib.logger import logger
from app.third_parties.telegram import send_slack_message

# === Cấu hình ===
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")  # ví dụ: "noreply@yourdomain.com"
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Toktak")
EMAIL_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

# === Cấu hình Jinja2 ===
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

        # Gửi email
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.sendmail(EMAIL_HOST_USER, to_email, msg.as_string())

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
        logger.error(f"❌ Lỗi khi gửi email đến {to_email}: {ex}")

        # Gửi alert Slack thất bại
        alert_msg = (
            f"❌ Email FAILED\n"
            f"- To: {to_email}\n"
            f"- Subject: {subject}\n"
            f"- VI: Gửi email thất bại.\n"
            f"- EN: Failed to send email.\n"
            f"- KO: 이메일 전송 실패.\n"
            f"- Error: {ex}"
        )
        send_slack_message(alert_msg)
        return False
