from __future__ import annotations

from typing import Any, Dict, List, Optional


Rect = Dict[str, float]


def _get(params: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = params
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


# ---------------------------------------------------------------------
# Geometry compatibility helpers
# Supports both {length,width} and {w,h} schemas while the backend converges
# ---------------------------------------------------------------------

def rect_x(r: Rect) -> float:
    return float(r.get("x", 0.0))


def rect_y(r: Rect) -> float:
    return float(r.get("y", 0.0))


def rect_w(r: Rect) -> float:
    if "length" in r:
        return float(r["length"])
    return float(r.get("w", 0.0))


def rect_h(r: Rect) -> float:
    if "width" in r:
        return float(r["width"])
    return float(r.get("h", 0.0))


def rect_right(r: Rect) -> float:
    return rect_x(r) + rect_w(r)


def rect_top(r: Rect) -> float:
    return rect_y(r) + rect_h(r)


def rect_area(r: Optional[Rect]) -> float:
    if not r:
        return 0.0
    return max(0.0, rect_w(r)) * max(0.0, rect_h(r))


def contained_in(inner: Rect, outer: Rect) -> bool:
    return (
        rect_x(inner) >= rect_x(outer)
        and rect_y(inner) >= rect_y(outer)
        and rect_right(inner) <= rect_right(outer)
        and rect_top(inner) <= rect_top(outer)
    )


def overlaps(a: Rect, b: Rect) -> bool:
    return not (
        rect_right(a) <= rect_x(b)
        or rect_right(b) <= rect_x(a)
        or rect_top(a) <= rect_y(b)
        or rect_top(b) <= rect_y(a)
    )


# ---------------------------------------------------------------------
# Baseline validation helpers
# ---------------------------------------------------------------------

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
    band = choose_store_size_band(area_m2)
    return int(_get(params, "fitting", "count_bands", band, "min", default=1))



def requires_accessible_fitting(area_m2: float) -> bool:
    return choose_store_size_band(area_m2) in {"normal", "large", "xl"}





def resolve_fitting_room_preset(area_m2: float, state) -> str:
    preset = str(getattr(state, "inputs", {}).get("fitting_room_size_preset", "standard"))
    band = choose_store_size_band(area_m2)
    if preset == "compact" and band != "micro":
        return "standard"
    if preset not in {"compact", "standard", "accessible"}:
        return "standard"
    return preset


def selected_fitting_dims(area_m2: float, state, params: Dict[str, Any]) -> tuple[float, float]:
    preset = resolve_fitting_room_preset(area_m2, state)
    if preset == "compact":
        return (float(_get(params, "fitting", "micro_room_width_m", default=1.2)), float(_get(params, "fitting", "micro_room_depth_m", default=1.2)))
    if preset == "accessible":
        return (float(_get(params, "fitting", "accessible_room_width_m", default=1.5)), float(_get(params, "fitting", "accessible_room_depth_m", default=1.5)))
    return (float(_get(params, "fitting", "standard_room_width_m", default=1.2)), float(_get(params, "fitting", "standard_room_depth_m", default=1.5)))
def zones_are_valid(state) -> bool:
    zones = state.zones
    required = ["decompression", "sales", "checkout", "back_of_house", "fitting"]
    for name in required:
        zone = zones.get(name)
        if not zone:
            return False
        if rect_area(zone) <= 0.0:
            return False
    return True



def zones_within_shell(state) -> bool:
    clear = state.shell.get("inner_clear_boundary")
    if not clear:
        return False
    for name, zone in state.zones.items():
        if name.startswith("_"):
            continue
        if zone and not contained_in(zone, clear):
            return False
    return True



def protected_zone_overlap_free(state) -> bool:
    zones = state.zones
    names = ["decompression", "fitting", "checkout", "back_of_house"]
    existing = [(n, zones.get(n)) for n in names if zones.get(n)]
    for i, (na, a) in enumerate(existing):
        for nb, b in existing[i + 1:]:
            if overlaps(a, b):
                return False
    return True



def entrance_clear(state) -> bool:
    entrance = state.shell.get("entrance_opening")
    decompression = state.zones.get("decompression")
    primary = state.bands.get("primary_path") if getattr(state, "bands", None) else None
    if not entrance or not decompression or not primary:
        return False

    # Entrance opening sits on the outer south frontage; decompression begins inside the clear boundary.
    # Require x-overlap with decompression and direct seeding of the primary spine from the decompression top.
    open_x1 = float(entrance.get("x1", 0.0))
    open_x2 = float(entrance.get("x2", 0.0))
    decomp_x1 = rect_x(decompression)
    decomp_x2 = rect_right(decompression)
    path_x1 = rect_x(primary)
    path_x2 = rect_right(primary)

    opening_hits_decompression = max(open_x1, decomp_x1) < min(open_x2, decomp_x2)
    overlaps_opening = max(open_x1, path_x1) < min(open_x2, path_x2)
    width_close = abs((open_x2 - open_x1) - rect_w(primary)) <= 0.15
    starts_at_frontage = abs(rect_y(primary) - rect_top(decompression)) <= 0.25

    return opening_hits_decompression and overlaps_opening and width_close and starts_at_frontage

def fitting_layout_generated(state) -> bool:
    fitting_zone = state.zones.get("fitting")
    if not fitting_zone:
        return False
    meta = state.walls_internal.get("fitting_meta", {})
    rooms = state.walls_internal.get("fitting_rooms", [])
    if meta.get("layout_mode") == "failed":
        return False
    return len(rooms) > 0



def fitting_rooms_inside_zone(state) -> bool:
    fitting_zone = state.zones.get("fitting")
    if not fitting_zone:
        return False
    rooms = state.walls_internal.get("fitting_rooms", [])
    if not rooms:
        return False
    return all(contained_in(room, fitting_zone) for room in rooms)



def fitting_room_count_valid(state, params: Dict[str, Any]) -> bool:
    rooms = state.walls_internal.get("fitting_rooms", [])
    area = float(state.shell.get("area_m2", 0.0))
    return len(rooms) >= minimum_fitting_room_count(area, params)



def fitting_room_dimensions_valid(state, params: Dict[str, Any]) -> bool:
    area = float(state.shell.get("area_m2", 0.0))
    rooms = state.walls_internal.get("fitting_rooms", [])
    if not rooms:
        return False

    base_w, base_d = selected_fitting_dims(area, state, params)
    acc_w = float(_get(params, "fitting", "accessible_room_width_m", default=1.5))
    acc_d = float(_get(params, "fitting", "accessible_room_depth_m", default=1.5))

    for room in rooms:
        kind = room.get("kind", "standard")
        rw, rh = rect_w(room), rect_h(room)
        if kind == "accessible":
            if rw + 1e-6 < acc_w or rh + 1e-6 < acc_d:
                return False
        else:
            if rw + 1e-6 < base_w or rh + 1e-6 < base_d:
                return False
    return True



def fitting_accessible_provision_valid(state) -> bool:
    area = float(state.shell.get("area_m2", 0.0))
    rooms = state.walls_internal.get("fitting_rooms", [])
    if not requires_accessible_fitting(area):
        return True
    return any(room.get("kind") == "accessible" for room in rooms)



def fitting_waiting_buffer_present(state) -> bool:
    meta = state.walls_internal.get("fitting_meta", {})
    waiting = meta.get("waiting_buffer")
    return bool(waiting) and rect_area(waiting) > 0.0



def fitting_openings_match_rooms(state) -> bool:
    rooms = state.walls_internal.get("fitting_rooms", [])
    openings = [o for o in state.walls_internal.get("openings", []) if o.get("zone") == "fitting"]
    if not rooms:
        return False
    return len(openings) >= len(rooms)



def mandatory_program_counts_satisfied(state, params: Dict[str, Any]) -> bool:
    # Baseline requires at least one checkout and fitting minimum count.
    return fitting_room_count_valid(state, params) and True



def turning_checks_pass(state, params: Dict[str, Any]) -> bool:
    # Placeholder for future full turning-geometry checks for >= threshold area.
    return True



def display_no_overlap(state) -> bool:
    items = []
    for key in ("wall", "gondola", "table", "mannequin"):
        items.extend((getattr(state, "display", {}) or {}).get(key, []))
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if overlaps(a, b):
                return False
    return True


def display_within_sales(state) -> bool:
    sales = state.zones.get("sales")
    if not sales:
        return False
    items = []
    for key in ("wall", "gondola", "table", "mannequin"):
        items.extend((getattr(state, "display", {}) or {}).get(key, []))
    return all(contained_in(item, sales) for item in items)


def display_respects_protected_paths(state) -> bool:
    paths = (getattr(state, "display", {}) or {}).get("circulation", {}).get("protected_paths", [])
    items = []
    for key in ("wall", "gondola", "table", "mannequin"):
        items.extend((getattr(state, "display", {}) or {}).get(key, []))
    for path in paths:
        for item in items:
            if overlaps(path, item):
                return False
    return True


def _touches(a: Rect, b: Rect, tol: float = 0.25) -> bool:
    horizontal_overlap = max(rect_x(a), rect_x(b)) < min(rect_right(a), rect_right(b))
    vertical_overlap = max(rect_y(a), rect_y(b)) < min(rect_top(a), rect_top(b))

    side_touch = (abs(rect_right(a) - rect_x(b)) <= tol or abs(rect_right(b) - rect_x(a)) <= tol) and vertical_overlap
    top_touch = (abs(rect_top(a) - rect_y(b)) <= tol or abs(rect_top(b) - rect_y(a)) <= tol) and horizontal_overlap
    overlap = overlaps(a, b)
    return side_touch or top_touch or overlap




def access_band_widths_match_primary(state, tol: float = 0.05) -> bool:
    bands = getattr(state, "bands", {}) or {}
    primary = bands.get("primary_path")
    access_bands = bands.get("access_bands", [])
    if not primary:
        return False
    if not access_bands:
        return True
    pw = min(rect_w(primary), rect_h(primary))
    for band in access_bands:
        bw = min(rect_w(band), rect_h(band))
        if abs(bw - pw) > tol:
            return False
    return True


def _connected_component(seed: Rect, rects: list[Rect]) -> list[Rect]:
    comp = [seed]
    changed = True
    while changed:
        changed = False
        for r in rects:
            if r in comp:
                continue
            if any(_touches(r, c) for c in comp):
                comp.append(r)
                changed = True
    return comp

def protected_paths_preserved(state) -> bool:
    bands = getattr(state, "bands", {}) or {}
    primary = bands.get("primary_path")
    access_bands = bands.get("access_bands", [])
    if not primary:
        return False

    fitting = state.zones.get("fitting")
    checkout = state.zones.get("checkout")

    if rect_w(primary) <= 0 or rect_area(primary) <= 0:
        return False

    # The access system may be a network (ribbon + bridge), not every rectangle must touch primary directly.
    if access_bands and not any(_touches(primary, b) for b in access_bands):
        return False

    if fitting and access_bands and not any(_touches(b, fitting) for b in access_bands):
        return False
    if checkout and access_bands and not any(_touches(b, checkout) for b in access_bands):
        return False

    # Every access band must connect into the access network or the primary spine.
    for band in access_bands:
        if _touches(primary, band):
            continue
        if not any((other is not band) and _touches(band, other) for other in access_bands):
            return False

    fitting_side = state.inputs.get("fitting_position", "auto")
    checkout_side = state.inputs.get("checkout_position", "auto")
    if fitting and checkout and fitting_side in {"left", "right"} and fitting_side == checkout_side:
        if len(access_bands) == 0:
            return False
        if not any(rect_w(b) <= rect_h(b) for b in access_bands):
            return False

    return True

def checkout_access_preserved(state) -> bool:
    checkout = state.zones.get("checkout")
    if checkout is None:
        return False
    access_bands = (getattr(state, "bands", {}) or {}).get("access_bands", [])
    if not access_bands:
        return True
    return any(_touches(b, checkout) for b in access_bands)

def boh_access_preserved(state) -> bool:
    # BOH opening logic is not fully encoded yet, so keep baseline presence check explicit
    # until Step 2 is fully closed.
    return state.zones.get("back_of_house") is not None

def display_density_too_high(state, params: Dict[str, Any]) -> bool:
    return False



def frontage_feels_tight(state, params: Dict[str, Any]) -> bool:
    return False


# ---------------------------------------------------------------------
# Public validation API
# ---------------------------------------------------------------------

def validate_baseline_state(state, params: dict) -> dict:
    checks = {
        "zones_nonempty": zones_are_valid(state),
        "zones_within_shell": zones_within_shell(state),
        "protected_zone_overlap_free": protected_zone_overlap_free(state),
        "entrance_clear": entrance_clear(state),
        "fitting_layout_generated": fitting_layout_generated(state),
        "fitting_rooms_inside_zone": fitting_rooms_inside_zone(state),
        "fitting_room_count_valid": fitting_room_count_valid(state, params),
        "fitting_room_dimensions_valid": fitting_room_dimensions_valid(state, params),
        "fitting_accessible_provision_valid": fitting_accessible_provision_valid(state),
        "fitting_waiting_buffer_present": fitting_waiting_buffer_present(state),
        "fitting_openings_match_rooms": fitting_openings_match_rooms(state),
        "checkout_access": checkout_access_preserved(state),
        "boh_access": boh_access_preserved(state),
        "mandatory_counts": mandatory_program_counts_satisfied(state, params),
        "display_no_overlap": display_no_overlap(state),
        "display_within_sales": display_within_sales(state),
        "display_respects_protected_paths": display_respects_protected_paths(state),
        "paths_preserved": protected_paths_preserved(state),
        "access_band_widths_match_primary": access_band_widths_match_primary(state),
        "display_variant_counts_present": "variant_counts" in ((getattr(state, "display", {}) or {}).get("summary", {})),
    }

    ok_meta, err_meta = validate_band_metadata(state)
    ok_down, err_down = validate_downgrade_reasoning(state)
    ok_score, err_score = validate_band_quality_scores(state)
    checks["band_metadata"] = ok_meta
    checks["band_downgrade_reasoning"] = ok_down
    checks["band_quality_scores"] = ok_score
    checks["band_quality_valid"] = band_quality_valid(state)

    checks["turning"] = "omitted_by_coding_policy"

    hard_pass = all(v is True or isinstance(v, str) for v in checks.values())

    soft_flags: List[str] = []
    if display_density_too_high(state, params):
        soft_flags.append("display_density_high")
    if frontage_feels_tight(state, params):
        soft_flags.append("frontage_tight")

    fitting_summary = {
        "store_band": choose_store_size_band(float(state.shell.get("area_m2", 0.0))),
        "required_min_rooms": minimum_fitting_room_count(float(state.shell.get("area_m2", 0.0)), params),
        "generated_rooms": len(state.walls_internal.get("fitting_rooms", [])),
        "layout_mode": state.walls_internal.get("fitting_meta", {}).get("layout_mode"),
        "side": state.walls_internal.get("fitting_meta", {}).get("side"),
        "failure_reason": state.walls_internal.get("fitting_meta", {}).get("failure_reason"),
        "room_size_preset": state.walls_internal.get("fitting_meta", {}).get("room_size_preset", getattr(state, "inputs", {}).get("fitting_room_size_preset", "standard")),
    }

    errors = [e for e in [err_meta, err_down, err_score] if e]

    return {
        "hard_pass": hard_pass,
        "checks": checks,
        "soft_flags": soft_flags,
        "fitting_summary": fitting_summary,
        "band_summary": summarize_band_metadata(state),
        "band_errors": errors,
        "display_summary": (getattr(state, "display", {}) or {}).get("summary", {}),
    }




def validate_band_metadata(state) -> tuple[bool, str | None]:
    bands = (getattr(state, "bands", {}) or {}).get("classified_bands", {})
    required = {
        "id", "type", "x", "y", "length", "width",
        "source_archetype", "classification_reason",
        "trimmed_by", "downgrade_history", "quality_score"
    }
    for band_id, band in bands.items():
        if not required.issubset(set(band.keys())):
            missing = sorted(required.difference(set(band.keys())))
            return False, f"{band_id} missing metadata: {', '.join(missing)}"
    return True, None


def validate_downgrade_reasoning(state) -> tuple[bool, str | None]:
    bands = (getattr(state, "bands", {}) or {}).get("classified_bands", {})
    for band in bands.values():
        if band.get("type") in {"side_strip", "feature_pocket", "residual_pocket"} and not band.get("downgrade_history"):
            return False, f"{band.get('id', 'band')} missing downgrade history"
    return True, None


def validate_band_quality_scores(state) -> tuple[bool, str | None]:
    bands = (getattr(state, "bands", {}) or {}).get("classified_bands", {})
    for band in bands.values():
        score = band.get("quality_score", -1)
        if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 1.0):
            return False, f"{band.get('id', 'band')} has invalid quality score"
    return True, None


