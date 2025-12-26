from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # Mongo
    MONGO_CONNECTION_STRING: str
    MONGO_DATABASE_NAME: str = "scheduled_payments"

    # External services
    TRANSFER_SERVICE_URL: str

    # Scheduler
    SCHEDULER_INTERVAL_SECONDS: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "log.txt"
    LOG_BACKUP_COUNT: int = 7
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # NTP
    NTP_SERVER: str = "pool.ntp.org"
    NTP_REFRESH_SECONDS: int = 60
    NTP_TIMEOUT_SECONDS: int = 3

settings = Settings()