from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from geometry import band_from_south, inset_rectangle, top_strip, vertical_band, left_strip, right_strip, intersects

Rect = Dict[str, float]


def _rect_right(r: Rect) -> float:
    return r["x"] + r["length"]


def _rect_top(r: Rect) -> float:
    return r["y"] + r["width"]




def _rect_x(r: Rect) -> float:
    return r["x"]


def _rect_y(r: Rect) -> float:
    return r["y"]

def _make_rect(x: float, y: float, length: float, width: float) -> Rect:
    return {
        "x": float(x),
        "y": float(y),
        "length": max(0.0, float(length)),
        "width": max(0.0, float(width)),
    }


def _rect_area(r: Optional[Rect]) -> float:
    if not r:
        return 0.0
    return r["length"] * r["width"]


def _is_valid_rect(r: Optional[Rect], min_length: float = 0.05, min_width: float = 0.05) -> bool:
    return bool(r) and r["length"] >= min_length and r["width"] >= min_width


def _largest_rect(rects: List[Rect]) -> Optional[Rect]:
    valid = [r for r in rects if _is_valid_rect(r)]
    if not valid:
        return None
    return max(valid, key=_rect_area)


def _dimension_pair(rect: Rect) -> Tuple[float, float]:
    short_dim = min(rect["length"], rect["width"])
    long_dim = max(rect["length"], rect["width"])
    return short_dim, long_dim


def subtract_obstacle(rect: Rect, obstacle: Optional[Rect], gap: float = 0.0) -> List[Rect]:
    if not obstacle or not _is_valid_rect(rect) or not intersects(rect, obstacle):
        return [rect]

    ox1 = max(rect["x"], obstacle["x"] - gap)
    ox2 = min(_rect_right(rect), _rect_right(obstacle) + gap)
    oy1 = max(rect["y"], obstacle["y"] - gap)
    oy2 = min(_rect_top(rect), _rect_top(obstacle) + gap)

    if ox2 <= ox1 or oy2 <= oy1:
        return [rect]

    parts = [
        _make_rect(rect["x"], rect["y"], ox1 - rect["x"], rect["width"]),
        _make_rect(ox2, rect["y"], _rect_right(rect) - ox2, rect["width"]),
        _make_rect(ox1, rect["y"], ox2 - ox1, oy1 - rect["y"]),
        _make_rect(ox1, oy2, ox2 - ox1, _rect_top(rect) - oy2),
    ]
    return [p for p in parts if _is_valid_rect(p)]


def subtract_obstacles(rects: List[Rect], obstacles: List[Rect], gap: float = 0.0) -> List[Rect]:
    out = rects[:]
    for obstacle in obstacles:
        next_out: List[Rect] = []
        for rect in out:
            next_out.extend(subtract_obstacle(rect, obstacle, gap=gap))
        out = next_out
    return [r for r in out if _is_valid_rect(r)]


def make_frontage_band(sales_zone: Rect, entrance_position: str, params: Dict[str, Any]) -> Rect:
    # Sales zone already begins after decompression. Keep frontage as a zero-height marker band
    # at the south edge of sales for metadata/continuity purposes without subtracting extra area.
    return _make_rect(sales_zone["x"], sales_zone["y"], sales_zone["length"], 0.0)


def make_primary_path_band(plan, sales_zone: Rect, archetype: str, frontage_band: Rect, params: Dict[str, Any]) -> Rect:
    opening = plan.shell.get("entrance_opening", {})
    open_x1 = float(opening.get("x1", sales_zone["x"]))
    open_x2 = float(opening.get("x2", sales_zone["x"] + sales_zone["length"]))
    opening_center_x = (open_x1 + open_x2) / 2.0

    # sales_zone already starts after decompression, so seed the path directly inside sales_zone
    host = sales_zone
    seeded_width = float(opening.get("width_m", params["primary_path_width_m"]))
    seeded_width = max(seeded_width, float(params["secondary_aisle_min_m"]))
    return vertical_band(host, opening_center_x, seeded_width)


def _target_ribbon(target: Rect, sales_zone: Rect, width: float) -> Rect:
    """Vertical service ribbon aligned with the target and extending from the sales spine zone to the target itself.

    The connector is allowed to extend beyond the sales rectangle because fitting and checkout are side destinations
    attached to the protected circulation network, not destinations reached only by leftover sales field.
    """
    tx = target["x"] if target["x"] <= sales_zone["x"] + sales_zone["length"] / 2.0 else _rect_right(target) - width
    overall_x1 = min(sales_zone["x"], target["x"])
    overall_x2 = max(_rect_right(sales_zone), _rect_right(target))
    tx = max(overall_x1, min(tx, overall_x2 - width))
    y1 = sales_zone["y"]
    y2 = _rect_top(target)
    return _make_rect(tx, y1, width, max(width, y2 - y1))


