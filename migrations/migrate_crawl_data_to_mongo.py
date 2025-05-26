import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from mongoengine import connect
from dotenv import load_dotenv

load_dotenv()

# ----------- Kết nối MySQL ----------
MYSQL_URI = (
    f"{os.getenv('SQLALCHEMY_ENGINE', 'mysql+pymysql')}://"
    f"{os.getenv('SQLALCHEMY_USER', 'root')}:{os.getenv('SQLALCHEMY_PASSWORD', '')}"
    f"@{os.getenv('SQLALCHEMY_HOST', 'localhost')}:{os.getenv('SQLALCHEMY_PORT', '3306')}/"
    f"{os.getenv('SQLALCHEMY_DATABASE', '')}"
)

engine = create_engine(MYSQL_URI)
Session = sessionmaker(bind=engine)
session = Session()

# ----------- Kết nối MongoDB ----------
MONGO_DB = os.getenv("MONGODB_DB", "test")
MONGO_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGODB_PORT", 27017))
MONGO_USERNAME = os.getenv("MONGODB_USERNAME", "")
MONGO_PASSWORD = os.getenv("MONGODB_PASSWORD", "")

if MONGO_USERNAME and MONGO_PASSWORD:
    connect(
        db=MONGO_DB,
        host=MONGO_HOST,
        port=MONGO_PORT,
        username=MONGO_USERNAME,
        password=MONGO_PASSWORD,
        authentication_source="admin",
    )
else:
    connect(
        db=MONGO_DB,
        host=MONGO_HOST,
        port=MONGO_PORT,
    )


# ----------- Migrate dữ liệu ----------
def migrate():
    results = session.execute(text("SELECT * FROM crawl_datas"))
    rows = results.fetchall()
    keys = results.keys()

    for row in rows:
        data = dict(zip(keys, row))
        data.pop("id", None)
        # None -> ""
        data = {k: (v if v is not None else "") for k, v in data.items()}
        crawl_url_hash = data.get("crawl_url_hash")

        print(f"Migrated: {crawl_url_hash}")

    print("Migration completed.")


if __name__ == "__main__":
    migrate()
