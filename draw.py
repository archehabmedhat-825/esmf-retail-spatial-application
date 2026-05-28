from __future__ import annotations

from typing import Any, Dict, List, Tuple


Rect = Dict[str, float]
Obj = Dict[str, Any]


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _rect(x: float, y: float, length: float, width: float) -> Rect:
    return {"x": float(x), "y": float(y), "length": max(0.0, float(length)), "width": max(0.0, float(width))}


def _right(r: Rect) -> float:
    return r["x"] + r["length"]


def _top(r: Rect) -> float:
    return r["y"] + r["width"]


def _center(r: Rect) -> tuple[float, float]:
    return (r["x"] + r["length"] / 2.0, r["y"] + r["width"] / 2.0)


def _rect_shape(rect: Rect, role: str, **extra: Any) -> Obj:
    obj = {
        "shape": "rect",
        "role": role,
        "draw_mode": "closed_polygon",
        **rect,
    }
    obj.update(extra)
    return obj


def _line(x1: float, y1: float, x2: float, y2: float, role: str, **extra: Any) -> Obj:
    obj = {"shape": "line", "role": role, "x1": x1, "y1": y1, "x2": x2, "y2": y2}
    obj.update(extra)
    return obj


def _text(x: float, y: float, text: str, role: str = "label", **extra: Any) -> Obj:
    obj = {"shape": "text", "role": role, "x": x, "y": y, "text": text}
    obj.update(extra)
    return obj


def _dimension(x1: float, y1: float, x2: float, y2: float, value_m: float, orientation: str, label: str = "", dim_class: str = "general", priority: int = 3) -> Obj:
    return {
        "shape": "dimension",
        "role": "dimension",
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "value_m": round(value_m, 3),
        "orientation": orientation,
        "label": label,
        "dim_class": dim_class,
        "priority": priority,
    }


def _zone_area(zone: Rect | None) -> float:
    if not zone:
        return 0.0
    return round(zone["length"] * zone["width"], 3)


def _family_graphic(role: str, item: Dict[str, Any]) -> Dict[str, Any]:
    variant = str(item.get("variant", ""))
    subfamily = str(item.get("subfamily", ""))

    if role == "display_wall":
        return {
            "graphic_class": "wall_bay",
            "internal_name": "WALL BAY",
            "lineweight": "medium",
            "hatch": "horizontal_bands",
            "pattern_class": "wall_bay_shelves",
        }
    if role == "display_gondola":
        if subfamily == "rack" or "rack" in variant:
            return {
                "graphic_class": "rack",
                "internal_name": "RACK",
                "lineweight": "medium",
                "hatch": "single_center_rail",
                "pattern_class": "rack_rail",
            }
        return {
            "graphic_class": "gondola",
            "internal_name": "GONDOLA",
            "lineweight": "medium_heavy",
            "hatch": "double_shelf_lines",
            "pattern_class": "gondola_shelves",
        }
    if role == "display_table":
        return {
            "graphic_class": "table",
            "internal_name": "TABLE",
            "lineweight": "medium",
            "hatch": "center_cross",
            "pattern_class": "table_cross",
        }
    if role == "display_mannequin":
        return {
            "graphic_class": "mannequin",
            "internal_name": "F7",
            "lineweight": "light_medium",
            "hatch": "none",
            "pattern_class": "mannequin_core",
        }
    return {"graphic_class": role, "internal_name": role.upper(), "lineweight": "medium", "hatch": "none", "pattern_class": "none"}


