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
    manufacturer: str = ""
    drug_name: str = ""
    drug_use: str = ""
    expiry: str = ""
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
    chain_intact: bool | None = None
    chain_message: str | None = None


class VerifyRequest(BaseModel):
    batch_id: str
    serial: str
    image_base64: str = ""
    lat: float = 0.0
    lng: float = 0.0
    timestamp: str = ""


class AIConfidence(BaseModel):
    p_genuine: float
    p_counterfeit: float
    model: str
    model_agrees_with_cv: bool | None = None


class VerifyResponse(BaseModel):
    status: str
    confidence: float
    message: str
    metrics: dict | None = None
    overlay_base64: str | None = None
    batch_info: BatchInfo | None = None
    scan_history: ScanHistory | None = None
    ai_confidence: AIConfidence | None = None


class RoutePointInput(BaseModel):
    location_name: str
    lat: float
    lng: float
    event: str


class RegisterBatchRequest(BaseModel):
    batch_id: str
    region: str
    mint_date: str
    manufacturer: str = ""
    drug_name: str = ""
    drug_use: str = ""
    expiry: str = ""
    route: list[RoutePointInput] = []


class RegisterBatchResponse(BaseModel):
    batch_id: str
    inserted: bool
    message: str


class ListBatchesResponse(BaseModel):
    batches: list[BatchInfo]
    total: int


class ExplainRequest(BaseModel):
    verify_response: dict
    user_message: str = ""
    conversation: list[dict] = []


class ExplainResponse(BaseModel):
    reply: str
    suggestions: list[str]
