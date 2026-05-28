
from __future__ import annotations
from typing import Any, Dict, List, Tuple

MIN_ISLAND_W = 0.60
MIN_ISLAND_D = 0.60

Rect = Dict[str, float]

def _rect(x: float, y: float, length: float, width: float) -> Rect:
    return {"x": round(float(x), 6), "y": round(float(y), 6), "length": round(max(0.0, float(length)), 6), "width": round(max(0.0, float(width)), 6)}

def _right(r: Rect) -> float:
    return r["x"] + r["length"]

def _top(r: Rect) -> float:
    return r["y"] + r["width"]

def _overlaps(a: Rect, b: Rect) -> bool:
    return not (_right(a) <= b["x"] or a["x"] >= _right(b) or _top(a) <= b["y"] or a["y"] >= _top(b))

def _center(r: Rect) -> Tuple[float, float]:
    return (r["x"] + r["length"]/2.0, r["y"] + r["width"]/2.0)

def _same_geom(a: Rect, b: Rect, tol: float = 1e-6) -> bool:
    return abs(a["x"]-b["x"]) <= tol and abs(a["y"]-b["y"]) <= tol and abs(a["length"]-b["length"]) <= tol and abs(a["width"]-b["width"]) <= tol

def _subtract_horizontal(base: Rect, cut: Rect) -> List[Rect]:
    out: List[Rect] = []
    if cut["x"] > base["x"] + 1e-6:
        out.append(_rect(base["x"], base["y"], cut["x"] - base["x"], base["width"]))
    if _right(cut) < _right(base) - 1e-6:
        out.append(_rect(_right(cut), base["y"], _right(base) - _right(cut), base["width"]))
    return [r for r in out if r["length"] >= MIN_ISLAND_W and r["width"] >= MIN_ISLAND_D]

def _dedupe_rects(rects: List[Rect]) -> List[Rect]:
    out: List[Rect] = []
    for r in rects:
        if not any(_same_geom(r, e) for e in out):
            out.append(r)
    return out

def _intersect(a: Rect, b: Rect) -> Rect | None:
    ix1 = max(a["x"], b["x"])
    iy1 = max(a["y"], b["y"])
    ix2 = min(_right(a), _right(b))
    iy2 = min(_top(a), _top(b))
    if ix2 - ix1 >= MIN_ISLAND_W and iy2 - iy1 >= MIN_ISLAND_D:
        return _rect(ix1, iy1, ix2 - ix1, iy2 - iy1)
    return None

def _subtract_vertical(base: Rect, cut: Rect) -> List[Rect]:
    out: List[Rect] = []
    if cut["y"] > base["y"] + 1e-6:
        out.append(_rect(base["x"], base["y"], base["length"], cut["y"] - base["y"]))
    if _top(cut) < _top(base) - 1e-6:
        out.append(_rect(base["x"], _top(cut), base["length"], _top(base) - _top(cut)))
    return [r for r in out if r["length"] >= MIN_ISLAND_W and r["width"] >= MIN_ISLAND_D]

def _left_right_side_aisles(side_aisles: List[Rect], sales: Rect) -> Tuple[Rect | None, Rect | None]:
    left = None
    right = None
    if side_aisles:
        mid_x = sales["x"] + sales["length"] / 2.0
        left_candidates = [r for r in side_aisles if _right(r) <= mid_x + 1e-6]
        right_candidates = [r for r in side_aisles if r["x"] >= mid_x - 1e-6]
        if left_candidates:
            left = min(left_candidates, key=lambda r: r["x"])
        if right_candidates:
            right = max(right_candidates, key=lambda r: r["x"])
        if left is None or right is None:
            sorted_aisles = sorted(side_aisles, key=lambda r: r["x"])
            if left is None:
                left = sorted_aisles[0]
            if right is None:
                right = sorted_aisles[-1]
    return left, right

def _build_domain(x1: float, x2: float, y0: float, y1: float) -> Rect | None:
    left_x = round(min(x1, x2), 6)
    right_x = round(max(x1, x2), 6)
    h = round(max(0.0, y1 - y0), 6)
    w = round(right_x - left_x, 6)
    if w + 1e-6 < MIN_ISLAND_W or h + 1e-6 < MIN_ISLAND_D:
        return None
    return _rect(left_x, y0, w, h)

