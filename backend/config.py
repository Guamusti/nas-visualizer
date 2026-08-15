from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    nas_host: str = "192.168.1.100"
    nas_port: int = 5005
    nas_use_https: bool = False
    nas_username: str = "admin"
    nas_password: str = ""
    nas_photos_path: str = "/Photos"

    thumbnail_cache_dir: str = "./thumbnail_cache"
    database_url: str = "sqlite+aiosqlite:///./nas_photos.db"

    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def nas_webdav_url(self) -> str:
        scheme = "https" if self.nas_use_https else "http"
        return f"{scheme}://{self.nas_host}:{self.nas_port}"

    @property
    def thumbnail_path(self) -> Path:
        p = Path(self.thumbnail_cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
