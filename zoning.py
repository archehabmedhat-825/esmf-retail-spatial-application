
from __future__ import annotations

from typing import Any, Dict

BALANCED_BY_BAND: dict[str, dict[str, float]] = {
    "micro":  {"sales": 0.575, "fitting": 0.09,  "checkout": 0.035, "back_of_house": 0.125},
    "small":  {"sales": 0.60,  "fitting": 0.10,  "checkout": 0.04,  "back_of_house": 0.125},
    "normal": {"sales": 0.55,  "fitting": 0.125, "checkout": 0.045, "back_of_house": 0.125},
    "large":  {"sales": 0.50,  "fitting": 0.135, "checkout": 0.055, "back_of_house": 0.15},
    "xl":     {"sales": 0.45,  "fitting": 0.16,  "checkout": 0.065, "back_of_house": 0.175},
}

MODE_PRESETS: dict[str, dict[str, dict[str, float]]] = {
    "balanced": BALANCED_BY_BAND,
    "sales_first": {
        "micro":  {"sales": 0.60, "fitting": 0.08,  "checkout": 0.03,  "back_of_house": 0.10},
        "small":  {"sales": 0.64, "fitting": 0.09,  "checkout": 0.03,  "back_of_house": 0.10},
        "normal": {"sales": 0.59, "fitting": 0.11,  "checkout": 0.035, "back_of_house": 0.10},
        "large":  {"sales": 0.54, "fitting": 0.12,  "checkout": 0.045, "back_of_house": 0.12},
        "xl":     {"sales": 0.49, "fitting": 0.145, "checkout": 0.055, "back_of_house": 0.15},
    },
    "fitting_first": {
        "micro":  {"sales": 0.55, "fitting": 0.10, "checkout": 0.035, "back_of_house": 0.12},
        "small":  {"sales": 0.57, "fitting": 0.12, "checkout": 0.04,  "back_of_house": 0.12},
        "normal": {"sales": 0.50, "fitting": 0.15, "checkout": 0.045, "back_of_house": 0.12},
        "large":  {"sales": 0.46, "fitting": 0.15, "checkout": 0.055, "back_of_house": 0.14},
        "xl":     {"sales": 0.42, "fitting": 0.18, "checkout": 0.065, "back_of_house": 0.16},
    },
    "service_first": {
        "micro":  {"sales": 0.55, "fitting": 0.08, "checkout": 0.04,  "back_of_house": 0.15},
        "small":  {"sales": 0.57, "fitting": 0.08, "checkout": 0.05,  "back_of_house": 0.15},
        "normal": {"sales": 0.50, "fitting": 0.10, "checkout": 0.06,  "back_of_house": 0.15},
        "large":  {"sales": 0.46, "fitting": 0.12, "checkout": 0.07,  "back_of_house": 0.18},
        "xl":     {"sales": 0.42, "fitting": 0.14, "checkout": 0.08,  "back_of_house": 0.20},
    },
}

MODE_LABELS = {
    "balanced": "Balanced",
    "sales_first": "Sales-first",
    "fitting_first": "Fitting-first",
    "service_first": "Service-first",
}


MIN_FRONTAGE_DEPTH = 1.5
MIN_DECOMPRESSION_DEPTH = 1.5
MIN_SALES_DEPTH = 3.0
MIN_SERVICE_DEPTH = 2.0
MIN_SERVICE_WIDTH = 1.2
MIN_BOH_DEPTH = 1.5
MIN_TOTAL_STORE_DEPTH = 8.0

def _rect(x: float, y: float, length: float, width: float) -> dict[str, float]:
    return {
        "x": round(float(x), 6),
        "y": round(float(y), 6),
        "length": round(max(0.0, float(length)), 6),
        "width": round(max(0.0, float(width)), 6),
    }

