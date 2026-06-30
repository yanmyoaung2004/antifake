import base64
import io
import secrets

import qrcode
import qrcode.image.pil
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

router = APIRouter()

API_KEYS: set[str] = set()


def require_api_key(x_api_key: str = Header(None)):
    if x_api_key is None or x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="invalid api key")
    return x_api_key


class BatchCreateRequest(BaseModel):
    batch_id: str
    serials: list[str]
    region: str


class BatchCreateResponse(BaseModel):
    batch_id: str
    count: int
    region: str
    layer1_qr: str
    layer2_pattern: str


@router.post("/api/v1/enterprise/keys", status_code=201)
def create_api_key():
    key = f"af_{secrets.token_hex(16)}"
    API_KEYS.add(key)
    return {"api_key": key}


@router.post("/api/v1/enterprise/batch", response_model=BatchCreateResponse)
def create_batch(body: BatchCreateRequest, _=Depends(require_api_key)):
    qr = qrcode.QRCode()
    qr.add_data(f"{body.batch_id}|{body.serials[0] if body.serials else ''}")
    qr_img = qr.make_image(image_factory=qrcode.image.pil.PilImage)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    layer1_qr = base64.b64encode(buf.getvalue()).decode()

    import numpy as np
    from PIL import Image
    noise = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    noise_img = Image.fromarray(noise)
    noise_buf = io.BytesIO()
    noise_img.save(noise_buf, format="PNG")
    layer2_pattern = base64.b64encode(noise_buf.getvalue()).decode()

    return BatchCreateResponse(
        batch_id=body.batch_id,
        count=len(body.serials),
        region=body.region,
        layer1_qr=layer1_qr,
        layer2_pattern=layer2_pattern,
    )
