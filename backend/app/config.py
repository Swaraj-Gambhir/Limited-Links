from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    AZURE_AD_CLIENT_ID: str
    AZURE_AD_TENANT_ID: str
    AZURE_AD_CLIENT_SECRET: str
    API_V1_STR: str = "/api/v1"

    SHAREPOINT_HOSTNAME: str
    SHAREPOINT_SITE_NAME: str
    SHAREPOINT_DOCLIB_NAME: str = "Shared Documents"
    SHAREPOINT_SITE_ID: str
    # For temporary view links
    VIEW_TOKEN_SECRET_KEY: str = "a_very_secret_key_for_view_tokens" # Should be strong and from .env
    VIEW_TOKEN_EXPIRE_MINUTES: int = 15
            
    model_config = SettingsConfigDict(env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

settings = Settings()
