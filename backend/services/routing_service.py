"""Geocoding (Nominatim) + route geometry (OSRM). OSRM provides geometry only - never risk."""
import requests

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "SafeRouteAI-hackathon-demo/1.0"}
# San Diego County viewbox: left, top, right, bottom
VIEWBOX = "-117.60,33.51,-116.08,32.53"


class RoutingError(Exception):
    def __init__(self, msg, status=502):
        super().__init__(msg)
        self.status = status


def geocode(query: str) -> dict:
    try:
        r = requests.get(NOMINATIM, params={"q": query, "format": "json", "limit": 1, "viewbox": VIEWBOX,
                                            "bounded": 1, "countrycodes": "us"}, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        raise RoutingError(f"Geocoding service unavailable: {e}")
    if not data:
        raise RoutingError(f"Could not find '{query}' in the San Diego area.", 404)
    d = data[0]
    return {"query": query, "lat": float(d["lat"]), "lng": float(d["lon"]), "display_name": d["display_name"]}


def get_routes(start: dict, end: dict) -> list:
    coords = f"{start['lng']},{start['lat']};{end['lng']},{end['lat']}"
    try:
        r = requests.get(f"{OSRM_URL}/{coords}", params={"alternatives": "true", "overview": "full",
                         "geometries": "geojson", "steps": "true"}, headers=HEADERS, timeout=20)
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        raise RoutingError(f"OSRM routing service unavailable: {e}")
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RoutingError(f"No route found between the two locations ({data.get('code', 'unknown')}).", 404)
    out = []
    for rt in data["routes"]:
        steps = [s for leg in rt["legs"] for s in leg["steps"]]
        out.append({"distance_m": rt["distance"], "duration_s": rt["duration"],
                    "path": [[c[1], c[0]] for c in rt["geometry"]["coordinates"]],
                    "steps": [{"name": s.get("name") or s.get("ref") or "", "geometry": s["geometry"]} for s in steps]})
    return out
