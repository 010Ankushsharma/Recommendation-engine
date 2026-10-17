import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Recommendation Engine"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    DATABASE_URL: str = "postgresql://recengine:recengine_password@postgres:5432/recommendation_db"
    REDIS_URL: str = "redis://redis:6379"
    CACHE_TTL: int = 300
    
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    QDRANT_URL: str = "http://qdrant:6333"
    EMBEDDING_DIMENSION: int = 512
    
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    
    FEAST_OFFLINE_STORE: str = "parquet"
    FEAST_ONLINE_STORE: str = "redis"
    
    RATE_LIMIT_REQUESTS: int = 1000
    RATE_LIMIT_WINDOW: int = 60
    
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

def get_settings():
    return Settings()

settings = get_settings()
