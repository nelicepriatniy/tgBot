from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    channel_id: str = ""
    channel_url: str = ""
    require_subscription: bool = False
    admin_ids: str = ""
    # promo_code: str = "DYHANIE30"  # промокод пока отключён
    promo_code: str = ""

    purchase_url_sleep: str = "https://example.com/sleep"
    purchase_url_longevity: str = "https://example.com/longevity"
    purchase_url_sport: str = "https://example.com/sport"
    database_path: str = "data/bot.db"

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids.strip():
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]

    def purchase_url(self, branch: str) -> str:
        return {
            "sleep": self.purchase_url_sleep,
            "longevity": self.purchase_url_longevity,
            "sport": self.purchase_url_sport,
        }.get(branch, self.purchase_url_sleep)

    @property
    def db_path(self) -> Path:
        path = Path(self.database_path)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