def _boundary_layers(shell: Dict[str, Any]) -> Dict[str, List[Obj]]:
    outer = shell.get("outer_boundary")
    inner = shell.get("inner_clear_boundary")
    entrance = shell.get("entrance_opening", {})
    length_m = float(shell.get("length_m", 0.0))
    width_m = float(shell.get("width_m", 0.0))

    wall_ext: List[Obj] = []
    wall_glass: List[Obj] = []
    openings: List[Obj] = []

    if outer and inner:
        west_t = inner["x"] - outer["x"]
        east_t = _right(outer) - _right(inner)
        south_t = inner["y"] - outer["y"]
        north_t = _top(outer) - _top(inner)

        if west_t > 0:
            wall_ext.append(_rect_shape(_rect(outer["x"], outer["y"], west_t, outer["width"]), "wall_external", side="west", lineweight="heavy"))
        if east_t > 0:
            wall_ext.append(_rect_shape(_rect(_right(inner), outer["y"], east_t, outer["width"]), "wall_external", side="east", lineweight="heavy"))
        if north_t > 0:
            wall_ext.append(_rect_shape(_rect(outer["x"], _top(inner), outer["length"], north_t), "wall_external", side="north", lineweight="heavy"))

        x1 = float(entrance.get("x1", 0.0))
        x2 = float(entrance.get("x2", 0.0))
        if south_t > 0:
            if x1 > outer["x"]:
                wall_glass.append(_rect_shape(_rect(outer["x"], outer["y"], x1 - outer["x"], south_t), "wall_glass", side="south_left", lineweight="light"))
            if x2 < _right(outer):
                wall_glass.append(_rect_shape(_rect(x2, outer["y"], _right(outer) - x2, south_t), "wall_glass", side="south_right", lineweight="light"))

        openings.append(_line(x1, outer["y"], x2, outer["y"], "entrance_opening", width_m=float(entrance.get("width_m", 0.0))))
        openings.append(_text((x1 + x2) / 2.0, outer["y"] - 0.28, "ENTRANCE OPENING", role="opening_label"))

    labels = []
    if outer:
        labels.append(_text(length_m / 2.0, outer["y"] - 0.95, "SOUTH FRONTAGE / GLASS WALL", role="title"))

    dims: List[Obj] = []
    if outer:
        dims.append(_dimension(0.0, -0.8, length_m, -0.8, length_m, "horizontal", "Store Length", dim_class="overall", priority=1))
        dims.append(_dimension(length_m + 0.8, 0.0, length_m + 0.8, width_m, width_m, "vertical", "Store Width", dim_class="overall", priority=1))
    if entrance:
        dims.append(_dimension(float(entrance.get("x1", 0.0)), -0.35, float(entrance.get("x2", 0.0)), -0.35, float(entrance.get("width_m", 0.0)), "horizontal", "Entrance Opening", dim_class="opening", priority=1))

    return {
        "WALL_EXT": wall_ext,
        "WALL_GLASS": wall_glass,
        "OPENINGS": openings,
        "LABELS": labels,
        "DIMENSIONS": dims,
        "INNER_BOUNDARY": [_rect_shape(inner, "inner_clear_boundary", lineweight="light")] if inner else [],
    }


def _line_walls_to_shapes(walls: List[Dict[str, Any]], role: str) -> List[Obj]:
    out: List[Obj] = []
    for w in walls or []:
        if all(k in w for k in ("x1", "y1", "x2", "y2")):
            out.append(_line(float(w["x1"]), float(w["y1"]), float(w["x2"]), float(w["y2"]), role, thickness=w.get("thickness"), zone=w.get("zone"), room_index=w.get("room_index"), room_kind=w.get("room_kind"), side=w.get("side")))
    return out


def _openings_to_shapes(openings: List[Dict[str, Any]]) -> List[Obj]:
    out: List[Obj] = []
    for op in openings or []:
        if all(k in op for k in ("x1", "y1", "x2", "y2")):
            out.append(_line(float(op["x1"]), float(op["y1"]), float(op["x2"]), float(op["y2"]), op.get("type", "opening"), room_index=op.get("room_index"), room_kind=op.get("room_kind"), width=op.get("width")))
    return out


