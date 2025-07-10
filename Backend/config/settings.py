from dotenv import load_dotenv
import sys
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    app_name: str = "AI Document Analyzer"
    debug: bool = True

    class Config:
        env_file = ".env"


try:
    settings = Settings()

except Exception as e:
    print(f"Error loading settings: {e}")
    print("Check the .env file for required variables")
    sys.exit(1)
