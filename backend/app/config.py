from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    rpc_url: str = "http://localhost:8545"
    contract_address: str = ""
    mock_gps: str | None = None
    velocity_max_kmh: float = 120.0
    density_threshold_consumer: int = 3
    density_threshold_wholesaler: int = 0


settings = Settings()