def _fitting_room_shapes(fitting_rooms: List[Dict[str, Any]]) -> tuple[List[Obj], List[Obj], List[Obj]]:
    rooms: List[Obj] = []
    labels: List[Obj] = []
    dims: List[Obj] = []
    for room in fitting_rooms or []:
        if all(k in room for k in ("x", "y", "length", "width")):
            rect = _rect(room["x"], room["y"], room["length"], room["width"])
            rooms.append(_rect_shape(rect, "fitting_room", room_index=room.get("index"), room_kind=room.get("kind"), draw_mode="closed_polygon", graphic_class="fitting_room"))
            cx, cy = _center(rect)
            labels.append(_text(cx, cy, f"FIT {room.get('index', '')}", role="room_label", room_kind=room.get("kind")))
            dims.append(_dimension(room["x"], room["y"] - 0.18, room["x"] + room["length"], room["y"] - 0.18, room["length"], "horizontal", f"Fit {room.get('index', '')} L", dim_class="room", priority=2))
            dims.append(_dimension(room["x"] - 0.18, room["y"], room["x"] - 0.18, room["y"] + room["width"], room["width"], "vertical", f"Fit {room.get('index', '')} W", dim_class="room", priority=2))
    return rooms, labels, dims


def _zone_guides_and_labels(zones: Dict[str, Any]) -> tuple[List[Obj], List[Obj], List[Obj]]:
    guides: List[Obj] = []
    labels: List[Obj] = []
    dims: List[Obj] = []
    for name in ["decompression", "sales", "fitting", "checkout", "back_of_house"]:
        z = zones.get(name)
        if isinstance(z, dict) and all(k in z for k in ("x", "y", "length", "width")):
            guides.append(_rect_shape(z, "zone_guide", zone=name, lineweight="light"))
            cx, cy = _center(z)
            labels.append(_text(cx, cy, f"{name.replace('_', ' ').title()}\n{_zone_area(z):.1f} m²", role="zone_label", zone=name))
            if name in {"fitting", "checkout", "back_of_house"}:
                dims.append(_dimension(z["x"], z["y"] - 0.24, z["x"] + z["length"], z["y"] - 0.24, z["length"], "horizontal", f"{name.title()} L", dim_class="zone", priority=2))
                dims.append(_dimension(z["x"] - 0.24, z["y"], z["x"] - 0.24, z["y"] + z["width"], z["width"], "vertical", f"{name.title()} W", dim_class="zone", priority=2))
    return guides, labels, dims


def _fixture_dimensions(rect: Rect, family_name: str, dim_class: str = "fixture", priority: int = 4) -> List[Obj]:
    return [
        _dimension(rect["x"], rect["y"] - 0.12, rect["x"] + rect["length"], rect["y"] - 0.12, rect["length"], "horizontal", f"{family_name} L", dim_class=dim_class, priority=priority),
        _dimension(rect["x"] - 0.12, rect["y"], rect["x"] - 0.12, rect["y"] + rect["width"], rect["width"], "vertical", f"{family_name} W", dim_class=dim_class, priority=priority),
    ]