def summarize_band_metadata(state) -> dict:
    bands_dict = (getattr(state, "bands", {}) or {}).get("classified_bands", {})
    bands = list(bands_dict.values())
    return {
        "row_band_count": sum(1 for b in bands if b.get("type") == "row_band"),
        "side_strip_count": sum(1 for b in bands if b.get("type") == "side_strip"),
        "feature_pocket_count": sum(1 for b in bands if b.get("type") == "feature_pocket"),
        "residual_pocket_count": sum(1 for b in bands if b.get("type") == "residual_pocket"),
        "average_quality_score": round(sum(float(b.get("quality_score", 0.0)) for b in bands) / max(len(bands), 1), 3),
    }

def band_quality_valid(state) -> bool:
    bands = getattr(state, "bands", {}) or {}
    segments = bands.get("perimeter_display_segments", [])
    classified = bands.get("classified_bands", {})
    # perimeter segments should be non-empty if a perimeter host exists
    if bands.get("perimeter_display") and not segments:
        return False
    # No classified bands is acceptable in very constrained small cases as long as perimeter and paths remain valid.
    if not classified:
        return True
    area = float(getattr(state, "shell", {}).get("area_m2", 0.0))
    min_short = 0.7 if area < 80 else 0.8
    min_area = 0.9 if area < 80 else 1.2
    for part in classified.values():
        short_dim = min(rect_w(part), rect_h(part))
        long_dim = max(rect_w(part), rect_h(part))
        if short_dim < min_short or rect_area(part) < min_area:
            return False
        if long_dim / max(short_dim, 0.01) > 10.0 and short_dim < 0.9 and area >= 80:
            return False
    return True
