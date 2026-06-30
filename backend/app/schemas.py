from pydantic import BaseModel


class ScanRequest(BaseModel):
    serial: str
    batch_id: str
    lat: float
    lng: float
    timestamp: str
    role: str = "consumer"
    crypto_image: str | None = None


class ScanResponse(BaseModel):
    status: str
    confidence: float
    message: str
    cached: bool = False
    last_verified: str | None = None
