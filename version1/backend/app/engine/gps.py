import json
import os

REGION_POLYGONS: dict[str, list[list[float]]] = {
    "MYANMAR": [[28.5, 92.0], [28.5, 101.0], [10.0, 101.0], [10.0, 92.0]],
    "VIETNAM": [[23.5, 102.0], [23.5, 110.0], [8.5, 110.0], [8.5, 102.0]],
    "THAILAND": [[20.5, 97.0], [20.5, 106.0], [5.5, 106.0], [5.5, 97.0]],
}


class Verdict:
    PASS = "pass"
    FLAG = "flag"


def _load_polygons() -> dict[str, list[list[float]]]:
    path = os.path.join(os.path.dirname(__file__), "..", "..", "seed", "data", "regions.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return REGION_POLYGONS


def _point_in_rect(lat: float, lng: float, rect: list[list[float]]) -> bool:
    min_lat = min(p[0] for p in rect)
    max_lat = max(p[0] for p in rect)
    min_lng = min(p[1] for p in rect)
    max_lng = max(p[1] for p in rect)
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


async def check_gps(batch_id: str, lat: float, lng: float) -> str:
    polygons = _load_polygons()

    batch_to_region = {
        "BATCH-A": "MYANMAR",
        "BATCH-B": "VIETNAM",
        "BATCH-C": "THAILAND",
    }

    region = batch_to_region.get(batch_id)
    if region is None:
        return Verdict.PASS

    rect = polygons.get(region)
    if rect is None:
        return Verdict.PASS

    if _point_in_rect(lat, lng, rect):
        return Verdict.PASS

    return Verdict.FLAG