def _pick_vertical_secondary_by_half(territorial_secondary_aisles: List[Rect], sales: Rect) -> Tuple[Rect | None, Rect | None]:
    left = None
    right = None
    if territorial_secondary_aisles:
        mid_x = sales["x"] + sales["length"] / 2.0
        left_candidates = [r for r in territorial_secondary_aisles if _right(r) <= mid_x + 1e-6]
        right_candidates = [r for r in territorial_secondary_aisles if r["x"] >= mid_x - 1e-6]
        if left_candidates:
            left = max(left_candidates, key=lambda r: _right(r))
        if right_candidates:
            right = min(right_candidates, key=lambda r: r["x"])
    return left, right

def _build_side_domains(sales: Rect, opening_pos: str, spine: Rect, side_aisles: List[Rect], territorial_secondary_aisles: List[Rect], frontage_top: float, top_limit: float) -> Tuple[Rect | None, Rect | None]:
    left_side_aisle, right_side_aisle = _left_right_side_aisles(side_aisles, sales)
    left_vertical_secondary, right_vertical_secondary = _pick_vertical_secondary_by_half(territorial_secondary_aisles, sales)
    y0 = frontage_top
    y1 = min(_top(sales), top_limit)
    if y1 - y0 < MIN_ISLAND_D:
        return None, None

    left_domain = None
    right_domain = None
    sales_left = sales["x"]
    sales_right = _right(sales)

    if opening_pos == "center":
        left_inner = left_vertical_secondary["x"] if left_vertical_secondary is not None else (left_side_aisle["x"] if left_side_aisle is not None else None)
        if left_inner is not None:
            left_domain = _build_domain(sales_left, left_inner, y0, y1)
        if left_domain is not None:
            mirror_w = round(left_domain["length"], 6)
            if mirror_w + 1e-6 >= MIN_ISLAND_W:
                right_domain = _build_domain(sales_right - mirror_w, sales_right, y0, y1)

    elif opening_pos == "right":
        if left_side_aisle is not None:
            left_domain = _build_domain(sales_left, left_side_aisle["x"], y0, y1)
        right_domain = _build_domain(_right(spine), sales_right, y0, y1)

    elif opening_pos == "left":
        left_domain = _build_domain(sales_left, spine["x"], y0, y1)
        if right_side_aisle is not None:
            right_domain = _build_domain(_right(right_side_aisle), sales_right, y0, y1)

    return left_domain, right_domain