def _bridge_to_ribbon(primary_path_band: Rect, ribbon: Rect, width: float) -> Rect:
    path_cx = primary_path_band["x"] + primary_path_band["length"] / 2.0
    rib_cx = ribbon["x"] + ribbon["length"] / 2.0
    x1 = min(path_cx, rib_cx)
    x2 = max(path_cx, rib_cx)
    y = max(primary_path_band["y"], min(_rect_top(primary_path_band) - width, ribbon["y"] + width * 0.5))
    return _make_rect(x1, y, max(width, x2 - x1), width)


def _side_service_ribbon(sales_zone: Rect, side: str, targets: List[Rect], width: float) -> Optional[Rect]:
    if not targets:
        return None
    y1 = min(t["y"] for t in targets)
    y2 = max(_rect_top(t) for t in targets)
    x = sales_zone["x"] if side == "left" else _rect_right(sales_zone) - width
    return _make_rect(x, y1, width, max(width, y2 - y1))


def make_access_bands(plan, sales_zone: Rect, primary_path_band: Rect, params: Dict[str, Any]) -> List[Rect]:
    access_bands: List[Rect] = []
    width = params["primary_path_width_m"]
    fitting = plan.zones.get("fitting")
    checkout = plan.zones.get("checkout")
    fitting_side = plan.inputs.get("fitting_position", "auto")
    checkout_side = plan.inputs.get("checkout_position", "auto")
    same_forced_side = fitting and checkout and fitting_side in {"left", "right"} and fitting_side == checkout_side

    if same_forced_side:
        ribbon = _side_service_ribbon(sales_zone, fitting_side, [fitting, checkout], width)
        if ribbon and _is_valid_rect(ribbon, min_length=width * 0.5, min_width=width * 0.5):
            access_bands.append(ribbon)
            access_bands.append(_bridge_to_ribbon(primary_path_band, ribbon, width))
    else:
        if fitting and (_rect_top(fitting) >= sales_zone["y"]):
            fr = _target_ribbon(fitting, sales_zone, width)
            access_bands.append(fr)
            access_bands.append(_bridge_to_ribbon(primary_path_band, fr, width))
        if checkout and (_rect_top(checkout) >= sales_zone["y"]):
            cr = _target_ribbon(checkout, sales_zone, width)
            access_bands.append(cr)
            access_bands.append(_bridge_to_ribbon(primary_path_band, cr, width))

    # Quality filter: avoid duplicate/near-duplicate tiny connectors.
    filtered: List[Rect] = []
    for band in access_bands:
        if not _is_valid_rect(band, min_length=width * 0.5, min_width=width * 0.5):
            continue
        if any(intersects(band, existing) and abs(_rect_area(band) - _rect_area(existing)) < 0.05 for existing in filtered):
            continue
        filtered.append(band)
    return filtered


def _score_perimeter_candidate(candidate: Rect, archetype: str, side: str) -> float:
    if not _is_valid_rect(candidate):
        return -1.0
    area = _rect_area(candidate)
    aspect_bonus = 0.0
    if side in {"left", "right"} and candidate["width"] > candidate["length"]:
        aspect_bonus = 0.10 * area
    if side == "top" and candidate["length"] > candidate["width"]:
        aspect_bonus = 0.10 * area
    preference = {
        "grid": {"top": 1.10, "left": 0.95, "right": 0.95},
        "loop": {"top": 0.95, "left": 1.05, "right": 1.05},
        "central": {"top": 0.90, "left": 1.10, "right": 1.10},
    }.get(archetype, {"top": 1.0, "left": 1.0, "right": 1.0})
    return area * preference.get(side, 1.0) + aspect_bonus


def _quality_filter_part(part: Rect, params: Dict[str, Any]) -> bool:
    if not _is_valid_rect(part, 0.8, 0.8):
        return False
    short_dim, long_dim = _dimension_pair(part)
    if short_dim < 0.8:
        return False
    # reject very awkward slivers that are unlikely to host baseline merchandising logic
    if long_dim / max(short_dim, 0.01) > float(params.get("max_candidate_aspect_ratio", 8.0)) and short_dim < params["gondola_depth_m"]:
        return False
    if _rect_area(part) < float(params.get("min_candidate_area_m2", 1.2)):
        return False
    return True