def build_zoning(shell: Dict[str, Any], fitting_side: str = "left", program_intent: str = "balanced") -> Dict[str, Any]:
    inner = shell["inner_clear_boundary"]
    band = shell["store_band"]
    if program_intent not in MODE_PRESETS:
        program_intent = "balanced"
    ratios = MODE_PRESETS[program_intent][band]

    total_area = inner["length"] * inner["width"]
    inner_x = inner["x"]
    inner_y = inner["y"]
    inner_w = inner["length"]
    inner_d = inner["width"]

    entrance = shell["entrance_opening"]
    entrance_node_size = 1.50
    entrance_center_x = (float(entrance["x1"]) + float(entrance["x2"])) / 2.0
    entrance_node_x = max(inner_x, min(entrance_center_x - entrance_node_size / 2.0, inner_x + inner_w - entrance_node_size))
    entrance_node = _rect(entrance_node_x, inner_y, entrance_node_size, entrance_node_size)

    fit_area = ratios["fitting"] * total_area
    checkout_area = ratios["checkout"] * total_area
    boh_area = ratios["back_of_house"] * total_area

    # Constitutional depth bands (shared stacks, not raw additive zone sums)
    boh_depth = max(MIN_BOH_DEPTH, boh_area / inner_w)
    service_front_depth = max(MIN_SERVICE_DEPTH, (fit_area + checkout_area) / inner_w)

    # Preserve the minimum sales depth after protecting BOH and service bands.
    max_back_band_depth = max(0.0, inner_d - MIN_SALES_DEPTH)
    back_band_depth = boh_depth + service_front_depth
    if back_band_depth > max_back_band_depth and max_back_band_depth > 0.0:
        # First preserve BOH, then compress service only down to its constitutional minimum.
        back_band_depth = max_back_band_depth
        service_front_depth = max(MIN_SERVICE_DEPTH, back_band_depth - boh_depth)
        boh_depth = max(MIN_BOH_DEPTH, back_band_depth - service_front_depth)

    back_band_y = inner_y + inner_d - back_band_depth
    boh_y = inner_y + inner_d - boh_depth

    fit_width = fit_area / service_front_depth if service_front_depth > 0 else inner_w * 0.5
    fit_width = max(0.0, min(inner_w, fit_width))
    checkout_width = inner_w - fit_width

    # Constitutional service hierarchy: fitting must never resolve smaller than checkout.
    # This keeps the geometric split aligned with the baseline ratios even if upstream
    # ratio selection or floating-point effects distort the service-band allocation.
    if fit_width < checkout_width:
        fit_width, checkout_width = checkout_width, fit_width

    # T8-led service adjustment: widen the checkout zone along the X-axis by 15%
    # by moving the vertical split between checkout and fitting. The shift remains
    # bounded so it does not break the constitutional service widths or the rule
    # that fitting should not resolve smaller than checkout.
    boosted_checkout_width = checkout_width * 1.15
    max_checkout_width = min(inner_w - MIN_SERVICE_WIDTH, inner_w * 0.5)
    checkout_width = min(boosted_checkout_width, max_checkout_width)
    fit_width = inner_w - checkout_width

    if fitting_side == "right":
        checkout_rect = _rect(inner_x, back_band_y, checkout_width, service_front_depth)
        fitting_rect = _rect(inner_x + checkout_width, back_band_y, fit_width, service_front_depth)
    else:
        fitting_rect = _rect(inner_x, back_band_y, fit_width, service_front_depth)
        checkout_rect = _rect(inner_x + fit_width, back_band_y, checkout_width, service_front_depth)

    boh_rect = _rect(inner_x, boh_y, inner_w, boh_depth)
    sales_rect = _rect(inner_x, inner_y, inner_w, max(0.0, back_band_y - inner_y))

    split_x = round(fitting_rect["x"] + fitting_rect["length"], 6) if fitting_side == "left" else round(checkout_rect["x"] + checkout_rect["length"], 6)

    entrance_node["label"] = "ENTRANCE /\nDECOMPRESSION"
    entrance_node["zone_type"] = "entrance"
    sales_rect["label"] = "SALES / DISPLAY"
    sales_rect["zone_type"] = "sales"
    fitting_rect["label"] = "FITTING\nSUITE"
    fitting_rect["zone_type"] = "fitting"
    checkout_rect["label"] = "CHECKOUT"
    checkout_rect["zone_type"] = "checkout"
    boh_rect["label"] = "BACK OF HOUSE\n(STAFF ONLY)"
    boh_rect["zone_type"] = "boh"

    return {
        "store_band": band,
        "program_intent": program_intent,
        "program_intent_label": MODE_LABELS[program_intent],
        "ratios": ratios,
        "entrance_node": entrance_node,
        "sales_zone": sales_rect,
        "back_band": _rect(inner_x, back_band_y, inner_w, back_band_depth),
        "fitting_zone": fitting_rect,
        "checkout_zone": checkout_rect,
        "boh_zone": boh_rect,
        "fitting_side": fitting_side,
        "service_lines": {
            "sales_to_back_y": round(back_band_y, 6),
            "service_to_boh_y": round(boh_y, 6),
            "fit_checkout_x": split_x,
        },
        "circulation_remainder_share": round(1.0 - (ratios["sales"] + ratios["fitting"] + ratios["checkout"] + ratios["back_of_house"]), 6),
    }

