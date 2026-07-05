from app.config import settings


class Verdict:
    PASS = "pass"
    FLAG_PROMPT = "flag_prompt"


async def check_density(redis, serial: str, role: str) -> str:
    if role == "wholesaler":
        return Verdict.PASS

    count = await redis.incr(f"item:{serial}:scan_count")
    if role == "consumer" and count > settings.density_threshold_consumer:
        return Verdict.FLAG_PROMPT

    return Verdict.PASS
