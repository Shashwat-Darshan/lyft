"""Environment configuration management."""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    database_url: str = "sqlite:////data/app.db"
    log_level: str = "INFO"
    webhook_secret: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def validate_webhook_secret(self) -> bool:
        """Check if webhook secret is set and non-empty."""
        return self.webhook_secret is not None and len(self.webhook_secret) > 0


# Global settings instance
settings = Settings()

