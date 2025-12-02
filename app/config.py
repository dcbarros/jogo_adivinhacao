import os
from dotenv import load_dotenv

load_dotenv()

class Configurations:
    APP_NAME: str = "AdvinhaBot"
    DATABASE_URL: str = "sqlite:///./game.db"
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"

config = Configurations()