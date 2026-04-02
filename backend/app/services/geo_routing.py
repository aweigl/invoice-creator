import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import (
    NOMINATIM_BASE_URL,
    OSRM_BASE_URL,
    OSRM_ROUTE_PROFILE,
    ROUTING_REQUEST_TIMEOUT_SECONDS,
    SENDER_DETAILS,
    SERVICE_AREA_ORIGIN_LATITUDE,
    SERVICE_AREA_ORIGIN_LONGITUDE,
    SERVICE_AREA_RADIUS_KM,
)
from app.schemas import (
    AddressAutocompleteResponse,
    AddressAutocompleteSuggestion,
    AddressDistanceResponse,
    CoordinatePoint,
)


class AddressLookupError(RuntimeError):
    status_code = 502


class AddressNotFoundError(AddressLookupError):
    status_code = 404


AUTOCOMPLETE_LIMIT = 5
AUTOCOMPLETE_VIEWBOX_LATITUDE_DELTA = 0.25
AUTOCOMPLETE_VIEWBOX_LONGITUDE_DELTA = 0.35


def _fetch_json(
    base_url: str,
    path: str,
    *,
    params: dict[str, str | int],
    headers: dict[str, str] | None = None,
) -> object:
    query_string = urlencode(params)
    request = Request(
        f"{base_url.rstrip('/')}{path}?{query_string}",
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "invoice-creator/1.0 "
                f"({SENDER_DETAILS['email']})"
            ),
            **(headers or {}),
        },
    )

    try:
        with urlopen(request, timeout=ROUTING_REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise AddressLookupError(
            f"Der Routing-Dienst hat mit HTTP {exc.code} geantwortet."
        ) from exc
    except URLError as exc:
        raise AddressLookupError(
            "Der Routing-Dienst ist derzeit nicht erreichbar."
        ) from exc
    except json.JSONDecodeError as exc:
        raise AddressLookupError(
            "Der Routing-Dienst hat keine gültige JSON-Antwort geliefert."
        ) from exc


def _build_autocomplete_viewbox() -> str:
    left = SERVICE_AREA_ORIGIN_LONGITUDE - AUTOCOMPLETE_VIEWBOX_LONGITUDE_DELTA
    top = SERVICE_AREA_ORIGIN_LATITUDE + AUTOCOMPLETE_VIEWBOX_LATITUDE_DELTA
    right = SERVICE_AREA_ORIGIN_LONGITUDE + AUTOCOMPLETE_VIEWBOX_LONGITUDE_DELTA
    bottom = SERVICE_AREA_ORIGIN_LATITUDE - AUTOCOMPLETE_VIEWBOX_LATITUDE_DELTA
    return f"{left},{top},{right},{bottom}"


def autocomplete_addresses(query: str) -> AddressAutocompleteResponse:
    normalized_query = query.strip()
    response = _fetch_json(
        NOMINATIM_BASE_URL,
        "/search",
        params={
            "q": normalized_query,
            "format": "jsonv2",
            "limit": AUTOCOMPLETE_LIMIT,
            "addressdetails": 1,
            "countrycodes": "de",
            "viewbox": _build_autocomplete_viewbox(),
            "bounded": 0,
            "email": SENDER_DETAILS["email"],
        },
        headers={"Accept-Language": "de"},
    )

    if not isinstance(response, list):
        raise AddressLookupError(
            "Die Autocomplete-Antwort konnte nicht verarbeitet werden."
        )

    suggestions: list[AddressAutocompleteSuggestion] = []
    for entry in response:
        if not isinstance(entry, dict):
            continue

        display_name = str(entry.get("display_name") or "").strip()
        if not display_name:
            continue

        try:
            latitude = float(entry["lat"])
            longitude = float(entry["lon"])
        except (KeyError, TypeError, ValueError):
            continue

        suggestions.append(
            AddressAutocompleteSuggestion(
                label=display_name,
                value=display_name,
                latitude=latitude,
                longitude=longitude,
            )
        )

    return AddressAutocompleteResponse(
        query=normalized_query,
        suggestions=suggestions[:AUTOCOMPLETE_LIMIT],
    )


def resolve_address_distance(address: str) -> AddressDistanceResponse:
    geocoding_response = _fetch_json(
        NOMINATIM_BASE_URL,
        "/search",
        params={
            "q": address.strip(),
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
            "email": SENDER_DETAILS["email"],
        },
        headers={"Accept-Language": "de"},
    )

    if not isinstance(geocoding_response, list) or not geocoding_response:
        raise AddressNotFoundError(
            "Die Adresse konnte über Nominatim nicht aufgelöst werden."
        )

    first_match = geocoding_response[0]
    if not isinstance(first_match, dict):
        raise AddressLookupError(
            "Die Geocoding-Antwort konnte nicht verarbeitet werden."
        )

    try:
        destination = CoordinatePoint(
            latitude=float(first_match["lat"]),
            longitude=float(first_match["lon"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AddressLookupError(
            "Die Geocoding-Antwort enthielt keine gültigen Koordinaten."
        ) from exc

    origin = CoordinatePoint(
        latitude=SERVICE_AREA_ORIGIN_LATITUDE,
        longitude=SERVICE_AREA_ORIGIN_LONGITUDE,
    )

    route_response = _fetch_json(
        OSRM_BASE_URL,
        (
            f"/route/v1/{OSRM_ROUTE_PROFILE}/"
            f"{origin.longitude},{origin.latitude};"
            f"{destination.longitude},{destination.latitude}"
        ),
        params={"overview": "false"},
    )

    if not isinstance(route_response, dict):
        raise AddressLookupError(
            "Die Routing-Antwort konnte nicht verarbeitet werden."
        )

    routes = route_response.get("routes")
    if route_response.get("code") != "Ok" or not isinstance(routes, list) or not routes:
        raise AddressLookupError(
            "OSRM konnte keine Route für diese Adresse berechnen."
        )

    first_route = routes[0]
    if not isinstance(first_route, dict):
        raise AddressLookupError(
            "Die Routing-Antwort enthielt keine lesbare Route."
        )

    try:
        route_distance_meters = float(first_route["distance"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AddressLookupError(
            "Die Routing-Antwort enthielt keine gültige Distanz."
        ) from exc

    route_distance_km = round(route_distance_meters / 1000, 2)

    return AddressDistanceResponse(
        address=address.strip(),
        resolved_address=str(first_match.get("display_name") or address.strip()),
        origin=origin,
        destination=destination,
        route_distance_meters=route_distance_meters,
        route_distance_km=route_distance_km,
        included_radius_km=SERVICE_AREA_RADIUS_KM,
        should_apply_extended_km_surcharge=route_distance_km > SERVICE_AREA_RADIUS_KM,
    )
