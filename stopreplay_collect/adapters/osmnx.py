"""Resolve a sourced city and country to a public OpenStreetMap object."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from threading import Lock
from typing import Callable, Mapping

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftSource, ResearchRequest

_SETTINGS_LOCK = Lock()
_ATTRIBUTION = "© OpenStreetMap contributors (https://www.openstreetmap.org/copyright)"


def _city_and_country(claim: str) -> tuple[str, str] | None:
    prefix, _, value = claim.partition(":")
    if prefix != "based_in":
        return None
    city, comma, country = (part.strip() for part in value.partition(","))
    if comma and all(
        any(ch.isalpha() for ch in field) and all(ch.isalpha() or ch in " .’'-" for ch in field)
        for field in (city, country)
    ):
        return city, country
    return None


def _lookup_city(city: str, country: str) -> Mapping[str, object]:
    import osmnx as ox

    overrides = {
        "http_user_agent": "STOPReplay-Collection/1.0",
        "cache_folder": Path(".cache") / "stopreplay-osmnx",
        "use_cache": True,
        "requests_timeout": 15,
    }
    endpoint = os.environ.get("STOPREPLAY_NOMINATIM_URL")
    if endpoint:
        overrides["nominatim_url"] = endpoint

    # OSMnx settings are process-wide. Serialize this connector's calls and
    # restore the caller's settings when the single, rate-limited request ends.
    with _SETTINGS_LOCK:
        previous = {key: getattr(ox.settings, key) for key in overrides}
        try:
            for key, value in overrides.items():
                setattr(ox.settings, key, value)
            results = ox.geocoder.geocode_to_gdf({"city": city, "country": country}, which_result=1)
        finally:
            for key, value in previous.items():
                setattr(ox.settings, key, value)
    return results.iloc[0].to_dict()


class OSMnxAdapter(CollectionAdapter):
    name = "osmnx"

    def __init__(self, *, lookup: Callable[[str, str], Mapping[str, object]] = _lookup_city) -> None:
        self._lookup = lookup

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        output = CollectionOutput()
        place = _city_and_country(request.params.get("based_in", ""))
        if place is None:
            output.retrieval_failures.append({"error": "select a sourced public based_in: City, Country fact"})
            return output

        try:
            entry = self._lookup(*place)
        except ModuleNotFoundError:
            output.retrieval_failures.append({"error": "install the OSMnx dependency: osmnx==2.2.0"})
            return output
        except (OSError, ValueError) as exc:
            output.retrieval_failures.append({"error": f"Nominatim lookup failed: {type(exc).__name__}"})
            return output

        osm_type = entry.get("osm_type")
        osm_id = str(entry.get("osm_id"))
        label = entry.get("display_name")
        if (entry.get("addresstype") not in {"city", "town", "municipality"}
                or osm_type not in {"node", "way", "relation"} or not osm_id.isdecimal()
                or not isinstance(label, str) or not label.strip()):
            output.extraction_failures.append({"error": "Nominatim did not return a citable municipality"})
            return output

        output.sources.append(DraftSource(
            source_ref=f"osm:{osm_type}:{osm_id}", origin="public_web",
            url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}", publisher="OpenStreetMap contributors",
            locator=f"{osm_type} {osm_id}", excerpt=f"{label.strip()}\n\n{_ATTRIBUTION}",
            retrieved_on=date.today(),
        ))
        return output
