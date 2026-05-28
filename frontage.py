
from __future__ import annotations
from typing import Any, Dict, List

def _rect(x: float, y: float, length: float, width: float) -> dict[str, float]:
    return {
        "x": round(float(x), 6),
        "y": round(float(y), 6),
        "length": round(max(0.0, float(length)), 6),
        "width": round(max(0.0, float(width)), 6),
    }

def build_frontage_zones(shell: Dict[str, Any], zoning: Dict[str, Any], circulation: Dict[str, Any] | None = None) -> Dict[str, Any]:
    inner = shell["inner_clear_boundary"]
    sales = zoning["sales_zone"]
    entrance = shell["entrance_opening"]
    opening_pos = entrance.get("position", "center")
    opening_w = float(entrance.get("width_m", 1.5))

    x_left = inner["x"]
    x_right = inner["x"] + inner["length"]
    x1 = float(entrance["x1"])
    x2 = float(entrance["x2"])
    spine = (circulation or {}).get("primary_spine") if circulation else None
    if opening_pos == "center" and spine:
        split_left = max(x_left, float(spine.get("x", x1)))
        split_right = min(x_right, float(spine.get("x", x1)) + float(spine.get("length", x2 - x1)))
    else:
        split_left = x1
        split_right = x2
    y = sales["y"]
    depth = min(max(opening_w, 1.5), sales["width"])

    left_len = max(0.0, split_left - x_left)
    right_len = max(0.0, x_right - split_right)

    zones: List[dict] = []

    if opening_pos == "center":
        if left_len > 0:
            zones.append({
                "rect": _rect(x_left, y, left_len, depth),
                "label": "FRONTAGE\nDISPLAY",
                "side": "left",
            })
        if right_len > 0:
            zones.append({
                "rect": _rect(split_right, y, right_len, depth),
                "label": "FRONTAGE\nDISPLAY",
                "side": "right",
            })
    elif opening_pos == "left":
        if right_len > 0:
            zones.append({
                "rect": _rect(split_right, y, right_len, depth),
                "label": "FRONTAGE\nDISPLAY",
                "side": "right_long",
            })
    elif opening_pos == "right":
        if left_len > 0:
            zones.append({
                "rect": _rect(x_left, y, left_len, depth),
                "label": "FRONTAGE\nDISPLAY",
                "side": "left_long",
            })

    return {
        "depth_m": round(depth, 3),
        "opening_width_m": round(opening_w, 3),
        "zones": zones,
        "count": len(zones),
        "rule": "frontage-zone depth is at least 1.50 m and follows entrance opening width where possible; center split aligns to main spine when available, otherwise to opening edges; length follows solid frontage segments",
    }