def _pattern_lines_for_rect(rect: Rect, graphic: Dict[str, Any]) -> List[Obj]:
    x, y, l, w = rect["x"], rect["y"], rect["length"], rect["width"]
    lines: List[Obj] = []
    pattern_class = graphic.get("pattern_class", "none")
    if pattern_class == "wall_bay_shelves":
        for frac in (0.30, 0.60):
            yy = y + w * frac
            lines.append(_line(x + l * 0.15, yy, x + l * 0.85, yy, "fixture_pattern", pattern_class=pattern_class, graphic_class=graphic.get("graphic_class")))
    elif pattern_class == "gondola_shelves":
        for frac in (0.33, 0.66):
            yy = y + w * frac
            lines.append(_line(x + l * 0.10, yy, x + l * 0.90, yy, "fixture_pattern", pattern_class=pattern_class, graphic_class=graphic.get("graphic_class")))
    elif pattern_class == "rack_rail":
        yy = y + w * 0.50
        lines.append(_line(x + l * 0.15, yy, x + l * 0.85, yy, "fixture_pattern", pattern_class=pattern_class, graphic_class=graphic.get("graphic_class")))
        lines.append(_line(x + l * 0.50, y + w * 0.25, x + l * 0.50, y + w * 0.75, "fixture_pattern", pattern_class=pattern_class, graphic_class=graphic.get("graphic_class")))
    elif pattern_class == "table_cross":
        lines.append(_line(x + l * 0.20, y + w * 0.20, x + l * 0.80, y + w * 0.80, "fixture_pattern", pattern_class=pattern_class, graphic_class=graphic.get("graphic_class")))
        lines.append(_line(x + l * 0.80, y + w * 0.20, x + l * 0.20, y + w * 0.80, "fixture_pattern", pattern_class=pattern_class, graphic_class=graphic.get("graphic_class")))
    elif pattern_class == "mannequin_core":
        core = _rect_shape(_rect(x + l * 0.35, y + w * 0.35, l * 0.30, w * 0.30), "fixture_pattern_rect", pattern_class=pattern_class, graphic_class=graphic.get("graphic_class"))
        lines.append(core)
    return lines


def _display_rects(items: List[Dict[str, Any]], role: str) -> tuple[List[Obj], List[Obj], List[Obj], List[Obj]]:
    rects: List[Obj] = []
    labels: List[Obj] = []
    dims: List[Obj] = []
    patterns: List[Obj] = []
    for i, item in enumerate(items or [], start=1):
        if all(k in item for k in ("x", "y", "length", "width")):
            rect = _rect(item["x"], item["y"], item["length"], item["width"])
            graphic = _family_graphic(role, item)
            rects.append(_rect_shape(rect, role, variant=item.get("variant"), orientation=item.get("orientation"), host_quality=item.get("host_quality"), lane_index=item.get("lane_index"), subfamily=item.get("subfamily"), **graphic))
            patterns.extend(_pattern_lines_for_rect(rect, graphic))
            cx, cy = _center(rect)
            labels.append(_text(cx, cy, graphic["internal_name"], role="fixture_label", graphic_class=graphic["graphic_class"]))
            if i <= 2:
                dims.extend(_fixture_dimensions(rect, graphic["internal_name"], dim_class="fixture", priority=4))
    return rects, labels, dims, patterns


def _path_shapes(paths: List[Dict[str, Any]]) -> tuple[List[Obj], List[Obj], List[Obj]]:
    path_rects: List[Obj] = []
    labels: List[Obj] = []
    dims: List[Obj] = []
    for idx, path in enumerate(paths or [], start=1):
        if all(k in path for k in ("x", "y", "length", "width")):
            path_rects.append(_rect_shape(path, "protected_path", path_index=idx, lineweight="light_medium", hatch="path_outline"))
            cx, cy = _center(path)
            labels.append(_text(cx, cy, f"MAIN AISLE" if idx == 1 else f"PATH {idx}", role="path_label"))
            dims.append(_dimension(path["x"] - 0.22, path["y"], path["x"] - 0.22, path["y"] + path["width"], path["width"], "vertical", f"Path {idx} W", dim_class="aisle", priority=2 if idx == 1 else 3))
    return path_rects, labels, dims


def _summary_labels(state) -> List[Obj]:
    shell = state.shell or {}
    display_summary = (state.display or {}).get("summary", {})
    fitting_meta = (state.walls_internal or {}).get("fitting_meta", {})

    x = 0.0
    y = float(shell.get("width_m", 0.0)) + 1.1
    lines = [
        f"Baseline Status: {state.status}",
        f"Display Counts — Wall: {display_summary.get('wall_count', 0)}, Gondola/Rack: {display_summary.get('gondola_count', 0)}, Tables: {display_summary.get('table_count', 0)}, Mannequins: {display_summary.get('mannequin_count', 0)}",
        f"Fitting Layout: {fitting_meta.get('layout_mode', 'n/a')} | Min Rooms: {fitting_meta.get('min_rooms', 'n/a')} | Side: {fitting_meta.get('side', 'n/a')}",
    ]
    return [_text(x, y + i * 0.35, line, role="summary") for i, line in enumerate(lines)]


