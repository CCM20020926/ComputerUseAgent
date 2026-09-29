
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model: str = 'gpt-6-luna'