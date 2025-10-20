import os

class Config:
    PROJECT_NAME = "Samsung TV Controller"
    API_V1_STR = "/api/v1"
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
    TOKENS_FILE = os.path.join(BASE_DIR, "tokens.json")
    DEBUG = True  # Set to False in production
    HOST = "0.0.0.0"
    PORT = 8000