def make_perimeter_display_segments(plan, sales_zone: Rect, frontage_band: Rect, access_bands: List[Rect], params: Dict[str, Any]) -> List[Rect]:
    archetype = plan.inputs.get("circulation_archetype", "grid")
    # sales_zone is already the post-decompression field; do not inset again by frontage
    host = sales_zone
    depth = params["perimeter_strip_depth_m"]
    raw_candidates = {
        "top": top_strip(host, depth),
        "left": left_strip(host, depth),
        "right": right_strip(host, depth),
    }
    fitting = plan.zones.get("fitting")
    checkout = plan.zones.get("checkout")

    segments: List[Tuple[float, Rect]] = []
    for side, raw in raw_candidates.items():
        obstacles: List[Rect] = []
        if fitting and intersects(raw, fitting):
            obstacles.append(fitting)
        if checkout and intersects(raw, checkout):
            obstacles.append(checkout)
        obstacles.extend([b for b in access_bands if intersects(raw, b)])
        remaining = subtract_obstacles([raw], obstacles, gap=0.0)
        for candidate in remaining:
            # Perimeter hosts are intentionally shallow; use a softer filter than generic candidate bands.
            if not _is_valid_rect(candidate, min_length=1.0, min_width=depth * 0.8):
                continue
            score = _score_perimeter_candidate(candidate, archetype, side)
            segments.append((score, candidate))

    segments.sort(key=lambda item: item[0], reverse=True)
    return [seg for _, seg in segments]


def make_perimeter_display_strip(plan, sales_zone: Rect, frontage_band: Rect, access_bands: List[Rect], params: Dict[str, Any]) -> Rect:
    segments = make_perimeter_display_segments(plan, sales_zone, frontage_band, access_bands, params)
    return segments[0] if segments else top_strip(sales_zone, params["perimeter_strip_depth_m"])


def _field_obstacles(plan, frontage_band: Rect, primary_path_band: Rect, perimeter_segments: List[Rect], access_bands: List[Rect]) -> List[Rect]:
    obstacles = [frontage_band, primary_path_band, *perimeter_segments, *access_bands]
    for key in ("fitting", "checkout", "back_of_house"):
        zone = plan.zones.get(key)
        if zone:
            obstacles.append(zone)
    return [o for o in obstacles if _is_valid_rect(o)]


def _base_candidate_rects(plan, sales_zone: Rect, frontage_band: Rect, primary_path_band: Rect, perimeter_segments: List[Rect], access_bands: List[Rect]) -> List[Rect]:
    obstacles = _field_obstacles(plan, frontage_band, primary_path_band, perimeter_segments, access_bands)
    rects = subtract_obstacles([sales_zone], obstacles, gap=0.0)
    return [r for r in rects if _quality_filter_part(r, plan.params if hasattr(plan, 'params') else {}) or _is_valid_rect(r, 1.0, 1.0)]


def _subdivide_by_vertical_strips(field: Rect, preferred_strip_width: float, min_strip_width: float = 0.8) -> List[Rect]:
    if not _is_valid_rect(field):
        return []
    if field["length"] <= preferred_strip_width * 1.35:
        return [field]
    parts: List[Rect] = []
    x = field["x"]
    remaining = field["length"]
    while remaining > 0.0:
        seg = min(preferred_strip_width, remaining)
        if seg >= min_strip_width:
            parts.append(_make_rect(x, field["y"], seg, field["width"]))
        x += seg
        remaining -= seg
    return [p for p in parts if _is_valid_rect(p, min_length=min_strip_width, min_width=0.6)]


def _subdivide_by_horizontal_strips(field: Rect, preferred_strip_width: float, min_strip_width: float = 0.8) -> List[Rect]:
    if not _is_valid_rect(field):
        return []
    if field["width"] <= preferred_strip_width * 1.35:
        return [field]
    parts: List[Rect] = []
    y = field["y"]
    remaining = field["width"]
    while remaining > 0.0:
        seg = min(preferred_strip_width, remaining)
        if seg >= min_strip_width:
            parts.append(_make_rect(field["x"], y, field["length"], seg))
        y += seg
        remaining -= seg
    return [p for p in parts if _is_valid_rect(p, min_length=0.6, min_width=min_strip_width)]


