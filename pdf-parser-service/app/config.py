import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # MySQL配置
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pdf_reader")

    # 服务配置
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 100 * 1024 * 1024))  # 100MB

    # OCR配置
    OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
    OCR_USE_GPU = os.getenv("OCR_USE_GPU", "false").lower() == "true"
    OCR_LANG = os.getenv("OCR_LANG", "ch")
    OCR_TEXT_THRESHOLD = int(os.getenv("OCR_TEXT_THRESHOLD", 100))

    @property
    def DATABASE_URL(self):
        # URL encode password to handle special characters
        encoded_password = quote_plus(self.MYSQL_PASSWORD)
        return f"mysql+pymysql://{self.MYSQL_USER}:{encoded_password}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

settings = Settings()
