from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    mongo_uri:str
    mongo_db_name:str
    
    session_expire_minutes: int = 60

    class Config:
        env_file =".env"

settings =Settings()