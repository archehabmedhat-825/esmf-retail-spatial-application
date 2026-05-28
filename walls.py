from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

Rect = Dict[str, float]
Wall = Dict[str, Any]
Opening = Dict[str, Any]

# ---------------------------------------------------------------------
# Basic rectangle helpers (normalized schema: x, y, length, width)
# ---------------------------------------------------------------------

def make_rect(x: float, y: float, length: float, width: float) -> Rect:
    return {"x": float(x), "y": float(y), "length": max(0.0, float(length)), "width": max(0.0, float(width))}


def rect_area(r: Optional[Rect]) -> float:
    if not r:
        return 0.0
    return r["length"] * r["width"]


def rect_right(r: Rect) -> float:
    return r["x"] + r["length"]


def rect_top(r: Rect) -> float:
    return r["y"] + r["width"]


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _get(params: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = params
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def choose_store_size_band(area_m2: float) -> str:
    if area_m2 < 80:
        return "micro"
    if area_m2 < 150:
        return "small"
    if area_m2 < 300:
        return "normal"
    if area_m2 < 600:
        return "large"
    return "xl"


def minimum_fitting_room_count(area_m2: float, params: Dict[str, Any]) -> int:
    area = float(area_m2)
    if area < 80.0:
        return 1
    if area < 120.0:
        return 1
    if area < 150.0:
        return 2
    if area < 225.0:
        return 3
    if area < 300.0:
        return 4
    if area < 450.0:
        return 5
    if area <= 600.0:
        return 6
    if area < 700.0:
        return 7
    if area < 800.0:
        return 8
    if area < 900.0:
        return 9
    return 10


def resolve_fitting_room_preset(area_m2: float, inputs: Dict[str, Any], params: Dict[str, Any]) -> str:
    preset = str(inputs.get("fitting_room_size_preset", "standard"))
    band = choose_store_size_band(area_m2)
    if preset == "compact" and band != "micro":
        return "standard"
    if preset not in {"compact", "standard", "accessible"}:
        return "standard"
    return preset


def standard_room_size_for_band(area_m2: float, params: Dict[str, Any], preset: str = "standard") -> Tuple[float, float]:
    band = choose_store_size_band(area_m2)
    if preset == "compact" and band == "micro":
        return (
            float(_get(params, "fitting", "micro_room_width_m", default=1.20)),
            float(_get(params, "fitting", "micro_room_depth_m", default=1.20)),
        )
    if preset == "accessible":
        return accessible_room_size(params)
    return (
        float(_get(params, "fitting", "standard_room_width_m", default=1.20)),
        float(_get(params, "fitting", "standard_room_depth_m", default=1.50)),
    )


def accessible_room_size(params: Dict[str, Any]) -> Tuple[float, float]:
    return (
        float(_get(params, "fitting", "accessible_room_width_m", default=1.50)),
        float(_get(params, "fitting", "accessible_room_depth_m", default=1.50)),
    )


def fitting_partition_thickness(params: Dict[str, Any]) -> float:
    return float(_get(params, "walls", "fitting_partition_thickness_m", default=params.get("wall_thickness_fitting_m", 0.10)))


def fitting_curtain_opening_width(params: Dict[str, Any]) -> float:
    return float(_get(params, "fitting", "curtain_opening_width_m", default=0.90))


def fitting_waiting_buffer_depth(params: Dict[str, Any]) -> float:
    return float(_get(params, "fitting", "waiting_buffer_depth_m", default=1.00))


def fitting_internal_access_gap(params: Dict[str, Any]) -> float:
    return float(_get(params, "fitting", "internal_access_gap_m", default=1.00))


def build_zone_enclosure_walls(zone: Rect, thickness: float, opening_mode: str, params: Dict[str, Any]) -> List[Wall]:
    x, y, length, width = zone["x"], zone["y"], zone["length"], zone["width"]
    return [
        {"type": "wall", "zone": "boh", "side": "south", "x1": x, "y1": y, "x2": x + length, "y2": y, "thickness": thickness},
        {"type": "wall", "zone": "boh", "side": "north", "x1": x, "y1": y + width, "x2": x + length, "y2": y + width, "thickness": thickness},
        {"type": "wall", "zone": "boh", "side": "west", "x1": x, "y1": y, "x2": x, "y2": y + width, "thickness": thickness},
        {"type": "wall", "zone": "boh", "side": "east", "x1": x + length, "y1": y, "x2": x + length, "y2": y + width, "thickness": thickness},
    ]


def subdivide_fitting_zone_into_rooms(fitting_zone: Rect, store_area_m2: float, params: Dict[str, Any], fitting_room_size_preset: str = "standard", side_hint: str = "auto") -> Dict[str, Any]:
    band = choose_store_size_band(store_area_m2)
    min_rooms = minimum_fitting_room_count(store_area_m2, params)
    std_length, std_width = standard_room_size_for_band(store_area_m2, params, fitting_room_size_preset)
    acc_length, acc_width = accessible_room_size(params)
    partition_t = fitting_partition_thickness(params)
    waiting_d = fitting_waiting_buffer_depth(params)
    internal_gap = fitting_internal_access_gap(params)
    zone_x, zone_y = fitting_zone["x"], fitting_zone["y"]
    zone_length, zone_width = fitting_zone["length"], fitting_zone["width"]
    require_accessible = band in {"normal", "large", "xl"}
    room_specs: List[Dict[str, Any]] = []
    if require_accessible:
        room_specs.append({"kind": "accessible", "length": acc_length, "width": acc_width})
        for _ in range(max(0, min_rooms - 1)):
            room_specs.append({"kind": "standard", "length": std_length, "width": std_width})
    else:
        for _ in range(min_rooms):
            room_specs.append({"kind": "standard", "length": std_length, "width": std_width})
    side = side_hint if side_hint in {"left", "right"} else ("left" if zone_x <= 0.75 else "right")
    usable_y = zone_y + waiting_d
    usable_width = max(0.0, zone_width - waiting_d)
    one_row = _try_pack_one_row(zone_x, usable_y, zone_length, usable_width, room_specs, partition_t, side)
    if one_row["fits"]:
        return {"rooms": one_row["rooms"], "layout_mode": "one_row", "waiting_buffer": make_rect(zone_x, zone_y, zone_length, waiting_d), "side": side, "min_rooms": min_rooms, "store_band": band, "room_size_preset": fitting_room_size_preset}
    two_row = _try_pack_two_rows(zone_x, usable_y, zone_length, usable_width, room_specs, partition_t, internal_gap, side)
    if two_row["fits"]:
        return {"rooms": two_row["rooms"], "layout_mode": "two_row", "waiting_buffer": make_rect(zone_x, zone_y, zone_length, waiting_d), "side": side, "min_rooms": min_rooms, "store_band": band, "room_size_preset": fitting_room_size_preset}
    return {"rooms": [], "layout_mode": "failed", "waiting_buffer": make_rect(zone_x, zone_y, zone_length, waiting_d), "side": side, "min_rooms": min_rooms, "store_band": band, "room_size_preset": fitting_room_size_preset, "failure_reason": "fitting_zone_too_small_for_minimum_room_layout"}


def _try_pack_one_row(zone_x: float, usable_y: float, zone_length: float, usable_width: float, room_specs: List[Dict[str, Any]], partition_t: float, side: str) -> Dict[str, Any]:
    max_room_width = max(spec["width"] for spec in room_specs) if room_specs else 0.0
    total_length = sum(spec["length"] for spec in room_specs) + partition_t * max(0, len(room_specs) - 1)
    if max_room_width > usable_width or total_length > zone_length:
        return {"fits": False, "rooms": []}
    rooms: List[Rect] = []
    cursor_x = zone_x if side == "left" else zone_x + zone_length - total_length
    for i, spec in enumerate(room_specs):
        room = make_rect(cursor_x, usable_y, spec["length"], spec["width"])
        room["kind"] = spec["kind"]
        room["index"] = i + 1
        rooms.append(room)
        cursor_x += spec["length"] + partition_t
    return {"fits": True, "rooms": rooms}


def _try_pack_two_rows(zone_x: float, usable_y: float, zone_length: float, usable_width: float, room_specs: List[Dict[str, Any]], partition_t: float, internal_gap: float, side: str) -> Dict[str, Any]:
    if not room_specs:
        return {"fits": True, "rooms": []}
    split_idx = (len(room_specs) + 1) // 2
    row1_specs = room_specs[:split_idx]
    row2_specs = room_specs[split_idx:]
    row1_width = max(spec["width"] for spec in row1_specs) if row1_specs else 0.0
    row2_width = max(spec["width"] for spec in row2_specs) if row2_specs else 0.0
    total_width = row1_width + internal_gap + row2_width
    row1_length = sum(spec["length"] for spec in row1_specs) + partition_t * max(0, len(row1_specs) - 1)
    row2_length = sum(spec["length"] for spec in row2_specs) + partition_t * max(0, len(row2_specs) - 1)
    if total_width > usable_width or max(row1_length, row2_length) > zone_length:
        return {"fits": False, "rooms": []}
    rooms: List[Rect] = []
    row1_x = zone_x if side == "left" else zone_x + zone_length - row1_length
    cursor_x = row1_x
    for i, spec in enumerate(row1_specs):
        room = make_rect(cursor_x, usable_y, spec["length"], spec["width"])
        room["kind"] = spec["kind"]
        room["index"] = i + 1
        rooms.append(room)
        cursor_x += spec["length"] + partition_t
    row2_y = usable_y + row1_width + internal_gap
    row2_x = zone_x if side == "left" else zone_x + zone_length - row2_length
    cursor_x = row2_x
    for j, spec in enumerate(row2_specs):
        room = make_rect(cursor_x, row2_y, spec["length"], spec["width"])
        room["kind"] = spec["kind"]
        room["index"] = len(row1_specs) + j + 1
        rooms.append(room)
        cursor_x += spec["length"] + partition_t
    return {"fits": True, "rooms": rooms}


def build_fitting_room_partitions(fitting_rooms_layout: Dict[str, Any], thickness: float, opening_mode: str, params: Dict[str, Any]) -> List[Wall]:
    if fitting_rooms_layout.get("layout_mode") == "failed":
        return []
    curtain_length = fitting_curtain_opening_width(params)
    walls: List[Wall] = []
    for room in fitting_rooms_layout["rooms"]:
        x, y, length, width = room["x"], room["y"], room["length"], room["width"]
        walls.append({"type": "wall", "zone": "fitting", "room_index": room["index"], "room_kind": room["kind"], "side": "west", "x1": x, "y1": y, "x2": x, "y2": y + width, "thickness": thickness})
        walls.append({"type": "wall", "zone": "fitting", "room_index": room["index"], "room_kind": room["kind"], "side": "east", "x1": x + length, "y1": y, "x2": x + length, "y2": y + width, "thickness": thickness})
        walls.append({"type": "wall", "zone": "fitting", "room_index": room["index"], "room_kind": room["kind"], "side": "north", "x1": x, "y1": y + width, "x2": x + length, "y2": y + width, "thickness": thickness})
        open_len = min(curtain_length, length * 0.80)
        left_seg = (length - open_len) / 2.0
        right_seg = left_seg
        if left_seg > 0:
            walls.append({"type": "wall", "zone": "fitting", "room_index": room["index"], "room_kind": room["kind"], "side": "south_left", "x1": x, "y1": y, "x2": x + left_seg, "y2": y, "thickness": thickness})
        if right_seg > 0:
            walls.append({"type": "wall", "zone": "fitting", "room_index": room["index"], "room_kind": room["kind"], "side": "south_right", "x1": x + length - right_seg, "y1": y, "x2": x + length, "y2": y, "thickness": thickness})
    return walls


def extract_fitting_curtain_openings(fitting_rooms_layout: Dict[str, Any], params: Dict[str, Any]) -> List[Opening]:
    if fitting_rooms_layout.get("layout_mode") == "failed":
        return []
    curtain_length = fitting_curtain_opening_width(params)
    openings: List[Opening] = []
    for room in fitting_rooms_layout["rooms"]:
        x, y, length = room["x"], room["y"], room["length"]
        open_len = min(curtain_length, length * 0.80)
        ox = x + (length - open_len) / 2.0
        openings.append({"type": "curtain_opening", "zone": "fitting", "room_index": room["index"], "room_kind": room["kind"], "x1": ox, "y1": y, "x2": ox + open_len, "y2": y, "length": open_len})
    return openings


def generate_internal_walls(zones: Dict[str, Any], inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    walls = {"boh": [], "fitting": [], "openings": [], "fitting_rooms": [], "fitting_meta": {}}
    boh_zone = zones.get("back_of_house")
    if boh_zone:
        walls["boh"] = build_zone_enclosure_walls(boh_zone, float(_get(params, "walls", "boh_internal_thickness_m", default=0.12)), "standard_opening", params)
    fitting_zone = zones.get("fitting")
    store_area_m2 = float(zones.get("_meta", {}).get("store_area_m2", inputs.get("area_m2", 0.0)))
    if fitting_zone:
        layout = subdivide_fitting_zone_into_rooms(fitting_zone, store_area_m2, params, resolve_fitting_room_preset(store_area_m2, inputs, params), inputs.get("fitting_position", "auto"))
        walls["fitting_rooms"] = layout.get("rooms", [])
        walls["fitting_meta"] = {"layout_mode": layout.get("layout_mode"), "store_band": layout.get("store_band"), "min_rooms": layout.get("min_rooms"), "waiting_buffer": layout.get("waiting_buffer"), "side": layout.get("side"), "room_size_preset": layout.get("room_size_preset"), "failure_reason": layout.get("failure_reason")}
        walls["fitting"] = build_fitting_room_partitions(layout, float(_get(params, "walls", "fitting_partition_thickness_m", default=0.10)), "curtain_gap", params)
        walls["openings"].extend(extract_fitting_curtain_openings(layout, params))
    return walls
