from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # Default settings
    MONGO_CONNECTION_STRING: str = "mongodb://localhost:27017"
    MONGO_DATABASE_NAME: str = "scheduled_payments"
    TRANSFER_SERVICE_URL: str = "http://IP_SERVICIO:1234/api/v1/transfers"
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "log.txt"
    LOG_BACKUP_COUNT: int = 7
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

settings = Settings()