def split_grid_field(interior_rects: List[Rect], primary_path_band: Rect, params: Dict[str, Any]) -> List[Rect]:
    parts: List[Rect] = []
    preferred = max(params["gondola_depth_m"] + params["secondary_aisle_min_m"], params.get("grid_candidate_strip_width_m", 2.4))
    for rect in interior_rects:
        if rect["length"] >= rect["width"] * 1.35:
            parts.extend(_subdivide_by_horizontal_strips(rect, preferred_strip_width=preferred))
        else:
            parts.extend(_subdivide_by_vertical_strips(rect, preferred_strip_width=preferred))
    return parts


def split_loop_field(interior_rects: List[Rect], primary_path_band: Rect, params: Dict[str, Any]) -> List[Rect]:
    parts: List[Rect] = []
    rear_band_w = max(params["secondary_aisle_min_m"], params.get("loop_rear_band_width_m", 1.6))
    side_pref = max(params.get("loop_candidate_strip_width_m", 2.0), params["gondola_depth_m"])
    for rect in interior_rects:
        if not _is_valid_rect(rect, 1.0, 1.0):
            continue
        if rect["width"] > rear_band_w * 2.0:
            rear = top_strip(rect, rear_band_w)
            below = subtract_obstacles([rect], [rear], gap=0.0)
        else:
            rear = None
            below = [rect]
        if rear and _is_valid_rect(rear, min_length=1.0, min_width=0.8):
            parts.append(rear)
        for sub in below:
            if sub["length"] > side_pref * 2.2:
                left = left_strip(sub, side_pref)
                right = right_strip(sub, side_pref)
                middle = subtract_obstacles([sub], [left, right], gap=0.0)
                if _is_valid_rect(left, 0.8, 0.8):
                    parts.append(left)
                if _is_valid_rect(right, 0.8, 0.8):
                    parts.append(right)
                parts.extend([m for m in middle if _is_valid_rect(m, 0.8, 0.8)])
            else:
                parts.extend(_subdivide_by_vertical_strips(sub, preferred_strip_width=side_pref))
    return parts


def split_central_field(interior_rects: List[Rect], primary_path_band: Rect, params: Dict[str, Any]) -> List[Rect]:
    parts: List[Rect] = []
    open_width = max(params.get("central_open_band_width_m", 2.4), params["secondary_aisle_min_m"])
    side_pref = max(params.get("grid_candidate_strip_width_m", 2.2), params["gondola_depth_m"])
    for rect in interior_rects:
        if rect["length"] > open_width * 2.2:
            central = vertical_band(rect, rect["x"] + rect["length"] / 2.0, open_width)
            side_parts = subtract_obstacles([rect], [central], gap=0.0)
            for sp in side_parts:
                parts.extend(_subdivide_by_vertical_strips(sp, preferred_strip_width=side_pref))
        else:
            parts.extend(_subdivide_by_vertical_strips(rect, preferred_strip_width=side_pref))
    return parts


def split_field_by_archetype(interior_rects: List[Rect], archetype: str, primary_path_band: Rect, params: Dict[str, Any]) -> List[Rect]:
    if archetype == "grid":
        return split_grid_field(interior_rects, primary_path_band, params)
    if archetype == "loop":
        return split_loop_field(interior_rects, primary_path_band, params)
    return split_central_field(interior_rects, primary_path_band, params)


def qualifies_as_row_band(part: Rect, params: Dict[str, Any]) -> bool:
    short_dim, long_dim = _dimension_pair(part)
    required_cross = params["gondola_depth_m"] + params["secondary_aisle_min_m"]
    required_run = params["row_band_min_length_m"]
    return short_dim >= required_cross and long_dim >= required_run


def qualifies_as_side_strip(part: Rect, params: Dict[str, Any]) -> bool:
    short_dim, long_dim = _dimension_pair(part)
    row_cross = params["gondola_depth_m"] + params["secondary_aisle_min_m"]
    return params["side_strip_min_width_m"] <= short_dim < row_cross and long_dim >= params["side_strip_min_length_m"]


def qualifies_as_feature_pocket(part: Rect, params: Dict[str, Any]) -> bool:
    short_dim, long_dim = _dimension_pair(part)
    min_short = min(min(s[0], s[1]) for s in params["table_size_options_m"])
    min_long = min(max(s[0], s[1]) for s in params["table_size_options_m"])
    return short_dim >= min_short and long_dim >= min_long




