from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Wallet Service"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Singleton instance
settings = Settings()