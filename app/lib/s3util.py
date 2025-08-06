import mimetypes
import os
import boto3
from botocore.exceptions import NoCredentialsError
from app.lib.logger import logger


class S3Utils:
    @staticmethod
    def upload_local_file_to_s3(local_path, s3_key):
        try:
            if not os.path.exists(local_path):
                logger.warning(f"File not found: {local_path}")
                return ""

            # Tự động xác định content-type
            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = "application/octet-stream"  # fallback chung

            session = boto3.session.Session(
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2"),
            )
            s3 = session.resource("s3")
            bucket = os.getenv("AWS_BUCKET")

            with open(local_path, "rb") as f:
                s3.Bucket(bucket).put_object(
                    Key=s3_key, Body=f, ContentType=content_type
                )

            return f"https://{bucket}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_key}"

        except NoCredentialsError:
            logger.error("❌ S3 credentials not found.")
        except Exception as e:
            logger.error(f"❌ Error uploading to S3: {e}")
        return ""
