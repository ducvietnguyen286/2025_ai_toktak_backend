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
from app.services.user import UserService

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

    package_name = "BASIC"
    origin_price = const.PACKAGE_CONFIG[package_name]["price"]
    migrated = 0

    users = User.query.filter(
        User.subscription == "FREE",
        User.created_at >= datetime(2025, 5, 22),
    ).all()

    print(f"Total Users Eligible: {len(users)}")

    for user in users:
        subscription_expired = user.created_at + relativedelta(months=1)
        data_update = {
            "subscription": "NEW_USER",
            "subscription_expired": subscription_expired,
            "batch_total": 30,
            "batch_remain": 30,
            "total_link_active": 1,
        }
        UserService.update_user(user.id, **data_update)

        if Payment.query.filter_by(user_id=user.id, package_name=package_name).first():
            continue

        print(f"Migrating User ID: {user.id}")
        try:

            payment = Payment(
                user_id=user.id,
                package_name=package_name,
                order_id=None,
                amount=origin_price,
                customer_name=user.name or user.email,
                method="NEW_USER",
                status="PAID",
                price=origin_price,
                requested_at=user.created_at,
                start_date=user.created_at,
                end_date=subscription_expired,
                total_link=const.PACKAGE_CONFIG[package_name]["total_link"],
                total_create=const.PACKAGE_CONFIG[package_name]["total_create"],
                description="MigrateNewUser",
            )

            history = UserHistory(
                user_id=user.id,
                type="user",
                type_2="NEW_USER",
                object_id=user.id,
                object_start_time=user.created_at,
                object_end_time=subscription_expired,
                title="신규 가입 선물",
                description="신규 가입 선물",
                value=30,
                num_days=30,
            )

            db.session.add(payment)
            db.session.add(history)
            db.session.commit()
            migrated += 1
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to migrate user {user.id}: {e}")

    print(f"Migration done. Total migrated users: {migrated}")


if __name__ == "__main__":
    from app import create_app
    from app.config import configs as config  # noqa

    config_name = os.environ.get("FLASK_CONFIG") or "develop"
    config_app = config[config_name]
    app = create_app(config_app)
    with app.app_context():
        migrate()
