"""
wi_fips.py
==========
Static mapping of Wisconsin county names → 5-digit FIPS codes (state 55).

Used by all pipeline scripts as a shared reference. Update here if agency
names in source documents don't match standard county names.
"""

import re

# Standard county name → FIPS (state 55 + county code)
WI_COUNTY_FIPS: dict[str, str] = {
    "adams":        "55001",
    "ashland":      "55003",
    "barron":       "55005",
    "bayfield":     "55007",
    "brown":        "55009",
    "buffalo":      "55011",
    "burnett":      "55013",
    "calumet":      "55015",
    "chippewa":     "55017",
    "clark":        "55019",
    "columbia":     "55021",
    "crawford":     "55023",
    "dane":         "55025",
    "dodge":        "55027",
    "door":         "55029",
    "douglas":      "55031",
    "dunn":         "55033",
    "eau claire":   "55035",
    "florence":     "55037",
    "fond du lac":  "55039",
    "forest":       "55041",
    "grant":        "55043",
    "green":        "55045",
    "green lake":   "55047",
    "iowa":         "55049",
    "iron":         "55051",
    "jackson":      "55053",
    "jefferson":    "55055",
    "juneau":       "55057",
    "kenosha":      "55059",
    "kewaunee":     "55061",
    "la crosse":    "55063",
    "lafayette":    "55065",
    "langlade":     "55067",
    "lincoln":      "55069",
    "manitowoc":    "55071",
    "marathon":     "55073",
    "marinette":    "55075",
    "marquette":    "55077",
    "menominee":    "55078",
    "milwaukee":    "55079",
    "monroe":       "55081",
    "oconto":       "55083",
    "oneida":       "55085",
    "outagamie":    "55087",
    "ozaukee":      "55089",
    "pepin":        "55091",
    "pierce":       "55093",
    "polk":         "55095",
    "portage":      "55097",
    "price":        "55099",
    "racine":       "55101",
    "richland":     "55103",
    "rock":         "55105",
    "rusk":         "55107",
    "st. croix":    "55109",
    "saint croix":  "55109",
    "st croix":     "55109",
    "sauk":         "55111",
    "sawyer":       "55113",
    "shawano":      "55115",
    "sheboygan":    "55117",
    "taylor":       "55119",
    "trempealeau":  "55121",
    "vernon":       "55123",
    "vilas":        "55125",
    "walworth":     "55127",
    "washburn":     "55129",
    "washington":   "55131",
    "waukesha":     "55133",
    "waupaca":      "55135",
    "waushara":     "55137",
    "winnebago":    "55139",
    "wood":         "55141",
}

# Reverse map: FIPS → canonical county name
FIPS_WI_COUNTY: dict[str, str] = {v: k for k, v in WI_COUNTY_FIPS.items()
                                    if k not in ("saint croix", "st croix")}


def normalize_county_name(raw: str) -> str:
    """
    Attempt to extract a canonical county name from a raw agency string.

    Examples
    --------
    "Dane County Sheriff's Office"  → "dane"
    "Milwaukee Co. Jail"            → "milwaukee"
    "St. Croix County"              → "st. croix"
    "La Crosse Co."                 → "la crosse"
    """
    s = raw.lower().strip()
    # Remove common suffixes
    s = re.sub(
        r"\b(county|co\.?|sheriff'?s?\s*(office|dept\.?|department)?|"
        r"jail|department|dept\.?|police|law enforcement)\b",
        "",
        s,
    )
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fips_from_raw(raw: str) -> str | None:
    """
    Return FIPS for a raw agency/county string, or None if not matched.

    Tries exact match first, then substring match.
    """
    norm = normalize_county_name(raw)
    if norm in WI_COUNTY_FIPS:
        return WI_COUNTY_FIPS[norm]
    # Substring fallback (e.g., "fond du lac" inside a longer string)
    for name, fips in WI_COUNTY_FIPS.items():
        if name in norm or norm in name:
            return fips
    return None
