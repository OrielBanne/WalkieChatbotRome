"""Generate nearby place suggestions around the current itinerary route."""

import math
import random
from typing import List, Tuple, Set, Optional
from src.models import PlaceMarker
from src.place_extractor import PlaceExtractor
from src.geocoder import Geocoder, MANUAL_COORDINATES
from src.logging_config import get_logger

logger = get_logger(__name__)

# Canonical display names for gazetteer entries
_CANONICAL_NAMES = {
    "colosseum": "Colosseum", "colosseo": "Colosseum",
    "trevi fountain": "Trevi Fountain", "fontana di trevi": "Trevi Fountain",
    "pantheon": "Pantheon",
    "vatican": "Vatican City", "vatican city": "Vatican City",
    "vatican museums": "Vatican Museums",
    "st peter's basilica": "St Peter's Basilica",
    "st. peter's basilica": "St Peter's Basilica",
    "saint peter's basilica": "St Peter's Basilica",
    "sistine chapel": "Sistine Chapel",
    "spanish steps": "Spanish Steps", "piazza di spagna": "Spanish Steps",
    "roman forum": "Roman Forum", "foro romano": "Roman Forum",
    "palatine hill": "Palatine Hill", "palatino": "Palatine Hill",
    "castel sant'angelo": "Castel Sant'Angelo",
    "castel sant angelo": "Castel Sant'Angelo",
    "piazza navona": "Piazza Navona",
    "villa borghese": "Villa Borghese",
    "borghese gallery": "Borghese Gallery", "galleria borghese": "Borghese Gallery",
    "trastevere": "Trastevere",
    "campo de' fiori": "Campo de' Fiori", "campo de fiori": "Campo de' Fiori",
    "piazza del popolo": "Piazza del Popolo",
    "circus maximus": "Circus Maximus", "circo massimo": "Circus Maximus",
    "capitoline hill": "Capitoline Hill", "campidoglio": "Capitoline Hill",
    "ara pacis": "Ara Pacis",
    "baths of caracalla": "Baths of Caracalla",
    "terme di caracalla": "Baths of Caracalla",
    "appian way": "Appian Way", "via appia antica": "Appian Way",
    "catacombs": "Catacombs",
    "mouth of truth": "Mouth of Truth",
    "bocca della verità": "Mouth of Truth", "bocca della verita": "Mouth of Truth",
    "piazza venezia": "Piazza Venezia",
    "vittoriano": "Vittoriano", "altare della patria": "Vittoriano",
    "janiculum hill": "Janiculum Hill", "gianicolo": "Janiculum Hill",
    "aventine hill": "Aventine Hill", "aventino": "Aventine Hill",
    "testaccio": "Testaccio", "monti": "Monti", "prati": "Prati",
    "santa maria maggiore": "Santa Maria Maggiore",
    "san giovanni in laterano": "San Giovanni in Laterano",
    "santa maria in trastevere": "Santa Maria in Trastevere",
    "santa prassede": "Santa Prassede",
    "san clemente": "San Clemente",
    "santa cecilia": "Santa Cecilia",
    "capitoline museums": "Capitoline Museums", "musei capitolini": "Capitoline Museums",
    "national roman museum": "National Roman Museum",
    "maxxi": "MAXXI Museum",
    "piazza della repubblica": "Piazza della Repubblica",
    "via del corso": "Via del Corso",
    "via veneto": "Via Veneto",
    "via condotti": "Via Condotti",
    "tiber river": "Tiber River", "fiume tevere": "Tiber River",
    "esquiline hill": "Esquiline Hill", "esquilino": "Esquiline Hill",
    "quirinal hill": "Quirinal Hill", "quirinale": "Quirinal Hill",
    "viminal hill": "Viminal Hill", "viminale": "Viminal Hill",
    "caelian hill": "Caelian Hill", "celio": "Caelian Hill",
    "castle of the holy angel": "Castel Sant'Angelo",
}


