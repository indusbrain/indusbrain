import re
from typing import Any, Dict, List, Tuple


class IndustrialConflictEngine:
    """
    Cross-document contradiction detector.

    Finds cases where two DIFFERENT documents state different values for the same
    parameter on the same asset - for example an OEM manual saying a pump's limit
    is 250 PSI while a later revision notice says 380 PSI.

    Everything reported is derived from the actual indexed text. When no
    contradiction exists the engine returns an empty result. It never emits a
    sample or placeholder finding.
    """

    def __init__(self):
        # Value + unit pairs, e.g. "250 PSI", "82 CELSIUS", "2900 RPM".
        self.metric_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*"
            r"(PSI|BAR|RPM|GPM|KW|HZ|MM/S|MM|CELSIUS|°C|DEGC|VOLT|V)\b",
            re.IGNORECASE,
        )
        # Equipment tags - shared definition, see app/services/asset_tags.py
        from app.services.asset_tags import ASSET_TAG_PATTERN
        self.asset_pattern = ASSET_TAG_PATTERN

        # Normalises unit spellings so "°C", "DEGC" and "CELSIUS" compare equal.
        self.unit_aliases = {
            "°C": "CELSIUS", "DEGC": "CELSIUS", "CELSIUS": "CELSIUS",
            "PSI": "PSI", "BAR": "BAR", "RPM": "RPM", "GPM": "GPM",
            "KW": "KW", "HZ": "HZ", "MM": "MM", "MM/S": "MM/S",
            "V": "VOLT", "VOLT": "VOLT",
        }

        # A difference must exceed this to count as a genuine contradiction rather
        # than rounding or normal measurement spread.
        self.tolerances = {
            "PSI": 5.0, "BAR": 0.5, "RPM": 50.0, "GPM": 5.0,
            "KW": 1.0, "HZ": 1.0, "MM": 0.5, "MM/S": 0.5,
            "CELSIUS": 2.0, "VOLT": 2.0,
        }

        # Human-readable parameter names for the UI.
        self.parameter_names = {
            "PSI": "Pressure", "BAR": "Pressure", "RPM": "Rotational speed",
            "GPM": "Flow rate", "KW": "Power", "HZ": "Frequency",
            "MM": "Clearance / dimension", "MM/S": "Vibration",
            "CELSIUS": "Temperature", "VOLT": "Voltage",
        }

    def _normalise_unit(self, raw_unit: str) -> str:
        return self.unit_aliases.get(raw_unit.upper(), raw_unit.upper())

    def _extract_assets(self, text: str) -> List[str]:
        from app.services.asset_tags import extract_asset_tags
        return sorted(extract_asset_tags(text))

    def _sentence_for(self, text: str, position: int) -> str:
        """Returns the sentence containing a match, so findings quote real context."""
        start = max(text.rfind(".", 0, position), text.rfind("\n", 0, position)) + 1
        end_candidates = [p for p in (text.find(".", position), text.find("\n", position)) if p != -1]
        end = min(end_candidates) if end_candidates else len(text)
        return text[start:end].strip()[:300]

    # Words that identify WHICH parameter a number refers to. Comparing "discharge
    # pressure" against "hydrostatic test pressure" is meaningless even though both
    # are in PSI, so a measurement only ever competes with the same qualifier.
    PARAMETER_QUALIFIERS = (
        "discharge", "suction", "hydrostatic", "test", "bearing", "seal face",
        "seal", "operating", "rated", "design", "inlet", "outlet", "casing",
        "ambient", "header", "differential", "set", "relief", "vibration",
        "flow", "speed", "housing",
    )

    def _classify_parameter(self, sentence: str, unit: str) -> str:
        """
        Builds a comparison key describing WHAT is being measured.

        Only measurements sharing a key are ever compared. This is what stops the
        engine reporting a pump's suction pressure and a casing test pressure as a
        contradiction merely because both are expressed in PSI.
        """
        lowered = sentence.lower()
        found = [q for q in self.PARAMETER_QUALIFIERS if q in lowered]
        if not found:
            return f"UNQUALIFIED::{unit}"
        # Longest qualifier wins ("seal face" beats "seal").
        found.sort(key=len, reverse=True)
        return f"{found[0].upper()}::{unit}"

    def analyze_context_slices(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scans indexed chunks and returns genuine cross-document contradictions.

        `chunks` items need: {"content": str, "filename": str}
        """
        # (asset, parameter_key) -> list of observations
        registry: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

        for chunk in chunks:
            text = chunk.get("content") or ""
            if not text:
                continue
            source_file = chunk.get("filename") or "Unknown document"

            for match in self.metric_pattern.finditer(text):
                value = float(match.group(1))
                unit = self._normalise_unit(match.group(2))
                context_sentence = self._sentence_for(text, match.start())

                # Bind the measurement ONLY to assets named in the SAME SENTENCE.
                # Chunk-level binding attached every number to every nearby tag and
                # generated large numbers of meaningless "conflicts".
                assets_in_sentence = self._extract_assets(context_sentence)
                if not assets_in_sentence:
                    continue

                parameter_key = self._classify_parameter(context_sentence, unit)
                if parameter_key.startswith("UNQUALIFIED"):
                    # We cannot tell what this number describes, so we must not
                    # assert that it contradicts anything.
                    continue

                for asset in assets_in_sentence:
                    registry.setdefault((asset, parameter_key), []).append({
                        "value": value,
                        "source": source_file,
                        "context": context_sentence,
                    })

        conflicts: List[Dict[str, Any]] = []

        for (asset, parameter_key), observations in registry.items():
            unit = parameter_key.split("::")[-1]
            # A contradiction requires at least two DIFFERENT source documents.
            distinct_sources = {o["source"] for o in observations}
            if len(distinct_sources) < 2:
                continue

            lowest = min(observations, key=lambda o: o["value"])
            highest = max(observations, key=lambda o: o["value"])

            # Both extremes must come from different documents, otherwise this is
            # just a range stated inside one document (e.g. min and max flow).
            if lowest["source"] == highest["source"]:
                continue

            spread = highest["value"] - lowest["value"]
            tolerance = self.tolerances.get(unit, 0.0)
            if spread <= tolerance:
                continue

            qualifier = parameter_key.split("::")[0].replace("_", " ").title()
            parameter_label = f"{qualifier} {self.parameter_names.get(unit, unit).lower()}"
            severity = "CRITICAL" if unit in ("PSI", "BAR", "CELSIUS") else "WARNING"

            conflicts.append({
                "asset_tag": asset,
                "parameter": parameter_label,
                "unit": unit,
                "severity": severity,
                "variance": round(spread, 2),
                "low_value": lowest["value"],
                "low_source": lowest["source"],
                "low_context": lowest["context"],
                "high_value": highest["value"],
                "high_source": highest["source"],
                "high_context": highest["context"],
                "conflict_statement": (
                    f"{parameter_label} for {asset} is stated as "
                    f"{lowest['value']} {unit} in '{lowest['source']}' but "
                    f"{highest['value']} {unit} in '{highest['source']}'. "
                    f"Difference of {round(spread, 2)} {unit} exceeds the "
                    f"{tolerance} {unit} tolerance."
                ),
                "recommended_action": (
                    f"Until an engineer resolves this, apply the lower value "
                    f"({lowest['value']} {unit}) as the controlling limit for {asset}."
                ),
            })

        # Most severe and largest discrepancies first.
        conflicts.sort(
            key=lambda c: (c["severity"] != "CRITICAL", -c["variance"])
        )

        return {
            "conflict_detected": len(conflicts) > 0,
            "severity": "CRITICAL" if any(c["severity"] == "CRITICAL" for c in conflicts)
                        else ("WARNING" if conflicts else "OK"),
            "detected_anomalies": conflicts,
            "chunks_scanned": len(chunks),
        }


# Instantiate our cross-document contradiction detector
industrial_conflict_engine = IndustrialConflictEngine()
