from pydantic import BaseModel


class RoutePoint(BaseModel):
    location_name: str
    lat: float
    lng: float
    event: str


class BatchInfo(BaseModel):
    batch_id: str
    region: str
    mint_date: str
    route: list[RoutePoint]


class PreviousScan(BaseModel):
    lat: float
    lng: float
    timestamp: str
    result: str


class ScanHistory(BaseModel):
    scan_count: int
    velocity_alert: str | None = None
    density_alert: str | None = None
    gps_alert: str | None = None
    previous_scan: PreviousScan | None = None


class VerifyRequest(BaseModel):
    batch_id: str
    serial: str
    image_base64: str = ""
    lat: float = 0.0
    lng: float = 0.0
    timestamp: str = ""


class VerifyResponse(BaseModel):
    status: str
    confidence: float
    message: str
    metrics: dict | None = None
    overlay_base64: str | None = None
    batch_info: BatchInfo | None = None
    scan_history: ScanHistory | None = None