def _source_side(part: Rect, sales_zone: Rect, primary_path_band: Rect) -> str:
    part_cx = part["x"] + part["length"] / 2.0
    spine_cx = primary_path_band["x"] + primary_path_band["length"] / 2.0
    if part_cx < spine_cx - 0.10:
        return "left"
    if part_cx > spine_cx + 0.10:
        return "right"
    return "center"


def _trimmed_by(part: Rect, plan, frontage_band: Rect, primary_path_band: Rect, access_bands: List[Rect]) -> List[str]:
    reasons: List[str] = []
    fitting = plan.zones.get("fitting")
    checkout = plan.zones.get("checkout")
    boh = plan.zones.get("back_of_house")

    if fitting and abs(_rect_top(fitting) - part["y"]) <= 0.35 or fitting and abs(_rect_right(fitting) - part["x"]) <= 0.35 or fitting and abs(_rect_x(fitting) - _rect_right(part)) <= 0.35:
        reasons.append("fitting")
    if checkout and (abs(_rect_top(checkout) - part["y"]) <= 0.35 or abs(_rect_right(checkout) - part["x"]) <= 0.35 or abs(_rect_x(checkout) - _rect_right(part)) <= 0.35):
        reasons.append("checkout")
    if boh and abs(_rect_y(boh) - _rect_top(part)) <= 0.35:
        reasons.append("back_of_house")
    if abs(_rect_top(frontage_band) - part["y"]) <= 0.35:
        reasons.append("frontage")
    if abs(_rect_right(primary_path_band) - part["x"]) <= 0.35 or abs(_rect_x(primary_path_band) - _rect_right(part)) <= 0.35:
        reasons.append("primary_path")
    if any(abs(_rect_right(b) - part["x"]) <= 0.35 or abs(_rect_x(b) - _rect_right(part)) <= 0.35 or abs(_rect_top(b) - part["y"]) <= 0.35 for b in access_bands):
        reasons.append("access_band")
    # Deduplicate while preserving order
    seen = set()
    out = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def score_row_band(part: Rect, params: Dict[str, Any]) -> float:
    short_dim, long_dim = _dimension_pair(part)
    min_cross = params["gondola_depth_m"] + params["secondary_aisle_min_m"]
    width_score = min(1.0, short_dim / max(min_cross, 0.01))
    run_score = min(1.0, long_dim / max(params["row_band_min_length_m"], 0.01))
    aspect_score = min(1.0, (long_dim / max(short_dim, 0.01)) / 3.0)
    return round((0.45 * width_score) + (0.40 * run_score) + (0.15 * aspect_score), 3)


def score_side_strip(part: Rect, params: Dict[str, Any]) -> float:
    short_dim, long_dim = _dimension_pair(part)
    run_score = min(1.0, long_dim / max(params["side_strip_min_length_m"], 0.01))
    slenderness = long_dim / max(short_dim, 0.01)
    slender_score = min(1.0, slenderness / 4.0)
    return round((0.60 * run_score) + (0.40 * slender_score), 3)


def score_feature_pocket(part: Rect, params: Dict[str, Any]) -> float:
    area = _rect_area(part)
    min_area = float(params.get("feature_pocket_min_area_m2", 1.0))
    return round(min(1.0, area / max(min_area * 2.0, 0.01)), 3)


def make_band(
    band_id: str,
    band_type: str,
    rect: Rect,
    source_archetype: str,
    source_side: str,
    classification_reason: str,
    trimmed_by: List[str],
    downgrade_history: List[Dict[str, str]],
    allowed_families: List[str],
    reducible: bool,
    quality_score: float,
) -> Dict[str, Any]:
    return {
        "id": band_id,
        "type": band_type,
        "x": rect["x"],
        "y": rect["y"],
        "length": rect["length"],
        "width": rect["width"],
        "rect": dict(rect),
        "source_archetype": source_archetype,
        "source_side": source_side,
        "quality_score": quality_score,
        "classification_reason": classification_reason,
        "trimmed_by": trimmed_by,
        "downgrade_history": downgrade_history,
        "allowed_families": allowed_families,
        "reducible": reducible,
    }


