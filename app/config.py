from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    APP_ENV: str = "development"
    SECRET_KEY: str
    
    # Add these so Pydantic recognizes them
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    MYSQL_ROOT_PASSWORD: str
    TEST_DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()