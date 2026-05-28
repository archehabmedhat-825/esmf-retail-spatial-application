
from __future__ import annotations

from typing import Any, Dict, List

PRIMARY_SPINE_WIDTH_BY_BAND = {
    "micro": 1.60,
    "small": 1.70,
    "normal": 1.80,
    "large": 2.00,
    "xl": 2.20,
}

PROGRAM_INTENT_BONUS = {
    "balanced": 0.00,
    "sales_first": 0.10,
    "fitting_first": 0.00,
    "service_first": 0.10,
}

PRIMARY_SPINE_MIN = 1.60
PRIMARY_SPINE_MAX = 2.40
SECONDARY_MIN = 1.20
SECONDARY_MAX = 1.80
ENTRANCE_OFFSET_DEPTH = 1.50
SIDE_AISLE_WALL_OFFSET = 0.60
TERRITORIAL_MIN = 1.20
TERRITORIAL_MAX = 1.20

def _rect(x: float, y: float, length: float, width: float) -> dict[str, float]:
    return {
        "x": round(float(x), 6),
        "y": round(float(y), 6),
        "length": round(max(0.0, float(length)), 6),
        "width": round(max(0.0, float(width)), 6),
    }

def _center(rect: dict[str, float]) -> tuple[float, float]:
    return rect["x"] + rect["length"] / 2.0, rect["y"] + rect["width"] / 2.0

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

def _secondary_from_spine_width(spine_w: float) -> float:
    ratio = (spine_w - PRIMARY_SPINE_MIN) / (PRIMARY_SPINE_MAX - PRIMARY_SPINE_MIN)
    return round(SECONDARY_MIN + ratio * (SECONDARY_MAX - SECONDARY_MIN), 3)

def _territorial_from_spine_width(spine_w: float) -> float:
    ratio = (spine_w - PRIMARY_SPINE_MIN) / (PRIMARY_SPINE_MAX - PRIMARY_SPINE_MIN)
    return round(TERRITORIAL_MIN + ratio * (TERRITORIAL_MAX - TERRITORIAL_MIN), 3)

def _territory_spacing_target(mode: str) -> float:
    return 0.70 if str(mode).lower().startswith("single") else 1.50

def _vertical_territorial_aisles(x_start: float, x_end: float, y: float, h: float, territorial_w: float, secondary_w: float, mode: str) -> tuple[list[dict], list[dict], dict]:
    usable = max(0.0, x_end - x_start)
    target = _territory_spacing_target(mode)
    territorial = []
    secondary = []
    territorial_count = 0
    secondary_count = 0
    actual_spacing = 0.0

    # Alternating vertical rhythm:
    # spacing + territorial + spacing + secondary + spacing + territorial + ...
    min_needed = territorial_w + target
    if usable >= min_needed:
        # k = number of territorial aisles, starts with territorial and alternates with secondary
        # secondaries = max(0, k-1)
        k = 1
        best_k = 0
        while True:
            sec_n = max(0, k - 1)
            needed = k * territorial_w + sec_n * secondary_w + (k + sec_n + 1) * target
            if needed <= usable + 1e-9:
                best_k = k
                k += 1
            else:
                break

        if best_k > 0:
            territorial_count = best_k
            secondary_count = max(0, best_k - 1)
            total_bands = territorial_count + secondary_count
            used_width = territorial_count * territorial_w + secondary_count * secondary_w
            actual_spacing = (usable - used_width) / (total_bands + 1)

            x = x_start + actual_spacing
            for i in range(territorial_count):
                territorial.append(_rect(x, y, territorial_w, h))
                x += territorial_w + actual_spacing
                if i < secondary_count:
                    secondary.append(_rect(x, y, secondary_w, h))
                    x += secondary_w + actual_spacing

    return territorial, secondary, {
        "mode": mode,
        "target_spacing_m": round(target, 3),
        "usable_width_m": round(usable, 3),
        "actual_spacing_m": round(actual_spacing, 3),
        "territorial_count": territorial_count,
        "secondary_count": secondary_count,
        "starts_with": "territorial",
    }

def _spine_side(inner: dict, spine: dict) -> str:
    cx = spine["x"] + spine["length"] / 2.0
    icx = inner["x"] + inner["length"] / 2.0
    tol = inner["length"] * 0.08
    if abs(cx - icx) <= tol:
        return "center"
    return "left" if cx < icx else "right"

def _secondary_branch_rects(sales: dict, spine: dict, side: str, y: float, w: float) -> List[dict]:
    rects: List[dict] = []
    if side in ("center", "right"):
        left_len = max(0.0, spine["x"] - sales["x"])
        if left_len > 0.0:
            rects.append(_rect(sales["x"], y, left_len, w))
    if side in ("center", "left"):
        right_x = spine["x"] + spine["length"]
        right_len = max(0.0, (sales["x"] + sales["length"]) - right_x)
        if right_len > 0.0:
            rects.append(_rect(right_x, y, right_len, w))
    return rects