def assemble_baseline_drawing_objects(state, params: dict) -> dict:
    shell_layers = _boundary_layers(state.shell or {})

    wall_boh = _line_walls_to_shapes(_as_list((state.walls_internal or {}).get("boh")), "wall_boh")
    wall_fit = _line_walls_to_shapes(_as_list((state.walls_internal or {}).get("fitting")), "wall_fitting")
    opening_shapes = shell_layers["OPENINGS"] + _openings_to_shapes(_as_list((state.walls_internal or {}).get("openings")))

    fitting_rooms, fitting_labels, fitting_dims = _fitting_room_shapes(_as_list((state.walls_internal or {}).get("fitting_rooms")))
    zone_guides, zone_labels, zone_dims = _zone_guides_and_labels(state.zones or {})

    wall_rects, wall_labels, wall_dims, wall_patterns = _display_rects(_as_list((state.display or {}).get("wall")), "display_wall")
    gondola_rects, gondola_labels, gondola_dims, gondola_patterns = _display_rects(_as_list((state.display or {}).get("gondola")), "display_gondola")
    table_rects, table_labels, table_dims, table_patterns = _display_rects(_as_list((state.display or {}).get("table")), "display_table")
    mannequin_rects, mannequin_labels, mannequin_dims, mannequin_patterns = _display_rects(_as_list((state.display or {}).get("mannequin")), "display_mannequin")

    path_rects, path_labels, path_dims = _path_shapes(_as_list((state.display or {}).get("circulation", {}).get("protected_paths", [])))

    labels = (
        shell_layers["LABELS"]
        + zone_labels
        + fitting_labels
        + wall_labels
        + gondola_labels
        + table_labels
        + mannequin_labels
        + path_labels
        + _summary_labels(state)
    )

    dimensions = shell_layers["DIMENSIONS"] + zone_dims + fitting_dims + path_dims + wall_dims + gondola_dims + table_dims

    drawing = {
        "WALL_EXT": shell_layers["WALL_EXT"],
        "WALL_GLASS": shell_layers["WALL_GLASS"],
        "INNER_BOUNDARY": shell_layers["INNER_BOUNDARY"],
        "WALL_BOH": wall_boh,
        "WALL_FITTING": wall_fit,
        "OPENINGS": opening_shapes,
        "FITTING_ROOMS": fitting_rooms,
        "DISPLAY_WALL": wall_rects,
        "DISPLAY_GONDOLA": gondola_rects,
        "DISPLAY_TABLE": table_rects,
        "DISPLAY_MANNEQUIN": mannequin_rects,
        "GRAPHIC_PATTERNS": wall_patterns + gondola_patterns + table_patterns + mannequin_patterns,
        "PATHS": path_rects,
        "ZONE_GUIDES": zone_guides,
        "DIMENSIONS": dimensions,
        "LABELS": labels,
        "DRAWING_SUMMARY": [{
            "overall_length_m": round(float((state.shell or {}).get("length_m", 0.0)), 3),
            "overall_width_m": round(float((state.shell or {}).get("width_m", 0.0)), 3),
            "zone_count": len([k for k, v in (state.zones or {}).items() if not k.startswith("_") and isinstance(v, dict)]),
            "fitting_room_count": len(_as_list((state.walls_internal or {}).get("fitting_rooms"))),
            "display_counts": (state.display or {}).get("summary", {}),
            "dimension_hierarchy": {
                "overall": 1,
                "opening": 1,
                "zone": 2,
                "room": 2,
                "aisle": 2,
                "fixture": 4,
            },
        }],
    }
    return drawing
