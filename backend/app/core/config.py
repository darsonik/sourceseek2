from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Required — server will not start without this
    DATABASE_URL: str

    # Optional until you wire up the vision/embedding features.
    # The relevant endpoints will raise a clear error if called without these set.
    VISION_MODEL_NAME: str | None = None
    VISION_MODEL_API_KEY: str | None = None
    EMBEDDING_MODEL_URL: str | None = None
    EMBEDDING_MODEL_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Create a global settings instance to import from elsewhere
settings = Settings()
