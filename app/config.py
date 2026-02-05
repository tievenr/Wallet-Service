from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    APP_ENV: str = "development"
    SECRET_KEY: str
    
    # API Configuration
    PROJECT_NAME: str = "Wallet Service"
    API_V1_PREFIX: str = "/api/v1"

    # DB Config
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    MYSQL_ROOT_PASSWORD: str
    TEST_DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()