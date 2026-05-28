
from __future__ import annotations

from typing import Any, Dict, List

MIN_CLEAR_SPACING = 1.50
COMFORT_LOW = 2.00
COMFORT_HIGH = 3.50

def _classify_spacing(spacing: float) -> str:
    if spacing < MIN_CLEAR_SPACING:
        return "INVALID"
    if spacing < COMFORT_LOW:
        return "TIGHT"
    if spacing <= COMFORT_HIGH:
        return "GOOD"
    return "SPACIOUS"

def analyze_spacing(circulation: Dict[str, Any], recommended_spacing_m: float = 2.50) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    logic = circulation.get("spacing_logic", {})
    spine_w = circulation.get("widths", {}).get("primary_spine_m", 0.0)

    # First field: from entrance offset to service connector boundary
    start_spacing = spine_w
    items.append({
        "between": "entrance_offset and service_connector",
        "value_m": round(start_spacing, 6),
        "status": _classify_spacing(start_spacing),
        "recommended_spacing_m": round(recommended_spacing_m, 3),
        "recommended_check": "MEETS" if start_spacing >= recommended_spacing_m else "BELOW",
        "rule": "start spacing equals main spine width",
    })

    sec_count = int(logic.get("secondary_aisle_count", 0) or 0)
    sec_spacing = float(logic.get("actual_secondary_spacing_m", 0.0) or 0.0)

    if sec_count > 0:
        # Between service connector and first secondary
        items.append({
            "between": "service_connector and secondary_1",
            "value_m": round(sec_spacing, 6),
            "status": _classify_spacing(sec_spacing),
            "recommended_spacing_m": round(recommended_spacing_m, 3),
            "recommended_check": "MEETS" if sec_spacing >= recommended_spacing_m else "BELOW",
        })
        # Between subsequent secondary aisles
        for i in range(1, sec_count):
            items.append({
                "between": f"secondary_{i} and secondary_{i+1}",
                "value_m": round(sec_spacing, 6),
                "status": _classify_spacing(sec_spacing),
                "recommended_spacing_m": round(recommended_spacing_m, 3),
                "recommended_check": "MEETS" if sec_spacing >= recommended_spacing_m else "BELOW",
            })
        # Between last secondary and entrance offset baseline
        items.append({
            "between": f"secondary_{sec_count} and entrance_offset",
            "value_m": round(sec_spacing, 6),
            "status": _classify_spacing(sec_spacing),
            "recommended_spacing_m": round(recommended_spacing_m, 3),
            "recommended_check": "MEETS" if sec_spacing >= recommended_spacing_m else "BELOW",
        })

    return {
        "recommended_spacing_m": round(recommended_spacing_m, 3),
        "minimum_spacing_m": MIN_CLEAR_SPACING,
        "comfort_band_m": [COMFORT_LOW, COMFORT_HIGH],
        "results": items,
        "valid": all(item["value_m"] >= MIN_CLEAR_SPACING for item in items) if items else True,
        "messages": [
            f"{item['between']} spacing is {item['value_m']:.2f} m ({item['status']})"
            for item in items
        ],
    }
