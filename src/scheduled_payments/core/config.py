from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # Mongo
    MONGO_CONNECTION_STRING: str
    MONGO_DATABASE_NAME: str = "scheduled_payments"

    # External services
    TRANSFER_SERVICE_URL: str
    ACCOUNTS_SERVICE_URL: str

    # Subscription limit
    SUBSCRIPTION_BASIC: int
    SUBSCRIPTION_STUDENT: int
    SUBSCRIPTION_PRO: int

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

    # Rate limit
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_DEFAULT_PER_WINDOW: int = 120
    RATE_LIMIT_CREATE_PER_WINDOW: int = 5
    RATE_LIMIT_LIST_PER_WINDOW: int = 60
    RATE_LIMIT_UPCOMING_PER_WINDOW: int = 30
    RATE_LIMIT_DELETE_PER_WINDOW: int = 20

settings = Settings()