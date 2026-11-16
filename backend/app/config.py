import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATA_DIR: str = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Security & Sessions
    SECRET_KEY: str = os.getenv("SECRET_KEY", "forgetcheck-super-secret-key-change-in-prod-382947192847")
    SESSION_COOKIE_NAME: str = "forgetcheck_session"
    SESSION_MAX_AGE_SECONDS: int = 86400 * 7 # 7 days
    CSRF_COOKIE_NAME: str = "forgetcheck_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    SECURE_COOKIES: bool = os.getenv("SECURE_COOKIES", "false").lower() == "true"

    # Default initial admin credentials
    INITIAL_ADMIN_USERNAME: str = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
    INITIAL_ADMIN_PASSWORD: str = os.getenv("INITIAL_ADMIN_PASSWORD", "Admin@ForgetCheck2026!")

    # Live Gemini AI configuration (optional)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Lab settings
    ENABLE_SYNTHETIC_LAB: bool = True
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024 # 15MB
    MAX_PROBES_PER_RUN: int = 100

    @property
    def database_path(self) -> Path:
        p = Path(self.DATA_DIR) / "forgetcheck.db"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_dir(self) -> Path:
        p = Path(self.DATA_DIR) / "chroma"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def upload_dir(self) -> Path:
        p = Path(self.DATA_DIR) / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def report_dir(self) -> Path:
        p = Path(self.DATA_DIR) / "reports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def model_cache_dir(self) -> Path:
        p = Path(self.DATA_DIR) / "models"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def database_url(self) -> str:
        # Standard SQLite URL with forward slashes
        return f"sqlite:///{self.database_path.as_posix()}"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
