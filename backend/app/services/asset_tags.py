"""
Single source of truth for industrial asset tag recognition.

WHY THIS MODULE EXISTS
----------------------
Six separate modules each carried their own copy of the asset-tag regex, and they
had drifted apart. Retrieval matched `[A-Z]+-\\d+` (which treated document
references like ERN-2024 as equipment), the dashboard matched a fixed prefix
list, and the graph writer matched a third, shorter list. An asset could
therefore be recognised by one component and invisible to another.

Everything that recognises equipment now imports from here.

TAGGING CONVENTIONS SUPPORTED
-----------------------------
Two families, because real plants use both:

  Descriptive  PUMP-101, VALVE-1010, PSV-1201
               Common in maintenance systems and smaller sites.

  ISA / process  P-101A, E-1501, K-2101, TK-1001
               The standard convention in refineries and chemical plants:
               a short class letter, a unit-based number, and an optional
               train suffix (A/B for duty and standby).

Single-letter prefixes require at least three digits. Refinery numbering always
has them, and the constraint prevents ordinary prose ("section D-1", "Figure
E-2") from being mistaken for equipment.
"""

import re
from typing import Dict, List

# --- Descriptive prefixes -----------------------------------------------------
DESCRIPTIVE_PREFIXES = (
    "PUMP", "VALVE", "PSV", "COMP", "MTR", "BRG", "HX", "TK",
    "FAN", "BLR", "ENG", "SYS",
)

# --- ISA / process-plant class letters ----------------------------------------
# P pump, E exchanger, K compressor, V vessel, T tower, C column,
# D drum, F fired heater, R reactor
ISA_PREFIXES = ("P", "E", "K", "V", "T", "C", "D", "F", "R")

_DESCRIPTIVE = "|".join(DESCRIPTIVE_PREFIXES)
_ISA = "|".join(ISA_PREFIXES)

# Longer descriptive prefixes are alternated FIRST so that, for example, "PSV-1201"
# matches as PSV rather than as P followed by "SV-1201".
# The negative lookbehind stops a tag matching INSIDE a longer reference. Without
# it, the register id "INS-PSV-2024" yielded a phantom relief valve "PSV-2024",
# and "IOM-P101A-R6" style refs can produce similar ghosts. A real tag always
# starts a token, so it is never directly preceded by a letter, digit or hyphen.
ASSET_TAG_REGEX = (
    rf"(?<![A-Za-z0-9-])(?:(?:{_DESCRIPTIVE})-\d{{2,4}}[A-Z]?|(?:{_ISA})-\d{{3,4}}[A-Z]?)\b"
)

ASSET_TAG_PATTERN = re.compile(ASSET_TAG_REGEX, re.IGNORECASE)

# "Asset: P-101A" headers in maintenance logs are the authoritative owner of an entry.
ASSET_HEADER_PATTERN = re.compile(rf"Asset:\s*({ASSET_TAG_REGEX})", re.IGNORECASE)

# Tokens that look like tags but are documents, standards or parts. Excluded so
# they never appear as plant equipment in the asset register.
NON_ASSET_PREFIXES = {
    "ERN", "RCA", "WO", "SOP", "IOM", "PM", "AR", "INS", "MNT", "SAF", "PSS",
    "ISO", "OSHA", "API", "ANSI", "ASME", "NFPA", "OISD", "PPE", "TA", "QMS",
    "JC", "SKF", "HPX", "VG", "LEL", "DCS",
}

EQUIPMENT_CATEGORIES: Dict[str, str] = {
    # descriptive
    "PUMP": "Rotating - pump",
    "COMP": "Rotating - compressor",
    "FAN": "Rotating - fan",
    "MTR": "Electrical - motor",
    "VALVE": "Flow control - valve",
    "PSV": "Safety - relief valve",
    "HX": "Static - heat exchanger",
    "TK": "Static - tank",
    "BLR": "Static - boiler",
    "BRG": "Component - bearing",
    "ENG": "Rotating - engine",
    "SYS": "System",
    # ISA / process
    "P": "Rotating - pump",
    "E": "Static - heat exchanger",
    "K": "Rotating - compressor",
    "V": "Static - vessel",
    "T": "Static - tower",
    "C": "Static - column",
    "D": "Static - drum",
    "F": "Fired - heater",
    "R": "Static - reactor",
}


def tag_prefix(tag: str) -> str:
    """Returns the class prefix of a tag, e.g. 'P-101A' -> 'P'."""
    return tag.split("-", 1)[0].upper()


def categorise(tag: str) -> str:
    return EQUIPMENT_CATEGORIES.get(tag_prefix(tag), "Unclassified")


def extract_asset_tags(text: str) -> List[str]:
    """
    Returns unique, upper-cased equipment tags found in the text, in order of
    first appearance, excluding document and standard references.
    """
    found: List[str] = []
    seen = set()
    for match in ASSET_TAG_PATTERN.findall(text or ""):
        tag = match.upper()
        if tag_prefix(tag) in NON_ASSET_PREFIXES:
            continue
        if tag not in seen:
            seen.add(tag)
            found.append(tag)
    return found


def extract_asset_header(text: str) -> str | None:
    """Returns the LAST 'Asset: <tag>' header in the text, or None."""
    matches = ASSET_HEADER_PATTERN.findall(text or "")
    return matches[-1].upper() if matches else None
