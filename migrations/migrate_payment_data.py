import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app import create_app  # <-- import create_app từ Flask project của bạn
from app.extensions import db
from app.models.payment import Payment
from app.models.user import User
from app.models.user_history import UserHistory
import const
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from app.lib.logger import logger
from dotenv import load_dotenv

load_dotenv()

# ----------- Kết nối MySQL (dùng cho raw query) ----------
MYSQL_URI = (
    f"{os.getenv('SQLALCHEMY_ENGINE', 'mysql+pymysql')}://"
    f"{os.getenv('SQLALCHEMY_USER', 'root')}:{os.getenv('SQLALCHEMY_PASSWORD', '')}"
    f"@{os.getenv('SQLALCHEMY_HOST', 'localhost')}:{os.getenv('SQLALCHEMY_PORT', '3306')}/"
    f"{os.getenv('SQLALCHEMY_DATABASE', '')}"
)
engine = create_engine(MYSQL_URI)
Session = sessionmaker(bind=engine)
session = Session()


def migrate():
    print("Starting migration...")

    histories = UserHistory.query.filter(
        UserHistory.type == "user",
        UserHistory.type_2 == "NEW_USER",
    ).all()

    package_name = "BASIC"
    origin_price = const.PACKAGE_CONFIG[package_name]["price"]
    migrated = 0
    logger.info(histories)
    for history_detail in histories:
        user_id = history_detail.user_id
        current_user = User.query.get(user_id)
        if not current_user:
            continue
        logger.info(user_id)

        # Check đã có payment tương tự chưa (chống trùng)
        existed = Payment.query.filter_by(
            user_id=user_id,
            package_name=package_name,
            start_date=history_detail.object_start_time,
            end_date=history_detail.object_end_time,
        ).first()
        if existed:
            continue

        data_update = {
            "user_id": user_id,
            "package_name": package_name,
            "order_id": None,
            "amount": origin_price,
            "customer_name": current_user.name or current_user.email,
            "method": "REQUEST",
            "status": "PAID",
            "price": origin_price,
            "requested_at": history_detail.created_at,
            "start_date": history_detail.object_start_time,
            "end_date": history_detail.object_end_time,
            "total_link": const.PACKAGE_CONFIG[package_name]["total_link"],
            "total_create": const.PACKAGE_CONFIG[package_name]["total_create"],
            "description": "MigrateNewUser",
        }

        crawl_data = Payment(**data_update)
        db.session.add(crawl_data)
        migrated += 1

    db.session.commit()
    print(f"Migration completed. Total migrated: {migrated}")


if __name__ == "__main__":
    from app import create_app
    from app.config import configs as config  # noqa

    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = create_app(config_app)
    with app.app_context():
        migrate()
