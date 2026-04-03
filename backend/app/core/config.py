from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This will automatically pick up DATABASE_URL from your .env file
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

# Create a global settings instance to import from elsewhere
settings = Settings()
