from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
GOLD_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOLD_", env_file=BACKEND_DIR / ".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000

    db_path: Path = GOLD_DIR / "data" / "gold.db"

    # Nguồn dữ liệu chính. Đổi qua env: GOLD_PROVIDER=mock để chạy offline.
    provider: str = "vangtoday"
    provider_timeout: float = 12.0

    # vang.today cập nhật ~30 phút/lần; poll nhanh hơn để bắt nhịp sớm (XAUUSD spot đổi liên tục).
    poll_interval: float = 30.0
    # Tỷ giá free giới hạn lượt gọi -> cache, chỉ làm mới theo chu kỳ này.
    fx_interval: float = 1800.0
    # Tin tức RSS làm mới theo chu kỳ này.
    news_interval: float = 900.0
    # Giữ lịch sử giá trong DB (ngày).
    history_days: int = 30

    # Frontend build output được FastAPI mount làm static.
    static_dir: Path = GOLD_DIR / "frontend" / "dist"

    # Ngưỡng cảnh báo mặc định (% thay đổi trong ngày).
    alert_threshold_pct: float = 1.0

    @property
    def ensure_dirs(self) -> Path:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return self.db_path


settings = Settings()