def build_circulation(shell: Dict[str, Any], zoning: Dict[str, Any], recommended_spacing_m: float = 2.50, user_spine_width_m: float | None = None, left_territory_mode: str = "Double Gondola", right_territory_mode: str = "Double Gondola") -> Dict[str, Any]:
    inner = shell["inner_clear_boundary"]
    entrance = zoning["entrance_node"]
    checkout = zoning["checkout_zone"]
    sales = zoning["sales_zone"]
    store_band = shell.get("store_band", "normal")
    intent = zoning.get("program_intent", "balanced")

    base_w = PRIMARY_SPINE_WIDTH_BY_BAND.get(store_band, 1.80)
    bonus = PROGRAM_INTENT_BONUS.get(intent, 0.0)
    computed_spine_w = _clamp(base_w + bonus, PRIMARY_SPINE_MIN, PRIMARY_SPINE_MAX)
    spine_w = _clamp(user_spine_width_m if user_spine_width_m is not None else computed_spine_w, PRIMARY_SPINE_MIN, PRIMARY_SPINE_MAX)

    ex, _ = _center(entrance)
    _, cy = _center(checkout)

    spine_x = _clamp(ex - spine_w / 2.0, inner["x"], inner["x"] + inner["length"] - spine_w)
    spine_y = inner["y"]
    spine_h = max(0.0, min(cy, inner["y"] + inner["width"]) - spine_y)
    spine = _rect(spine_x, spine_y, spine_w, spine_h)

    side = _spine_side(inner, spine)
    entrance_side = str(shell.get("entrance_opening", {}).get("position", side)).lower()
    secondary_w = _secondary_from_spine_width(spine_w)
    territorial_w = _territorial_from_spine_width(spine_w)

    # Service connector straddles the sales/service zoning boundary
    connector_center_y = zoning["service_lines"]["sales_to_back_y"]
    connector_y = connector_center_y - spine_w / 2.0

    if side == "center":
        connector_x = sales["x"]
        connector_len = sales["length"]
    elif side == "left":
        connector_x = spine["x"] + spine["length"]
        connector_len = max(0.0, (sales["x"] + sales["length"]) - connector_x)
    else:
        connector_x = sales["x"]
        connector_len = max(0.0, spine["x"] - sales["x"])

    service_connector = _rect(connector_x, connector_y, connector_len, spine_w)

    # --- PATCH v52: main spine stops at service connector ---
    service_top_y = service_connector["y"] + service_connector["width"]
    spine["width"] = max(0.0, service_top_y - spine["y"])

    # Dynamic secondary aisle count:
    # vertical circulation starts at the upper boundary of the frontage decomposition
    # rather than the generic entrance offset. This aligns all vertical secondary and
    # territorial aisles to end at the frontage top line.
    frontage_boundary_y = sales["y"] + min(float(entrance.get("width_m", ENTRANCE_OFFSET_DEPTH)), sales["width"])
    entrance_offset_y = max(entrance["y"] + ENTRANCE_OFFSET_DEPTH, frontage_boundary_y)
    connector_bottom_y = service_connector["y"]
    available_depth = max(0.0, connector_bottom_y - entrance_offset_y)

    secondary_aisles: List[dict] = []
    actual_spacing = 0.0
    secondary_count = 0

    if available_depth >= secondary_w + recommended_spacing_m:
        # max n such that n*secondary_w + (n+1)*recommended_spacing <= available_depth
        n = int((available_depth - recommended_spacing_m) // (secondary_w + recommended_spacing_m))
        n = max(1, n)
        while n > 0:
            needed = n * secondary_w + (n + 1) * recommended_spacing_m
            if needed <= available_depth + 1e-9:
                break
            n -= 1
        if n > 0:
            secondary_count = n
            actual_spacing = (available_depth - n * secondary_w) / (n + 1)
            # place from bottom to top between entrance offset and service connector
            y = entrance_offset_y + actual_spacing
            for _ in range(n):
                rects = _secondary_branch_rects(sales, spine, side, y, secondary_w)
                secondary_aisles.extend(rects)
                y += secondary_w + actual_spacing

    side_aisles = []
    side_y = entrance_offset_y
    side_h = max(0.0, service_connector["y"] - entrance_offset_y)
    if side_h > 0.0:
        left_x = inner["x"] + SIDE_AISLE_WALL_OFFSET
        right_x = inner["x"] + inner["length"] - SIDE_AISLE_WALL_OFFSET - secondary_w

        # Corrected rule:
        # when the spine is on one side, that same-side wall aisle is removed instead of overlapping the spine.
        if entrance_side == "left":
            side_aisles.append(_rect(right_x, side_y, secondary_w, side_h))
        elif entrance_side == "right":
            side_aisles.append(_rect(left_x, side_y, secondary_w, side_h))
        else:
            side_aisles.append(_rect(left_x, side_y, secondary_w, side_h))
            side_aisles.append(_rect(right_x, side_y, secondary_w, side_h))


    # Territorial aisles: generated independently per side between side aisles and main spine
    territorial_aisles: List[dict] = []
    territorial_secondary_aisles: List[dict] = []
    territory_logic = {"left": {}, "right": {}}
    territory_y = entrance_offset_y
    territory_h = max(0.0, service_connector["y"] - entrance_offset_y)

    if territory_h > 0.0:
        left_wall_x = inner["x"] + SIDE_AISLE_WALL_OFFSET
        right_wall_x = inner["x"] + inner["length"] - SIDE_AISLE_WALL_OFFSET - secondary_w

        # left side field
        if entrance_side == "left":
            left_field_start = left_wall_x
        else:
            left_field_start = left_wall_x + secondary_w
        left_field_end = spine["x"]
        left_terr, left_sec, left_info = _vertical_territorial_aisles(left_field_start, left_field_end, territory_y, territory_h, territorial_w, secondary_w, left_territory_mode)
        territorial_aisles.extend(left_terr)
        territorial_secondary_aisles.extend(left_sec)
        territory_logic["left"] = left_info

        # right side field
        if entrance_side == "right":
            right_field_end = right_wall_x + secondary_w
        else:
            right_field_end = right_wall_x
        right_field_start = spine["x"] + spine["length"]
        right_terr, right_sec, right_info = _vertical_territorial_aisles(right_field_start, right_field_end, territory_y, territory_h, territorial_w, secondary_w, right_territory_mode)
        territorial_aisles.extend(right_terr)
        territorial_secondary_aisles.extend(right_sec)
        territory_logic["right"] = right_info

    return {
        "primary_spine": spine,
        "service_connector": service_connector,
        "secondary_aisles": secondary_aisles,
        "side_secondary_aisles": side_aisles,
        "territorial_aisles": territorial_aisles,
        "territorial_secondary_aisles": territorial_secondary_aisles,
        "widths": {
            "primary_spine_m": round(spine_w, 3),
            "primary_spine_computed_m": round(computed_spine_w, 3),
            "primary_band_min_m": PRIMARY_SPINE_MIN,
            "primary_band_max_m": PRIMARY_SPINE_MAX,
            "secondary_aisle_m": round(secondary_w, 3),
            "secondary_band_min_m": SECONDARY_MIN,
            "secondary_band_max_m": SECONDARY_MAX,
            "service_connector_m": round(spine_w, 3),
            "territorial_aisle_m": round(territorial_w, 3),
        },
        "spacing_logic": {
            "recommended_spacing_m": round(recommended_spacing_m, 3),
            "entrance_offset_depth_m": ENTRANCE_OFFSET_DEPTH,
            "frontage_boundary_start_y_m": round(entrance_offset_y, 3),
            "start_spacing_reference_m": round(spine_w, 3),
            "available_depth_m": round(available_depth, 3),
            "actual_secondary_spacing_m": round(actual_spacing, 3),
            "secondary_aisle_count": secondary_count,
            "side_aisle_wall_offset_m": SIDE_AISLE_WALL_OFFSET,
            "side_secondary_aisle_count": 1 if entrance_side in ("left", "right") else 2,
            "same_side_aisle_alignment": "same-side wall aisle removed to avoid overlap with main spine",
            "territory_logic": territory_logic,
        },
        "anchors": {
            "start": {"x": round(ex, 6), "y": round(entrance["y"] + entrance["width"]/2.0, 6)},
            "checkout_centroid_y": round(cy, 6),
            "connector_center_y": round(connector_center_y, 6),
            "entrance_offset_y": round(entrance_offset_y, 6),
            "connector_bottom_y": round(connector_bottom_y, 6),
        },
        "spine_side": side,
        "type": "strict_straight_spine_plus_service_connector_plus_dynamic_secondary",
        "valid": spine_h > 0.0 and connector_len > 0.0,
        "messages": [] if (spine_h > 0.0 and connector_len > 0.0) else ["Main spine or service connector collapsed."],
    }

def validate_circulation(shell: Dict[str, Any], zoning: Dict[str, Any], circulation: Dict[str, Any]) -> Dict[str, Any]:
    msgs = list(circulation.get("messages", []))
    valid = bool(circulation.get("valid", False))
    sc = circulation.get("service_connector", {})
    if sc and (sc.get("length", 0) <= 0 or sc.get("width", 0) <= 0):
        valid = False
        msgs.append("Service connector collapsed.")
    for i, a in enumerate(circulation.get("secondary_aisles", []), start=1):
        if a["length"] <= 0 or a["width"] <= 0:
            valid = False
            msgs.append(f"Secondary aisle {i} collapsed.")
    for i, a in enumerate(circulation.get("territorial_aisles", []), start=1):
        if a["length"] <= 0 or a["width"] <= 0:
            valid = False
            msgs.append(f"Territorial aisle {i} collapsed.")
    return {"is_valid": valid, "messages": msgs}
