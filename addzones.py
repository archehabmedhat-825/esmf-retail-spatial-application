
from __future__ import annotations

from typing import Any, Dict, List, Tuple

INTENSITY_FACTORS = {"low": 0.0, "medium": 0.5, "high": 1.0}

ADDED_ZONE_SPECS: dict[str, dict[str, Any]] = {
    "consultation_styling": {
        "label": "CONSULTATION / STYLING",
        "range": (0.03, 0.06),
        "anchor": "fitting_edge",
        "shape": "balanced",
    },
    "promotional_featured": {
        "label": "PROMOTIONAL / FEATURED",
        "range": (0.05, 0.10),
        "anchor": "front",
        "shape": "shallow",
    },
    "digital_interaction": {
        "label": "PROMOTIONAL / FEATURED DISPLAY",
        "range": (0.02, 0.05),
        "anchor": "central",
        "shape": "compact",
    },
    "queue_pocket": {
        "label": "GAMING & INTERACTIONS",
        "range": (0.02, 0.04),
        "anchor": "checkout_edge",
        "shape": "narrow",
    },
    "lounge_seating": {
        "label": "LOUNGE / SEATING",
        "range": (0.04, 0.08),
        "anchor": "quiet_side",
        "shape": "broad",
    },
    "scanner_support": {
        "label": "SCANNER / MIRROR SUPPORT",
        "range": (0.02, 0.04),
        "anchor": "fitting_edge",
        "shape": "compact",
    },
}

UI_NAME_TO_KEY = {
    "Promotional / Featured display": "digital_interaction",
    "Gaming & Interactions": "queue_pocket",
    "Lounge / Seating Corner": "lounge_seating",
}

PLACEMENT_ORDER = [
    "promotional_featured",
    "consultation_styling",
    "digital_interaction",
    "lounge_seating",
    "queue_pocket",
    "scanner_support",
]

MAX_ADDED_SHARE = 0.40

Rect = Dict[str, float]

def _rect(x: float, y: float, length: float, width: float) -> Rect:
    return {
        "x": round(float(x), 6),
        "y": round(float(y), 6),
        "length": round(max(0.0, float(length)), 6),
        "width": round(max(0.0, float(width)), 6),
    }

def _right(r: Rect) -> float:
    return r["x"] + r["length"]

def _top(r: Rect) -> float:
    return r["y"] + r["width"]

def _overlaps(a: Rect, b: Rect) -> bool:
    return not (
        _right(a) <= b["x"] or
        a["x"] >= _right(b) or
        _top(a) <= b["y"] or
        a["y"] >= _top(b)
    )

def _contains(container: Rect, block: Rect) -> bool:
    return (
        block["x"] >= container["x"] - 1e-6 and
        block["y"] >= container["y"] - 1e-6 and
        _right(block) <= _right(container) + 1e-6 and
        _top(block) <= _top(container) + 1e-6
    )

def _intensity_ratio(zone_key: str, intensity: str) -> float:
    low, high = ADDED_ZONE_SPECS[zone_key]["range"]
    f = INTENSITY_FACTORS[intensity]
    return round(low + (high - low) * f, 6)

def _shape_dims(area: float, shape: str) -> tuple[float, float]:
    if shape == "shallow":
        width = max(1.2, min(2.0, area / 2.2))
        length = max(1.8, area / width)
    elif shape == "narrow":
        width = max(1.2, min(1.8, area / 2.0))
        length = max(1.6, area / width)
    elif shape == "broad":
        width = max(1.8, min(2.4, area / 2.2))
        length = max(2.0, area / width)
    elif shape == "compact":
        width = max(1.2, min(1.8, area ** 0.5))
        length = max(1.2, area / width)
    else:  # balanced
        width = max(1.5, min(2.2, area ** 0.5))
        length = max(1.5, area / width)
    return round(length, 6), round(width, 6)

