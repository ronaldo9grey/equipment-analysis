from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "设备运行数据分析系统"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # 上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list = [".mdb", ".accdb", ".bak", ".sql", ".mysql"]

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/equipment_analysis.db"

    # AI配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 本地AI配置 (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    USE_LOCAL_MODEL: bool = False

    # 文件解析配置
    MDB_DRIVER: str = "{Microsoft Access Driver (*.mdb, *.accdb)}"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)