def classify_candidate_part(part: Rect, params: Dict[str, Any], archetype: str, source_side: str, band_index: int, trimmed_by: List[str]) -> Dict[str, Any]:
    downgrade_history: List[Dict[str, str]] = []

    if qualifies_as_row_band(part, params):
        return make_band(
            band_id=f"row_band_{band_index}",
            band_type="row_band",
            rect=part,
            source_archetype=archetype,
            source_side=source_side,
            classification_reason="satisfies row width and minimum run length",
            trimmed_by=trimmed_by,
            downgrade_history=downgrade_history,
            allowed_families=["gondola"],
            reducible=True,
            quality_score=score_row_band(part, params),
        )

    downgrade_history.append({"from": "row_band", "to": "side_strip", "reason": "insufficient cross-width or run length for row band"})

    if qualifies_as_side_strip(part, params):
        return make_band(
            band_id=f"side_strip_{band_index}",
            band_type="side_strip",
            rect=part,
            source_archetype=archetype,
            source_side=source_side,
            classification_reason="too narrow for row band but continuous enough for side merchandising",
            trimmed_by=trimmed_by,
            downgrade_history=list(downgrade_history),
            allowed_families=["single_gondola", "table_limited"],
            reducible=True,
            quality_score=score_side_strip(part, params),
        )

    downgrade_history.append({"from": "side_strip", "to": "feature_pocket", "reason": "continuous strip behavior not supported"})

    if qualifies_as_feature_pocket(part, params):
        return make_band(
            band_id=f"feature_pocket_{band_index}",
            band_type="feature_pocket",
            rect=part,
            source_archetype=archetype,
            source_side=source_side,
            classification_reason="fits compact feature use but not strip behavior",
            trimmed_by=trimmed_by,
            downgrade_history=list(downgrade_history),
            allowed_families=["table", "mannequin"],
            reducible=True,
            quality_score=score_feature_pocket(part, params),
        )

    downgrade_history.append({"from": "feature_pocket", "to": "residual_pocket", "reason": "fails usable feature-pocket criteria"})

    return make_band(
        band_id=f"residual_pocket_{band_index}",
        band_type="residual_pocket",
        rect=part,
        source_archetype=archetype,
        source_side=source_side,
        classification_reason="retained as empty residual space",
        trimmed_by=trimmed_by,
        downgrade_history=list(downgrade_history),
        allowed_families=[],
        reducible=True,
        quality_score=0.1,
    )


def build_layout_bands(plan, params: Dict[str, Any]) -> Dict[str, Any]:
    sales_zone = plan.zones["sales"]
    entrance_position = plan.inputs["entrance_position"]
    archetype = plan.inputs["circulation_archetype"]

    frontage_band = make_frontage_band(sales_zone, entrance_position, params)
    primary_path_band = make_primary_path_band(plan, sales_zone, archetype, frontage_band, params)
    access_bands = make_access_bands(plan, sales_zone, primary_path_band, params)
    perimeter_segments = make_perimeter_display_segments(plan, sales_zone, frontage_band, access_bands, params)
    perimeter_strip = perimeter_segments[0] if perimeter_segments else make_perimeter_display_strip(plan, sales_zone, frontage_band, access_bands, params)

    interior_candidate = _base_candidate_rects(plan, sales_zone, frontage_band, primary_path_band, perimeter_segments, access_bands)
    candidate_parts = split_field_by_archetype(interior_candidate, archetype, primary_path_band, params)
    candidate_parts = [p for p in candidate_parts if _quality_filter_part(p, params)]

    classified: Dict[str, Dict[str, Any]] = {}
    counts = {"row_band": 0, "side_strip": 0, "feature_pocket": 0, "residual_pocket": 0}
    for i, part in enumerate(candidate_parts, start=1):
        source_side = _source_side(part, sales_zone, primary_path_band)
        trimmed_by = _trimmed_by(part, plan, frontage_band, primary_path_band, access_bands)
        band = classify_candidate_part(part, params, archetype, source_side, i, trimmed_by)
        counts[band["type"]] += 1
        classified[band["id"]] = band

    return {
        "frontage": frontage_band,
        "primary_path": primary_path_band,
        "access_bands": access_bands,
        "perimeter_display": perimeter_strip,
        "perimeter_display_segments": perimeter_segments,
        "classified_bands": classified,
        "interior_candidate": interior_candidate,
        "meta": {
            "candidate_rect_count": len(interior_candidate),
            "classified_counts": counts,
            "archetype": archetype,
            "perimeter_rect": perimeter_strip,
            "perimeter_segment_count": len(perimeter_segments),
            "band_ids": list(classified.keys()),
            "average_quality_score": round(sum(b.get("quality_score", 0.0) for b in classified.values()) / max(len(classified), 1), 3),
        },
    }
