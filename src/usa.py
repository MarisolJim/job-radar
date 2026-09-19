"""Best-effort detection of whether a posting's location is in the USA.

Location strings are wildly inconsistent across ATS boards, so this returns a
three-way answer:
    True  -> clearly US
    False -> clearly NOT US
    None  -> unknown / ambiguous (e.g. a bare "Remote", or empty)

The filter decides what to do with None (default: keep, so we never drop a US
remote role just because the country wasn't spelled out).

Matching is word-boundary based, so "india" does NOT match "Indiana" and "uk"
does not match "Paducah".
"""

from __future__ import annotations

import re

STATE_CODES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", "il",
    "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", "mo", "mt",
    "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri",
    "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy", "dc",
}

STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho", "illinois",
    "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland",
    "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana",
    "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah",
    "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming",
}

# Positive US signals (whole-word / phrase).
US_SIGNALS = [
    "united states", "usa", "u.s.a", "u.s.", "u. s.", "us remote", "remote us",
    "americas",
]

# Major US cities that often appear WITHOUT a state (so they'd otherwise be
# ambiguous). Lets strict mode still keep obvious US roles.
US_CITIES = {
    "san francisco", "new york", "new york city", "nyc", "seattle", "boston",
    "los angeles", "san jose", "san mateo", "palo alto", "mountain view",
    "sunnyvale", "cupertino", "menlo park", "chicago", "austin", "denver",
    "atlanta", "dallas", "houston", "san diego", "portland", "philadelphia",
    "washington dc", "washington, d.c.", "bay area", "silicon valley", "redmond",
    "bellevue", "pittsburgh", "miami", "phoenix", "minneapolis", "detroit",
    "nashville", "raleigh", "durham", "salt lake city", "irvine", "santa monica",
    "santa clara", "brooklyn", "cambridge, ma", "arlington", "reston",
}

# Clear non-US signals: countries, regions, and unambiguous foreign cities.
# NOTE: "georgia" and "jordan" are intentionally omitted (they collide with US
# places); country Georgia/Jordan postings are rare and not worth the false drops.
NON_US = [
    # regions
    "emea", "apac", "latam", "anz", "europe", "european", "asia", "aspac",
    "middle east", "north africa", "sub-saharan",
    # North America (non-US) + common cities
    "canada", "canadian", "ontario", "quebec", "british columbia", "alberta",
    "manitoba", "saskatchewan", "nova scotia", "toronto", "vancouver", "montreal",
    "ottawa", "calgary", "waterloo", "mexico", "guadalajara", "monterrey",
    # UK / Ireland
    "united kingdom", "uk", "u.k.", "england", "scotland", "wales",
    "northern ireland", "london", "manchester", "edinburgh", "cambridge, uk",
    "ireland", "dublin", "belfast",
    # Europe
    "germany", "berlin", "munich", "hamburg", "france", "paris", "lyon", "spain",
    "madrid", "barcelona", "netherlands", "amsterdam", "belgium", "brussels",
    "poland", "warsaw", "krakow", "portugal", "lisbon", "porto", "italy", "milan",
    "rome", "switzerland", "zurich", "geneva", "sweden", "stockholm", "norway",
    "oslo", "denmark", "copenhagen", "finland", "helsinki", "austria", "vienna",
    "czech", "czechia", "prague", "hungary", "budapest", "romania", "bucharest",
    "bulgaria", "greece", "athens", "croatia", "serbia", "ukraine", "estonia",
    "latvia", "lithuania", "slovakia", "slovenia", "iceland", "luxembourg",
    "malta", "cyprus",
    # Asia
    "india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi",
    "gurgaon", "gurugram", "chennai", "noida", "china", "beijing", "shanghai",
    "shenzhen", "hong kong", "japan", "tokyo", "singapore", "south korea",
    "korea", "seoul", "taiwan", "taipei", "philippines", "manila", "indonesia",
    "jakarta", "vietnam", "hanoi", "thailand", "bangkok", "malaysia",
    "kuala lumpur", "pakistan", "bangladesh", "sri lanka", "nepal", "kazakhstan",
    # Middle East
    "israel", "tel aviv", "uae", "united arab emirates", "dubai", "abu dhabi",
    "saudi", "qatar", "doha", "bahrain", "kuwait", "turkey", "turkiye", "istanbul",
    # Oceania
    "australia", "sydney", "melbourne", "brisbane", "perth", "canberra",
    "new zealand", "auckland", "wellington",
    # Africa
    "south africa", "johannesburg", "cape town", "kenya", "nairobi", "nigeria",
    "lagos", "ghana", "accra", "morocco", "egypt", "cairo", "tunisia", "rwanda",
    "uganda", "ethiopia", "tanzania",
    # Latin America
    "brazil", "brasil", "sao paulo", "são paulo", "rio de janeiro", "argentina",
    "buenos aires", "chile", "santiago", "colombia", "bogota", "bogotá", "peru",
    "lima", "uruguay", "montevideo", "costa rica", "panama", "ecuador",
    "guatemala", "dominican republic",
]


def _has_word(text: str, phrase: str) -> bool:
    """Whole-word / phrase match with boundaries, e.g. 'uk' not in 'paducah'."""
    return re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text) is not None


def is_usa(location: str | None) -> bool | None:
    if not location or not location.strip():
        return None
    s = location.lower()

    # Clear non-US wins first (e.g. "Toronto, Ontario, Canada").
    if any(_has_word(s, kw) for kw in NON_US):
        return False

    # Explicit US text.
    if any(_has_word(s, sig) for sig in US_SIGNALS):
        return True
    # Standalone "US" token.
    tokens = set(re.split(r"[\s,/|()\-.;]+", s))
    if "us" in tokens:
        return True
    if STATE_CODES & tokens:
        return True
    if any(name in s for name in STATE_NAMES):
        return True
    if any(_has_word(s, city) for city in US_CITIES):
        return True

    # Bare "remote" with no country -> ambiguous.
    return None