def build_display_classification(shell: Dict[str, Any], zoning: Dict[str, Any], circulation: Dict[str, Any], frontage: Dict[str, Any] | None = None) -> Dict[str, Any]:
    sales = zoning["sales_zone"]
    opening_pos = str(shell.get("entrance_opening", {}).get("position", "center")).lower()
    spine = circulation["primary_spine"]

    frontage_zones = list((frontage or {}).get("zones", []))
    frontage_rects = [z["rect"] for z in frontage_zones]
    frontage_top = max((_top(r) for r in frontage_rects), default=sales["y"])

    # Horizontal circulation bands used to create rows
    horiz_paths = []
    if circulation.get("service_connector"):
        horiz_paths.append(circulation["service_connector"])
    seen = set()
    for r in circulation.get("secondary_aisles", []):
        key = (round(r["y"], 6), round(r["width"], 6))
        if key not in seen:
            seen.add(key)
            horiz_paths.append(r)
    horiz_paths = sorted(horiz_paths, key=lambda r: r["y"])

    row_bands: List[Rect] = []
    current_y = frontage_top
    for hp in horiz_paths:
        if hp["y"] > current_y + MIN_ISLAND_D:
            row_bands.append(_rect(sales["x"], current_y, sales["length"], hp["y"] - current_y))
        current_y = max(current_y, hp["y"] + hp["width"])

    # Vertical circulation boundaries
    verticals = []
    for key in ["side_secondary_aisles", "territorial_aisles", "territorial_secondary_aisles"]:
        verticals.extend(circulation.get(key, []))
    verticals.append(spine)
    verticals = [r for r in verticals if r["width"] > 0 and r["length"] > 0]

    # General cells above frontage
    cells: List[Rect] = []
    for band in row_bands:
        band_verticals = [v for v in verticals if not (_top(v) <= band["y"] or v["y"] >= _top(band))]
        band_verticals = sorted(band_verticals, key=lambda r: r["x"])
        x_cursor = sales["x"]
        for v in band_verticals:
            if v["x"] > x_cursor + MIN_ISLAND_W:
                cells.append(_rect(x_cursor, band["y"], v["x"] - x_cursor, band["width"]))
            x_cursor = max(x_cursor, _right(v))
        if _right(sales) > x_cursor + MIN_ISLAND_W:
            cells.append(_rect(x_cursor, band["y"], _right(sales)-x_cursor, band["width"]))
    cells = [r for r in cells if r["length"] >= MIN_ISLAND_W and r["width"] >= MIN_ISLAND_D]

    # D5/D6 wall segments: explicit side domains by opening condition
    # Center opening: wall strip is between wall and side wall aisle on each side
    # Right opening: left strip uses left side wall aisle, right strip uses main spine
    # Left opening: left strip uses main spine, right strip uses right side wall aisle
    d5: List[Rect] = []
    d6: List[Rect] = []
    top_limit = circulation.get("service_connector", {}).get("y", _top(sales)) if circulation.get("service_connector") else _top(sales)
    left_domain, right_domain = _build_side_domains(
        sales,
        opening_pos,
        spine,
        circulation.get("side_secondary_aisles", []),
        circulation.get("territorial_secondary_aisles", []),
        frontage_top,
        top_limit,
    )

    secondary_bands: List[Rect] = []
    seen_secondary = set()
    for r in circulation.get("secondary_aisles", []):
        key = (round(r["y"], 6), round(r["width"], 6))
        if key not in seen_secondary:
            seen_secondary.add(key)
            secondary_bands.append(_rect(sales["x"], r["y"], sales["length"], r["width"]))
    secondary_bands = sorted(secondary_bands, key=lambda r: r["y"])

    domain_cuts: Dict[str, List[Rect]] = {"left": [], "right": []}
    domain_pieces: Dict[str, List[Rect]] = {"left": [], "right": []}
    domain_map = [("left", left_domain), ("right", right_domain)]
    for side, domain in domain_map:
        if not domain:
            continue
        cuts: List[Rect] = []
        for band in secondary_bands:
            inter = _intersect(domain, band)
            if inter is not None:
                cuts.append(inter)
        domain_cuts[side] = cuts
        pieces = [domain]
        for c in sorted(cuts, key=lambda r: r["y"]):
            next_pieces: List[Rect] = []
            for p in pieces:
                if _overlaps(p, c):
                    next_pieces.extend(_subtract_vertical(p, c))
                else:
                    next_pieces.append(p)
            pieces = next_pieces
        domain_pieces[side] = pieces

    # Center-spine hard mirroring: apply the full left-side D5/D6 division concept to the right side.
    if opening_pos == "center" and left_domain is not None and right_domain is not None:
        mirrored_right_cuts: List[Rect] = []
        for lc in domain_cuts["left"]:
            mirrored_right_cuts.append(_rect(right_domain["x"], lc["y"], right_domain["length"], lc["width"]))
        mirrored_right_pieces: List[Rect] = []
        for lp in domain_pieces["left"]:
            mirrored_right_pieces.append(_rect(right_domain["x"], lp["y"], right_domain["length"], lp["width"]))
        domain_cuts["right"] = mirrored_right_cuts
        domain_pieces["right"] = mirrored_right_pieces

    d6.extend(domain_cuts["left"])
    d6.extend(domain_cuts["right"])
    d5.extend(domain_pieces["left"])
    d5.extend(domain_pieces["right"])

    # D7/D8: wall display strips alongside the horizontal service connector aisle.
    # - Vertical extent = service connector aisle thickness
    # - Horizontal depth = same wall-strip depth used by D5/D6 domains
    # - D7 follows fitting side; D8 follows checkout side
    d7: List[Rect] = []
    d8: List[Rect] = []
    service_connector = circulation.get("service_connector")
    left_strip_depth = round(left_domain["length"], 6) if left_domain is not None else None
    right_strip_depth = round(right_domain["length"], 6) if right_domain is not None else None

    left_service_strip = None
    right_service_strip = None
    if service_connector is not None:
        if left_strip_depth is not None and left_strip_depth + 1e-6 >= MIN_ISLAND_W:
            left_service_strip = _build_domain(sales["x"], sales["x"] + left_strip_depth, service_connector["y"], _top(service_connector))
        if right_strip_depth is not None and right_strip_depth + 1e-6 >= MIN_ISLAND_W:
            right_service_strip = _build_domain(_right(sales) - right_strip_depth, _right(sales), service_connector["y"], _top(service_connector))

    if service_connector is not None and (left_service_strip is not None or right_service_strip is not None):

        fitting_side = str(zoning.get("fitting_side", "left")).lower()
        sales_mid_x = sales["x"] + sales["length"] / 2.0
        checkout_zone = zoning.get("checkout_zone")
        checkout_side = "right"
        if checkout_zone is not None:
            checkout_cx = checkout_zone["x"] + checkout_zone["length"] / 2.0
            checkout_side = "left" if checkout_cx < sales_mid_x else "right"

        if fitting_side == "left" and left_service_strip is not None:
            d7.append(left_service_strip)
        elif fitting_side == "right" and right_service_strip is not None:
            d7.append(right_service_strip)

        if checkout_side == "left" and left_service_strip is not None:
            d8.append(left_service_strip)
        elif checkout_side == "right" and right_service_strip is not None:
            d8.append(right_service_strip)

    # D9/D10: opening-side frontage residual wall strips for asymmetric openings.
    # - D9 exists only for right opening, on the right wall side.
    # - D10 exists only for left opening, on the left wall side.
    # - X-depth equals the corresponding D5 wall-strip depth on that side.
    # - Y-depth equals the frontage decomposition depth.
    d9: List[Rect] = []
    d10: List[Rect] = []
    frontage_depth = frontage_rects[0]["width"] if frontage_rects else 0.0
    if frontage_depth >= MIN_ISLAND_W - 1e-6:
        if opening_pos == "right" and right_strip_depth is not None and right_strip_depth + 1e-6 >= MIN_ISLAND_W:
            residual_right = _build_domain(_right(sales) - right_strip_depth, _right(sales), sales["y"], sales["y"] + frontage_depth)
            if residual_right is not None:
                d9.append(residual_right)
        elif opening_pos == "left" and left_strip_depth is not None and left_strip_depth + 1e-6 >= MIN_ISLAND_W:
            residual_left = _build_domain(sales["x"], sales["x"] + left_strip_depth, sales["y"], sales["y"] + frontage_depth)
            if residual_left is not None:
                d10.append(residual_left)

    # D2: first islands after opening = bottom row adjacent to spine
    d2: List[Rect] = []
    if cells:
        min_y = min(r["y"] for r in cells)
        same_row = [r for r in cells if abs(r["y"] - min_y) < 1e-6]
        left_of_spine = [r for r in same_row if _right(r) <= spine["x"] + 1e-6]
        right_of_spine = [r for r in same_row if r["x"] >= _right(spine) - 1e-6]
        if opening_pos == "center":
            if left_of_spine:
                d2.append(max(left_of_spine, key=lambda r: _right(r)))
            if right_of_spine:
                d2.append(min(right_of_spine, key=lambda r: r["x"]))
        elif opening_pos == "left":
            # Left opening: the first island after the opening sits on the inner/right side of the main spine.
            if right_of_spine:
                d2.append(min(right_of_spine, key=lambda r: r["x"]))
        elif opening_pos == "right":
            # Right opening: the first island after the opening sits on the inner/left side of the main spine.
            if left_of_spine:
                d2.append(max(left_of_spine, key=lambda r: _right(r)))

    # D3: frontage modules opposite to D2.
    # Locked rule: each D2 projects upward into its corresponding frontage piece and creates one matching D3.
    d3: List[Rect] = []
    def _best_frontage_for_source(src: Rect, pieces: List[Rect]) -> Rect | None:
        if not pieces:
            return None
        cx = src["x"] + src["length"] / 2.0
        containing = [f for f in pieces if f["x"] - 1e-6 <= cx <= _right(f) + 1e-6]
        if containing:
            return min(containing, key=lambda f: abs((f["x"] + f["length"] / 2.0) - cx))
        return min(pieces, key=lambda f: abs((f["x"] + f["length"] / 2.0) - cx))

    if d2 and frontage_rects:
        if opening_pos == "center":
            # Each D2 creates the D3 directly opposite to it in its frontage piece.
            for src in d2:
                f = _best_frontage_for_source(src, frontage_rects)
                if f is None:
                    continue
                ix1 = max(src["x"], f["x"])
                ix2 = min(_right(src), _right(f))
                seg_len = ix2 - ix1
                if seg_len >= MIN_ISLAND_W - 1e-6:
                    d3.append(_rect(ix1, f["y"], seg_len, f["width"]))
        else:
            # Single active frontage side; D3 starts from the spine side and matches D2 length in X.
            src = d2[0]
            f = _best_frontage_for_source(src, frontage_rects)
            if f is not None:
                seg_len = min(src["length"], f["length"])
                if seg_len >= MIN_ISLAND_W - 1e-6:
                    if opening_pos == "left":
                        start_x = max(f["x"], _right(spine))
                        use_len = min(seg_len, _right(f) - start_x)
                        if use_len >= MIN_ISLAND_W - 1e-6:
                            d3.append(_rect(start_x, f["y"], use_len, f["width"]))
                    elif opening_pos == "right":
                        end_x = min(_right(f), spine["x"])
                        use_len = min(seg_len, end_x - f["x"])
                        if use_len >= MIN_ISLAND_W - 1e-6:
                            d3.append(_rect(end_x - use_len, f["y"], use_len, f["width"]))

    # D1: remaining middle islands after excluding D2 and side strips
    excluded = d2 + d5 + d6
    d1 = [r for r in cells if not any(_same_geom(r, e) or _overlaps(r, e) for e in excluded)]

    # D4: frontage modules opposite to D1.
    # Locked rule: each D1 projects upward into its corresponding frontage piece/cell and creates one matching D4.
    # The projection clips to vertical aisle / spine boundaries that touch frontage, and must not overlap D3.
    d4: List[Rect] = []
    frontage_cells: List[Rect] = []
    for f in frontage_rects:
        touching_verticals = [v for v in verticals if not (_top(v) <= f["y"] or v["y"] >= _top(f))]
        touching_verticals = sorted(touching_verticals, key=lambda r: r["x"])
        x_cursor = f["x"]
        for v in touching_verticals:
            if v["x"] > x_cursor + MIN_ISLAND_W:
                frontage_cells.append(_rect(x_cursor, f["y"], v["x"] - x_cursor, f["width"]))
            x_cursor = max(x_cursor, _right(v))
        if _right(f) > x_cursor + MIN_ISLAND_W:
            frontage_cells.append(_rect(x_cursor, f["y"], _right(f) - x_cursor, f["width"]))

    # Remove D3-occupied spans from D4 candidate cells so D3 stays the frontage piece opposite D2.
    frontage_cells_no_d3: List[Rect] = []
    for fc in frontage_cells:
        segments = [fc]
        for r3 in d3:
            next_segments: List[Rect] = []
            for seg in segments:
                if not _overlaps(seg, r3):
                    next_segments.append(seg)
                    continue
                if seg["x"] < r3["x"] - 1e-6:
                    left_len = r3["x"] - seg["x"]
                    if left_len >= MIN_ISLAND_W - 1e-6:
                        next_segments.append(_rect(seg["x"], seg["y"], left_len, seg["width"]))
                if _right(seg) > _right(r3) + 1e-6:
                    right_x = _right(r3)
                    right_len = _right(seg) - right_x
                    if right_len >= MIN_ISLAND_W - 1e-6:
                        next_segments.append(_rect(right_x, seg["y"], right_len, seg["width"]))
            segments = next_segments
        frontage_cells_no_d3.extend(segments)

    def _best_frontage_cell_for_source(src: Rect, pieces: List[Rect]) -> Rect | None:
        if not pieces:
            return None
        cx = src["x"] + src["length"] / 2.0
        containing = [fc for fc in pieces if fc["x"] - 1e-6 <= cx <= _right(fc) + 1e-6]
        if containing:
            return min(containing, key=lambda fc: abs((fc["x"] + fc["length"] / 2.0) - cx))
        return min(pieces, key=lambda fc: abs((fc["x"] + fc["length"] / 2.0) - cx))

    for src in d1:
        fc = _best_frontage_cell_for_source(src, frontage_cells_no_d3)
        if fc is None:
            continue
        ix1 = max(src["x"], fc["x"])
        ix2 = min(_right(src), _right(fc))
        seg_len = ix2 - ix1
        if seg_len >= MIN_ISLAND_W - 1e-6:
            d4.append(_rect(ix1, fc["y"], seg_len, fc["width"]))

    # D11: frontage display islands opposite vertical paths.
    # These fill the frontage decomposition voids aligned with vertical side/territorial paths.
    d11: List[Rect] = []
    frontage_path_verticals: List[Rect] = []
    for key in ["side_secondary_aisles", "territorial_aisles", "territorial_secondary_aisles"]:
        frontage_path_verticals.extend(circulation.get(key, []))
    for f in frontage_rects:
        for v in frontage_path_verticals:
            inter = _intersect(f, _rect(v["x"], f["y"], v["length"], f["width"]))
            if inter is not None and inter["length"] >= MIN_ISLAND_W - 1e-6:
                d11.append(inter)

    # D12: corner frontage display island.
    # Center opening: build on both left and right frontage pieces using nearest D4, else D3.
    # Left main spine: build on the right frontage piece only, from the right wall to the end of the right side secondary aisle.
    # Right main spine: build on the left frontage piece only, from the left wall to the end of the left side secondary aisle.
    d12: List[Rect] = []
    left_side_aisle, right_side_aisle = _left_right_side_aisles(circulation.get("side_secondary_aisles", []), sales)

    def _anchors_for_frontage(f: Rect) -> Tuple[List[Rect], List[Rect]]:
        return [r for r in d4 if _overlaps(r, f)], [r for r in d3 if _overlaps(r, f)]

    if opening_pos == "left":
        active_f = max(frontage_rects, key=lambda r: _right(r), default=None)
        if active_f is not None:
            anchors_d4, anchors_d3 = _anchors_for_frontage(active_f)
            seg = None
            if right_side_aisle is not None:
                # D12 ends at the OUTER side of the right vertical path (the far path edge from the right wall relation).
                seg = _build_domain(max(active_f["x"], right_side_aisle["x"]), _right(active_f), active_f["y"], _top(active_f))
            if seg is None and anchors_d4:
                nearest = max(anchors_d4, key=lambda r: _right(r))
                seg = _build_domain(_right(nearest), _right(active_f), active_f["y"], _top(active_f))
            if seg is None and anchors_d3:
                nearest = max(anchors_d3, key=lambda r: _right(r))
                seg = _build_domain(_right(nearest), _right(active_f), active_f["y"], _top(active_f))
            if seg is not None:
                d12.append(seg)
    elif opening_pos == "right":
        active_f = min(frontage_rects, key=lambda r: r["x"], default=None)
        if active_f is not None:
            anchors_d4, anchors_d3 = _anchors_for_frontage(active_f)
            seg = None
            if left_side_aisle is not None:
                # D12 ends at the OUTER side of the left vertical path (the far path edge from the left wall relation).
                seg = _build_domain(active_f["x"], min(_right(active_f), _right(left_side_aisle)), active_f["y"], _top(active_f))
            if seg is None and anchors_d4:
                nearest = min(anchors_d4, key=lambda r: r["x"])
                seg = _build_domain(active_f["x"], nearest["x"], active_f["y"], _top(active_f))
            if seg is None and anchors_d3:
                nearest = min(anchors_d3, key=lambda r: r["x"])
                seg = _build_domain(active_f["x"], nearest["x"], active_f["y"], _top(active_f))
            if seg is not None:
                d12.append(seg)
    else:
        for f in frontage_rects:
            piece_is_left = _right(f) <= spine["x"] + 1e-6
            piece_is_right = f["x"] >= _right(spine) - 1e-6
            if not (piece_is_left or piece_is_right):
                continue
            anchors_d4, anchors_d3 = _anchors_for_frontage(f)
            if piece_is_left:
                if anchors_d4:
                    nearest = min(anchors_d4, key=lambda r: r["x"])
                    seg = _build_domain(f["x"], nearest["x"], f["y"], _top(f))
                elif anchors_d3:
                    nearest = min(anchors_d3, key=lambda r: r["x"])
                    seg = _build_domain(f["x"], nearest["x"], f["y"], _top(f))
                else:
                    seg = None
                if seg is not None:
                    d12.append(seg)
            elif piece_is_right:
                if anchors_d4:
                    nearest = max(anchors_d4, key=lambda r: _right(r))
                    seg = _build_domain(_right(nearest), _right(f), f["y"], _top(f))
                elif anchors_d3:
                    nearest = max(anchors_d3, key=lambda r: _right(r))
                    seg = _build_domain(_right(nearest), _right(f), f["y"], _top(f))
                else:
                    seg = None
                if seg is not None:
                    d12.append(seg)

    # Keep D12 visible as the corner frontage piece by removing any accidental D4 overlap.
    if d12:
        clipped_d4: List[Rect] = []
        for r4 in d4:
            segments = [r4]
            for c in d12:
                next_segments: List[Rect] = []
                for s in segments:
                    if not _overlaps(s, c):
                        next_segments.append(s)
                        continue
                    ix1 = max(s["x"], c["x"])
                    ix2 = min(_right(s), _right(c))
                    if ix1 - s["x"] >= MIN_ISLAND_W - 1e-6:
                        next_segments.append(_rect(s["x"], s["y"], ix1 - s["x"], s["width"]))
                    if _right(s) - ix2 >= MIN_ISLAND_W - 1e-6:
                        next_segments.append(_rect(ix2, s["y"], _right(s) - ix2, s["width"]))
                segments = next_segments
            clipped_d4.extend(segments)
        d4 = clipped_d4

    # Remove D11 wherever it meets D12 at the frontage corners.
    if d12 and d11:
        clipped_d11: List[Rect] = []
        for r11 in d11:
            keep = True
            for c in d12:
                if not _overlaps(r11, c):
                    continue
                # Corner cleanup rule: suppress D11 completely if it touches or overlaps a D12 corner piece.
                keep = False
                break
            if keep:
                clipped_d11.append(r11)
        d11 = clipped_d11

    d1 = _dedupe_rects(d1)
    d2 = _dedupe_rects(d2)
    d3 = _dedupe_rects(d3)
    d4 = _dedupe_rects(d4)
    d5 = _dedupe_rects(d5)
    d6 = _dedupe_rects(d6)
    d7 = _dedupe_rects(d7)
    d8 = _dedupe_rects(d8)
    d9 = _dedupe_rects(d9)
    d10 = _dedupe_rects(d10)
    d12 = _dedupe_rects(d12)

    def pack(name: str, rects: List[Rect]) -> List[Dict[str, Any]]:
        return [{"rect": r, "class": name, "area_m2": round(r["length"]*r["width"], 6)} for r in rects]

    return {
        "D1": pack("D1", d1),
        "D2": pack("D2", d2),
        "D3": pack("D3", d3),
        "D4": pack("D4", d4),
        "D5": pack("D5", d5),
        "D6": pack("D6", d6),
        "D7": pack("D7", d7),
        "D8": pack("D8", d8),
        "D9": pack("D9", d9),
        "D10": pack("D10", d10),
        "D11": pack("D11", d11),
        "D12": pack("D12", d12),
        "counts": {"D1": len(d1), "D2": len(d2), "D3": len(d3), "D4": len(d4), "D5": len(d5), "D6": len(d6), "D7": len(d7), "D8": len(d8), "D9": len(d9), "D10": len(d10), "D11": len(d11), "D12": len(d12)},
        "rule_order": ["D9", "D10", "D12", "D11", "D7", "D8", "D5", "D6", "D3", "D4", "D2", "D1"],
    }
