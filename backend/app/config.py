from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    AZURE_AD_CLIENT_ID: str
    AZURE_AD_TENANT_ID: str
    AZURE_AD_CLIENT_SECRET: str # Keep this secret!
    API_V1_STR: str = "/api/v1"

    model_config = SettingsConfigDict(env_file="../.env") # Points to backend/.env

settings = Settings()