def validate_zoning(shell: Dict[str, Any], zoning: Dict[str, Any]) -> Dict[str, Any]:
    inner = shell["inner_clear_boundary"]
    messages = []
    valid = True

    if inner["width"] < MIN_TOTAL_STORE_DEPTH:
        valid = False
        messages.append(f"Store depth fell below {MIN_TOTAL_STORE_DEPTH:.2f} m minimum constitutional threshold.")

    if zoning["entrance_node"]["width"] < MIN_DECOMPRESSION_DEPTH:
        valid = False
        messages.append(f"Entrance decomposition depth fell below {MIN_DECOMPRESSION_DEPTH:.2f} m.")

    frontage_depth = float(zoning["sales_zone"]["width"])
    if frontage_depth < (MIN_FRONTAGE_DEPTH + MIN_SALES_DEPTH):
        valid = False
        messages.append(
            f"Sales band depth fell below the required frontage + sales constitutional minimum ({MIN_FRONTAGE_DEPTH + MIN_SALES_DEPTH:.2f} m)."
        )

    service_band_depth = max(float(zoning["fitting_zone"]["width"]), float(zoning["checkout_zone"]["width"]))
    if service_band_depth < MIN_SERVICE_DEPTH:
        valid = False
        messages.append(f"Shared fitting/checkout service band fell below {MIN_SERVICE_DEPTH:.2f} m.")

    if zoning["fitting_zone"]["length"] < MIN_SERVICE_WIDTH:
        valid = False
        messages.append(f"Fitting zone became too narrow horizontally (< {MIN_SERVICE_WIDTH:.2f} m).")
    if zoning["checkout_zone"]["length"] < MIN_SERVICE_WIDTH:
        valid = False
        messages.append(f"Checkout zone became too narrow horizontally (< {MIN_SERVICE_WIDTH:.2f} m).")

    if zoning["fitting_zone"]["length"] + 1e-6 < zoning["checkout_zone"]["length"]:
        valid = False
        messages.append("Fitting zone resolved smaller than checkout zone, which violates the baseline service hierarchy.")

    if zoning["boh_zone"]["width"] < MIN_BOH_DEPTH:
        valid = False
        messages.append(f"BOH depth fell below {MIN_BOH_DEPTH:.2f} m.")

    total_required_depth = (
        max(MIN_FRONTAGE_DEPTH, MIN_DECOMPRESSION_DEPTH)
        + MIN_SALES_DEPTH
        + MIN_SERVICE_DEPTH
        + MIN_BOH_DEPTH
    )
    total_store_depth = float(shell.get("outer_boundary", {}).get("width", inner["width"]))
    if total_store_depth + 1e-6 < MIN_TOTAL_STORE_DEPTH:
        valid = False
        messages.append(
            f"Constitutional depth stack invalid: requires at least {MIN_TOTAL_STORE_DEPTH:.2f} m total store depth."
        )

    if zoning["fitting_zone"]["length"] + zoning["checkout_zone"]["length"] > inner["length"] + 1e-6:
        valid = False
        messages.append("Back-band split exceeds inner width.")

    return {"is_valid": valid, "messages": messages}