def _haversine_km(c1: Tuple[float, float], c2: Tuple[float, float]) -> float:
    """Haversine distance in km between two (lat, lon) tuples."""
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def _route_centroid(stops_coords: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Average lat/lon of itinerary stops."""
    if not stops_coords:
        return (41.9028, 12.4964)  # Rome center
    avg_lat = sum(c[0] for c in stops_coords) / len(stops_coords)
    avg_lon = sum(c[1] for c in stops_coords) / len(stops_coords)
    return (avg_lat, avg_lon)


def get_nearby_suggestions(
    itinerary_stop_names: Set[str],
    itinerary_stop_coords: List[Tuple[float, float]],
    visited_places: List[str],
    geocoder: Geocoder,
    vector_store=None,
    count: int = 10,
    max_distance_km: float = 3.0,
) -> List[dict]:
    """Return up to *count* nearby place suggestions not in the itinerary or visited.

    Each returned dict has keys: name, coordinates (lat, lon), place_type.

    The pool is built from:
      1. The PlaceExtractor gazetteer (always available)
      2. Places extracted from a vector-store query (if vector_store provided)

    Places are filtered, sorted by proximity to the route centroid, then a
    random sample of *count* is drawn from the closest ~25 to keep suggestions
    fresh across renders.
    """
    exclude_lower = {n.lower() for n in itinerary_stop_names} | {v.lower() for v in visited_places}
    centroid = _route_centroid(itinerary_stop_coords)

    # --- Build candidate pool ---
    # 1. Gazetteer places (deduplicated via canonical names)
    seen_canonical: Set[str] = set()
    candidates: List[dict] = []

    for raw, canonical in _CANONICAL_NAMES.items():
        if canonical in seen_canonical:
            continue
        if canonical.lower() in exclude_lower:
            continue
        seen_canonical.add(canonical)
        # Try to get coords from manual db first (fast, no API)
        coords_obj = MANUAL_COORDINATES.get(raw)
        if coords_obj:
            coords = (coords_obj.latitude, coords_obj.longitude)
        else:
            coords_obj = geocoder.geocode_place(canonical, bias_location=centroid)
            if not coords_obj:
                continue
            coords = (coords_obj.latitude, coords_obj.longitude)
        candidates.append({"name": canonical, "coordinates": coords, "place_type": "suggestion"})

    # 2. Vector-store enrichment (query for "popular places in Rome near <route>")
    if vector_store is not None:
        try:
            stop_names_str = ", ".join(list(itinerary_stop_names)[:4])
            query = f"popular places to visit in Rome near {stop_names_str}"
            docs = vector_store.similarity_search(query, k=8)
            extractor = PlaceExtractor()
            for doc in docs:
                mentions = extractor.extract_places(doc.page_content)
                for m in mentions:
                    cname = _CANONICAL_NAMES.get(m.name.lower(), m.name.title())
                    if cname.lower() in exclude_lower or cname in seen_canonical:
                        continue
                    seen_canonical.add(cname)
                    coords_obj = MANUAL_COORDINATES.get(m.name.lower())
                    if coords_obj:
                        coords = (coords_obj.latitude, coords_obj.longitude)
                    else:
                        coords_obj = geocoder.geocode_place(cname, bias_location=centroid)
                        if not coords_obj:
                            continue
                        coords = (coords_obj.latitude, coords_obj.longitude)
                    candidates.append({"name": cname, "coordinates": coords, "place_type": "suggestion"})
        except Exception as e:
            logger.warning(f"Vector store suggestion query failed: {e}")

    # --- Filter by distance & sample ---
    for c in candidates:
        c["_dist"] = _haversine_km(centroid, c["coordinates"])
    candidates = [c for c in candidates if c["_dist"] <= max_distance_km]
    candidates.sort(key=lambda c: c["_dist"])

    # Take top ~25 nearest, then randomly pick *count*
    pool = candidates[:25]
    if len(pool) <= count:
        chosen = pool
    else:
        chosen = random.sample(pool, count)

    # Clean up internal key
    for c in chosen:
        c.pop("_dist", None)

    return chosen
