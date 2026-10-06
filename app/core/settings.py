from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str
    BCRYPT_ROUNDS: int

    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    DATABASE_URL:str
    PSP_BASE_URL: str
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USERNAME: str
    RABBITMQ_PASSWORD: str

    model_config = SettingsConfigDict( 
        env_file=".env",
        extra="ignore",
    )


settings = Settings()