def _anchor_candidates(zone_key: str, sales: Rect, zoning: Dict[str, Any], length: float, width: float) -> List[Rect]:
    fitting = zoning["fitting_zone"]
    checkout = zoning["checkout_zone"]
    candidates: List[Rect] = []
    margin = 0.15

    def clamp_rect(x: float, y: float, l: float, w: float) -> Rect:
        return _rect(
            max(sales["x"], min(x, _right(sales) - l)),
            max(sales["y"], min(y, _top(sales) - w)),
            l, w
        )

    if zone_key == "promotional_featured":
        candidates.append(clamp_rect(sales["x"] + margin, sales["y"] + margin, length, width))
        candidates.append(clamp_rect(_right(sales) - length - margin, sales["y"] + margin, length, width))
        candidates.append(clamp_rect(sales["x"] + (sales["length"] - length) / 2.0, sales["y"] + margin, length, width))
    elif zone_key in ("consultation_styling", "scanner_support"):
        # adjacent to fitting-facing side of sales
        if abs(fitting["x"] - sales["x"]) < 0.2:
            candidates.append(clamp_rect(_right(fitting) + margin, max(sales["y"] + margin, fitting["y"]), length, width))
        elif abs(_right(fitting) - _right(sales)) < 0.2:
            candidates.append(clamp_rect(fitting["x"] - length - margin, max(sales["y"] + margin, fitting["y"]), length, width))
        else:
            candidates.append(clamp_rect(sales["x"] + margin, max(sales["y"] + margin, fitting["y"] - width - margin), length, width))
        candidates.append(clamp_rect(sales["x"] + margin, _top(sales) - width - margin, length, width))
    elif zone_key == "queue_pocket":
        # adjacent to checkout-facing side of sales
        if abs(checkout["x"] - sales["x"]) < 0.2:
            candidates.append(clamp_rect(_right(checkout) + margin, max(sales["y"] + margin, checkout["y"]), length, width))
        elif abs(_right(checkout) - _right(sales)) < 0.2:
            candidates.append(clamp_rect(checkout["x"] - length - margin, max(sales["y"] + margin, checkout["y"]), length, width))
        else:
            candidates.append(clamp_rect(sales["x"] + margin, max(sales["y"] + margin, checkout["y"] - width - margin), length, width))
    elif zone_key == "lounge_seating":
        candidates.append(clamp_rect(_right(sales) - length - margin, _top(sales) - width - margin, length, width))
        candidates.append(clamp_rect(sales["x"] + margin, _top(sales) - width - margin, length, width))
        candidates.append(clamp_rect(_right(sales) - length - margin, sales["y"] + sales["width"] * 0.5 - width / 2.0, length, width))
    else:  # digital_interaction
        candidates.append(clamp_rect(sales["x"] + (sales["length"] - length) / 2.0, sales["y"] + sales["width"] * 0.30, length, width))
        candidates.append(clamp_rect(_right(sales) - length - margin, sales["y"] + sales["width"] * 0.35, length, width))
        candidates.append(clamp_rect(sales["x"] + margin, sales["y"] + sales["width"] * 0.35, length, width))
    return candidates

def build_added_zones(zoning: Dict[str, Any], selected_keys: List[str], intensity: str = "medium", frontage: Dict[str, Any] | None = None) -> Dict[str, Any]:
    sales = zoning["sales_zone"]
    base_sales_area = sales["length"] * sales["width"]
    frontage_area = 0.0
    if frontage and frontage.get("zones"):
        frontage_area = sum(float(z.get("rect", {}).get("length", 0.0)) * float(z.get("rect", {}).get("width", 0.0)) for z in frontage.get("zones", []))
    display_area = base_sales_area + frontage_area

    zone_ratios = {}
    total_share = 0.0
    for k in selected_keys:
        r = _intensity_ratio(k, intensity)
        zone_ratios[k] = r
        total_share += r

    messages: List[str] = []
    valid = True
    if len(selected_keys) > 1 and total_share > MAX_ADDED_SHARE + 1e-9 and total_share > 0:
        scale = MAX_ADDED_SHARE / total_share
        for k in list(zone_ratios.keys()):
            zone_ratios[k] = round(zone_ratios[k] * scale, 6)
        total_share = round(sum(zone_ratios.values()), 6)
    elif total_share > MAX_ADDED_SHARE + 1e-9:
        total_share = MAX_ADDED_SHARE

    placed = []
    occupied: List[Rect] = []

    for key in PLACEMENT_ORDER:
        if key not in selected_keys:
            continue
        spec = ADDED_ZONE_SPECS[key]
        target_area = zone_ratios[key] * display_area
        length, width = _shape_dims(target_area, spec["shape"])

        candidates = _anchor_candidates(key, sales, zoning, length, width)
        chosen = None
        for cand in candidates:
            # Added-value zones may share the same display-island hosts and are later
            # re-hosted by islands in the drawing stage. Therefore, do not reject a
            # candidate here merely because it overlaps another added-zone target
            # rectangle inside the sales zone.
            if _contains(sales, cand):
                chosen = cand
                break
        if chosen is None:
            valid = False
            messages.append(f"{spec['label']} zone could not fit inside the sales zone with the selected intensity.")
            continue

        placed.append({
            "key": key,
            "label": spec["label"],
            "rect": chosen,
            "target_ratio": zone_ratios[key],
            "target_area_m2": round(target_area, 6),
            "actual_area_m2": round(chosen["length"] * chosen["width"], 6),
            "anchor": spec["anchor"],
        })
        occupied.append(chosen)

    return {
        "valid": valid and len(messages) == 0,
        "messages": messages,
        "intensity": intensity,
        "base_sales_area_m2": round(base_sales_area, 6),
        "frontage_display_area_m2": round(frontage_area, 6),
        "display_area_m2": round(display_area, 6),
        "total_added_share": round(total_share, 6),
        "total_added_area_m2": round(sum(p["actual_area_m2"] for p in placed), 6),
        "sales_area_after_added_m2": round(base_sales_area - sum(p["actual_area_m2"] for p in placed), 6),
        "selected_zone_keys": selected_keys,
        "zones": placed,
    }

def validate_added_zones(added: Dict[str, Any]) -> Dict[str, Any]:
    return {"is_valid": bool(added.get("valid", False)), "messages": list(added.get("messages", []))}
