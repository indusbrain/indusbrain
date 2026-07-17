import re
from typing import List, Dict, Any

class IndustrialConflictEngine:
    """
    Enterprise In-Memory Anomaly Detection Matrix. Algorithmically evaluates
    cross-document text context slices to identify parameter and threshold 
    contradictions without incurring LLM pricing or latency overhead.
    """
    def __init__(self):
        # Maps matching industrial metric indicators along with trailing unit parameters
        self.metric_pattern = re.compile(
            r"(\b\d+(?:\.\d+)?)\s*(PSI|bar|RPM|kW|V|Hz|mm|°C|bar)\b", 
            re.IGNORECASE
        )
        # Binds parameters against equipment tag definitions
        self.asset_pattern = re.compile(
            r"\b(PUMP|VALVE|SYS|COMP|PSV)[-_\s]*(\d{2,4})\b", 
            re.IGNORECASE
        )
        
        # Engineering delta tolerances (Trigger alert if variation exceeds threshold)
        self.tolerances = {
            "PSI": 5.0,
            "BAR": 0.5,
            "RPM": 50.0,
            "KW": 1.0,
            "V": 2.0,
            "°C": 2.0
        }

    def analyze_context_slices(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scans document segments, populates lookahead matrices, and calculates
        numerical discrepancy indexes across multi-version text elements.
        """
        # Dictionary layout: { "PUMP-101": { "PSI": [350.0, 280.0] } }
        registry: Dict[str, Dict[str, List[float]]] = {}
        conflicts = []

        for chunk in chunks:
            text = chunk.get("content", "")
            filename = chunk.get("filename", "Unknown Document")
            
            # Extract active asset identifier tags within this segment text footprint
            assets = []
            for match in self.asset_pattern.findall(text):
                assets.append(f"{match[0].upper()}-{match[1]}")
                
            if not assets:
                continue

            # Parse out all parameter measurement combinations
            for match in self.metric_pattern.findall(text):
                numeric_value = float(match[0])
                unit = match[1].upper()

                # Bind the metrics to every asset identified within this active block context
                for asset in set(assets):
                    if asset not in registry:
                        registry[asset] = {}
                    if unit not in registry[asset]:
                        registry[asset][unit] = []
                    
                    # Log the numerical data parameter along with source tracking indicators
                    registry[asset][unit].append({
                        "value": numeric_value,
                        "source": filename
                    })

        # Evaluate the tracking registry table cells to isolate threshold variations
        for asset, metrics in registry.items():
            for unit, occurrences in metrics.items():
                if len(occurrences) < 2:
                    continue

                values = [item["value"] for item in occurrences]
                max_val = max(values)
                min_val = min(values)
                delta_variance = max_val - min_val
                allowed_tolerance = self.tolerances.get(unit, 0.0)

                # 🚨 ANOMALY BOUNDARY AUDIT: Trigger warning status if variance pops past our tolerance index
                if delta_variance > allowed_tolerance:
                    sources = list(set([item["source"] for item in occurrences]))
                    conflicts.append({
                        "asset": asset,
                        "metric": unit,
                        "variance": round(delta_variance, 2),
                        "max_value": max_val,
                        "min_value": min_val,
                        "conflicting_sources": sources,
                        "message": f"CRITICAL SPECIFICATION CONTRADICTION: Asset {asset} logs conflicting thresholds for {unit} across files. Max limit is listed as {max_val}, but Min limit drops down to {min_val}."
                    })

        return {
            "conflict_detected": len(conflicts) > 0,
            "severity": "CRITICAL" if len(conflicts) > 0 else "OK",
            "detected_anomalies": conflicts
        }

# Instantiate our cross-document cognitive scraper instance into system memory
industrial_conflict_engine = IndustrialConflictEngine()