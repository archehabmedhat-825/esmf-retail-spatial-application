from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# Final export layer
# - Monochrome output
# - No hatch
# - Distinct lineweights
# - Center labels inside objects with text-fit behavior
# - SVG markup generation
# - Structured DXF payload generation
# ============================================================

LINEWEIGHTS_MM: Dict[str, float] = {
    "WALL_EXT": 0.55,
    "WALL_GLASS": 0.55,
    "WALL_INT": 0.55,
    "WALL_BOH": 0.55,
    "WALL_FITTING": 0.55,
    "ADDED_ZONES": 0.35,
    "FITTING_AREA_BUFFER": 0.35,
    "FITTING_ROOMS": 0.35,
    "CHECKOUT_BUFFER": 0.18,
    "CHECKOUT_COUNTER": 0.35,
    "CHECKOUT_STAFF_BUFFER": 0.35,
    "DISPLAY_WALL": 0.35,
    "DISPLAY_WALL_BUFFER": 0.35,
    "DISPLAY_GONDOLA": 0.22,
    "DISPLAY_GONDOLA_BUFFER": 0.15,
    "DISPLAY_TABLE": 0.22,
    "DISPLAY_TABLE_BUFFER_MIN": 0.15,
    "DISPLAY_TABLE_BUFFER": 0.20,
    "INTERACTIVE_T1_BUFFER": 0.13,
    "INTERACTIVE_T1_BUFFER_MIN": 0.13,
    "INTERACTIVE_T1": 0.55,
    "INTERACTIVE_T2_BUFFER": 0.13,
    "INTERACTIVE_T2_BUFFER_MIN": 0.13,
    "INTERACTIVE_T2": 0.55,
    "INTERACTIVE_T3_BUFFER": 0.13,
    "INTERACTIVE_T3_BUFFER_MIN": 0.13,
    "INTERACTIVE_T3": 0.55,
    "INTERACTIVE_T4_BUFFER": 0.13,
    "INTERACTIVE_T4_BUFFER_MIN": 0.13,
    "INTERACTIVE_T4": 0.55,
    "INTERACTIVE_T5_BUFFER": 0.13,
    "INTERACTIVE_T5_BUFFER_MIN": 0.13,
    "INTERACTIVE_T5": 0.55,
    "INTERACTIVE_T6_BUFFER": 0.13,
    "INTERACTIVE_T6_BUFFER_MIN": 0.13,
    "INTERACTIVE_T6": 0.55,
    "INTERACTIVE_T7_BUFFER": 0.13,
    "INTERACTIVE_T7_BUFFER_MIN": 0.13,
    "INTERACTIVE_T7": 0.55,
    "INTERACTIVE_T8_BUFFER": 0.13,
    "INTERACTIVE_T8_BUFFER_MIN": 0.13,
    "INTERACTIVE_T8": 0.55,
    "INTERACTIVE_T9_BUFFER": 0.13,
    "INTERACTIVE_T9_BUFFER_MIN": 0.13,
    "INTERACTIVE_T9": 0.55,
    "DISPLAY_MANNEQUIN": 0.20,
    "DISPLAY_MANNEQUIN_BUFFER": 0.20,
    "DISPLAY_D1": 0.18,
    "DISPLAY_D2": 0.18,
    "DISPLAY_D3": 0.18,
    "DISPLAY_D4": 0.18,
    "DISPLAY_D5": 0.18,
    "DISPLAY_D6": 0.18,
    "DISPLAY_D7": 0.18,
    "DISPLAY_D8": 0.18,
    "DISPLAY_D9": 0.18,
    "DISPLAY_D10": 0.18,
    "DISPLAY_D11": 0.18,
    "DISPLAY_D12": 0.18,
    "PATHS": 0.15,
    "GRAPHIC_PATTERNS": 0.10,
    "DIMENSIONS": 0.11,
    "LABELS": 0.10,
    "ZONE_GUIDES": 0.10,
    "OPENINGS": 0.18,
}

TEXT_SIZE_PT: Dict[str, float] = {
    "title": 20.0,
    "zone": 13.0,
    "fixture": 9.0,
    "dimension": 8.0,
    "small": 7.0,
}

DASH_PATTERNS: Dict[str, str] = {
    "PATHS": "6,4",
    "ZONE_GUIDES": "4,4",
    "FITTING_AREA_BUFFER": "8,4",
    "CHECKOUT_BUFFER": "4,3",
    "CHECKOUT_STAFF_BUFFER": "8,4",
    "DISPLAY_WALL_BUFFER": "8,4",
    "DISPLAY_GONDOLA_BUFFER": "8,4",
    "DISPLAY_TABLE_BUFFER_MIN": "8,4",
    "DISPLAY_TABLE_BUFFER": "8,4",
    "INTERACTIVE_T1_BUFFER": "6,4",
    "INTERACTIVE_T1_BUFFER_MIN": "6,4",
    "INTERACTIVE_T2_BUFFER": "6,4",
    "INTERACTIVE_T2_BUFFER_MIN": "6,4",
    "INTERACTIVE_T3_BUFFER": "6,4",
    "INTERACTIVE_T3_BUFFER_MIN": "6,4",
    "INTERACTIVE_T4_BUFFER": "6,4",
    "INTERACTIVE_T4_BUFFER_MIN": "6,4",
    "INTERACTIVE_T5_BUFFER": "6,4",
    "INTERACTIVE_T5_BUFFER_MIN": "6,4",
    "INTERACTIVE_T6_BUFFER": "6,4",
    "INTERACTIVE_T6_BUFFER_MIN": "6,4",
    "INTERACTIVE_T7_BUFFER": "6,4",
    "INTERACTIVE_T7_BUFFER_MIN": "6,4",
    "INTERACTIVE_T8_BUFFER": "6,4",
    "INTERACTIVE_T8_BUFFER_MIN": "6,4",
    "INTERACTIVE_T9_BUFFER": "6,4",
    "INTERACTIVE_T9_BUFFER_MIN": "6,4",
    "DISPLAY_MANNEQUIN_BUFFER": "8,4",
    "DIMENSIONS": "3,2",
}

SVG_STYLE_BY_LAYER: Dict[str, Dict[str, str]] = {
    "WALL_EXT": {"stroke": "black", "fill": "black"},
    "WALL_GLASS": {"stroke": "black", "fill": "none"},
    "WALL_INT": {"stroke": "black", "fill": "none"},
    "WALL_BOH": {"stroke": "black", "fill": "none"},
    "WALL_FITTING": {"stroke": "black", "fill": "none"},
    "ADDED_ZONES": {"stroke": "black", "fill": "none"},
    "FITTING_AREA_BUFFER": {"stroke": "black", "fill": "none"},
    "FITTING_ROOMS": {"stroke": "black", "fill": "none"},
    "CHECKOUT_BUFFER": {"stroke": "black", "fill": "none"},
    "CHECKOUT_COUNTER": {"stroke": "black", "fill": "none"},
    "CHECKOUT_STAFF_BUFFER": {"stroke": "black", "fill": "none"},
    "DISPLAY_WALL": {"stroke": "black", "fill": "none"},
    "DISPLAY_WALL_BUFFER": {"stroke": "black", "fill": "none"},
    "DISPLAY_GONDOLA": {"stroke": "black", "fill": "none"},
    "DISPLAY_GONDOLA_BUFFER": {"stroke": "black", "fill": "none"},
    "DISPLAY_TABLE": {"stroke": "black", "fill": "none"},
    "DISPLAY_TABLE_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "DISPLAY_TABLE_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T1_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T1_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T1": {"stroke": "black", "fill": "red"},
    "INTERACTIVE_T2_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T2_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T2": {"stroke": "black", "fill": "green"},
    "INTERACTIVE_T3_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T3_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T3": {"stroke": "black", "fill": "blue"},
    "INTERACTIVE_T4_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T4_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T4": {"stroke": "black", "fill": "yellow"},
    "INTERACTIVE_T5_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T5_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T5": {"stroke": "black", "fill": "magenta"},
    "INTERACTIVE_T6_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T6_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T6": {"stroke": "black", "fill": "cyan"},
    "INTERACTIVE_T7_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T7_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T7": {"stroke": "black", "fill": "purple"},
    "INTERACTIVE_T8_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T8_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T8": {"stroke": "black", "fill": "orange"},
    "INTERACTIVE_T9_BUFFER": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T9_BUFFER_MIN": {"stroke": "black", "fill": "none"},
    "INTERACTIVE_T9": {"stroke": "black", "fill": "cyan"},
    "DISPLAY_MANNEQUIN": {"stroke": "black", "fill": "none"},
    "DISPLAY_MANNEQUIN_BUFFER": {"stroke": "black", "fill": "none"},
    "DISPLAY_D1": {"stroke": "black", "fill": "none"},
    "DISPLAY_D2": {"stroke": "black", "fill": "none"},
    "DISPLAY_D3": {"stroke": "black", "fill": "none"},
    "DISPLAY_D4": {"stroke": "black", "fill": "none"},
    "DISPLAY_D5": {"stroke": "black", "fill": "none"},
    "DISPLAY_D6": {"stroke": "black", "fill": "none"},
    "DISPLAY_D7": {"stroke": "black", "fill": "none"},
    "DISPLAY_D8": {"stroke": "black", "fill": "none"},
    "DISPLAY_D9": {"stroke": "black", "fill": "none"},
    "DISPLAY_D10": {"stroke": "black", "fill": "none"},
    "DISPLAY_D11": {"stroke": "black", "fill": "none"},
    "DISPLAY_D12": {"stroke": "black", "fill": "none"},
    "PATHS": {"stroke": "black", "fill": "none"},
    "GRAPHIC_PATTERNS": {"stroke": "black", "fill": "none"},
    "DIMENSIONS": {"stroke": "black", "fill": "none"},
    "LABELS": {"stroke": "black", "fill": "none"},
    "ZONE_GUIDES": {"stroke": "black", "fill": "none"},
    "OPENINGS": {"stroke": "black", "fill": "none"},
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _rect_x(obj: Dict[str, Any]) -> float:
    return _safe_float(obj.get("x", 0.0))


def _rect_y(obj: Dict[str, Any]) -> float:
    return _safe_float(obj.get("y", 0.0))


def _rect_length(obj: Dict[str, Any]) -> float:
    return _safe_float(obj.get("length", obj.get("w", 0.0)))


def _rect_width(obj: Dict[str, Any]) -> float:
    return _safe_float(obj.get("width", obj.get("h", 0.0)))


def _rect_center(obj: Dict[str, Any]) -> Tuple[float, float]:
    return (
        _rect_x(obj) + _rect_length(obj) / 2.0,
        _rect_y(obj) + _rect_width(obj) / 2.0,
    )


def _mm_to_svg_px(mm: float) -> float:
    return mm * 3.7795275591


def _pt_to_svg_px(pt: float) -> float:
    return pt * 1.3333333333


def _estimate_text_width_px(text: str, font_size_px: float) -> float:
    return max(1.0, len(text)) * font_size_px * 0.58


def _fit_center_label(
    obj: Dict[str, Any],
    text: str,
    preferred_pt: float,
    min_pt: float = 5.5,
    horizontal_margin_m: float = 0.08,
    vertical_margin_m: float = 0.05,
) -> Dict[str, Any]:
    available_length_m = max(0.0, _rect_length(obj) - 2 * horizontal_margin_m)
    available_width_m = max(0.0, _rect_width(obj) - 2 * vertical_margin_m)
    available_length_px = available_length_m * 100.0
    available_height_px = available_width_m * 100.0

    font_pt = preferred_pt
    while font_pt > min_pt:
        font_px = _pt_to_svg_px(font_pt)
        if _estimate_text_width_px(text, font_px) <= available_length_px and font_px <= available_height_px:
            break
        font_pt -= 0.5

    font_px = _pt_to_svg_px(font_pt)
    if _estimate_text_width_px(text, font_px) > available_length_px or font_px > available_height_px:
        return {"visible": False}

    cx, cy = _rect_center(obj)
    return {
        "visible": True,
        "shape": "text",
        "text": text,
        "x": cx,
        "y": cy,
        "font_size_pt": round(font_pt, 2),
        "anchor": "middle",
        "dominant_baseline": "central",
    }


def _stroke_style_for_layer(layer: str) -> Dict[str, Any]:
    style = dict(SVG_STYLE_BY_LAYER.get(layer, {"stroke": "black", "fill": "none"}))
    style["stroke_width_px"] = _mm_to_svg_px(LINEWEIGHTS_MM.get(layer, 0.18))
    if layer in DASH_PATTERNS:
        style["stroke_dasharray"] = DASH_PATTERNS[layer]
    return style


def _svg_rect(obj: Dict[str, Any], layer: str) -> str:
    style = _stroke_style_for_layer(layer)
    dash = f' stroke-dasharray="{style.get("stroke_dasharray")}"' if style.get("stroke_dasharray") else ""
    return (
        f'<rect x="{_rect_x(obj) * 100:.2f}" y="{-(_rect_y(obj) + _rect_width(obj)) * 100:.2f}" '
        f'width="{_rect_length(obj) * 100:.2f}" height="{_rect_width(obj) * 100:.2f}" '
        f'stroke="{style["stroke"]}" fill="{style["fill"]}" '
        f'stroke-width="{style["stroke_width_px"]:.2f}"{dash} />'
    )


def _svg_line(obj: Dict[str, Any], layer: str) -> str:
    style = _stroke_style_for_layer(layer)
    dash = f' stroke-dasharray="{style.get("stroke_dasharray")}"' if style.get("stroke_dasharray") else ""
    x1 = _safe_float(obj.get("x1", 0.0)) * 100.0
    y1 = -_safe_float(obj.get("y1", 0.0)) * 100.0
    x2 = _safe_float(obj.get("x2", 0.0)) * 100.0
    y2 = -_safe_float(obj.get("y2", 0.0)) * 100.0
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
        f'stroke="{style["stroke"]}" stroke-width="{style["stroke_width_px"]:.2f}"{dash} />'
    )


def _svg_text(label: Dict[str, Any], layer: str = "LABELS") -> str:
    if not label.get("visible", True):
        return ""
    style = _stroke_style_for_layer(layer)
    font_px = _pt_to_svg_px(_safe_float(label.get("font_size_pt", TEXT_SIZE_PT["fixture"])))
    x = _safe_float(label.get("x", 0.0)) * 100.0
    y = -_safe_float(label.get("y", 0.0)) * 100.0
    anchor = label.get("anchor", "middle")
    baseline = label.get("dominant_baseline", "central")
    text = escape(str(label.get("text", "")))
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{font_px:.2f}px" '
        f'text-anchor="{anchor}" dominant-baseline="{baseline}" '
        f'fill="{style["stroke"]}">{text}</text>'
    )


def _normalize_drawing_layers(drawing: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    return {key: list(value) for key, value in drawing.items() if isinstance(value, list)}


def _inject_center_labels(drawing_layers: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    labels = list(drawing_layers.get("LABELS", []))
    family_text = {
        "DISPLAY_WALL": None,
        "DISPLAY_GONDOLA": None,
        "DISPLAY_TABLE": "F8",
        "DISPLAY_MANNEQUIN": "F7",
        "INTERACTIVE_T1": "T1",
        "INTERACTIVE_T2": "T2",
        "INTERACTIVE_T3": "T3",
        "INTERACTIVE_T4": "T4",
        "INTERACTIVE_T5": "T5",
        "INTERACTIVE_T6": "T6",
        "INTERACTIVE_T7": "T7",
        "INTERACTIVE_T8": "T8",
        "INTERACTIVE_T9": "T9",
        "FITTING_ROOMS": "FITTING",
    }

    for layer_name in ["DISPLAY_WALL", "DISPLAY_GONDOLA", "DISPLAY_TABLE", "DISPLAY_MANNEQUIN", "INTERACTIVE_T1", "INTERACTIVE_T2", "INTERACTIVE_T3", "INTERACTIVE_T4", "INTERACTIVE_T5", "INTERACTIVE_T6", "INTERACTIVE_T7", "INTERACTIVE_T8", "INTERACTIVE_T9", "FITTING_ROOMS"]:
        for obj in drawing_layers.get(layer_name, []):
            if not isinstance(obj, dict) or obj.get("draw_mode") != "closed_polygon":
                continue
            if layer_name == "DISPLAY_GONDOLA":
                family = str(obj.get("family", "")).upper()
                text = family if family in {"F4", "F5", "F6"} else ("RACK" if "rack" in str(obj.get("graphic_class", "")).lower() else "GONDOLA")
            elif layer_name == "DISPLAY_WALL":
                family = str(obj.get("family", "")).upper()
                text = family if family in {"F1", "F2", "F3"} else family_text[layer_name]
            else:
                text = family_text[layer_name]
            if not text:
                continue
            preferred_pt = TEXT_SIZE_PT["fixture"] if layer_name != "FITTING_ROOMS" else TEXT_SIZE_PT["small"]
            fitted = _fit_center_label(obj, text, preferred_pt=preferred_pt)
            if fitted.get("visible"):
                fitted["source_layer"] = layer_name
                labels.append(fitted)

    drawing_layers["LABELS"] = labels
    return drawing_layers


def build_svg_payload(drawing: Dict[str, List[Dict[str, Any]]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    layers = _normalize_drawing_layers(drawing)
    layers = _inject_center_labels(layers)

    max_x = 0.0
    max_y = 0.0
    for layer_items in layers.values():
        for obj in layer_items:
            if isinstance(obj, dict):
                max_x = max(max_x, _rect_x(obj) + _rect_length(obj), _safe_float(obj.get("x1", 0.0)), _safe_float(obj.get("x2", 0.0)))
                max_y = max(max_y, _rect_y(obj) + _rect_width(obj), _safe_float(obj.get("y1", 0.0)), _safe_float(obj.get("y2", 0.0)))

    margin_px = 80.0
    view_w = max(700.0, max_x * 100.0 + 2 * margin_px)
    view_h = max(500.0, max_y * 100.0 + 2 * margin_px)
    svg_parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" viewBox="{-margin_px:.0f} {-view_h + margin_px:.0f} {view_w:.0f} {view_h:.0f}">'
    ]

    ordered_layers = [
        "WALL_EXT", "WALL_GLASS", "WALL_INT", "WALL_BOH", "WALL_FITTING", "OPENINGS",
        "ZONE_GUIDES", "ADDED_ZONES", "FITTING_AREA_BUFFER", "CHECKOUT_BUFFER", "CHECKOUT_COUNTER", "CHECKOUT_STAFF_BUFFER",
        "DISPLAY_D1", "DISPLAY_D2", "DISPLAY_D3", "DISPLAY_D4", "DISPLAY_D5", "DISPLAY_D6", "DISPLAY_D7", "DISPLAY_D8", "DISPLAY_D9", "DISPLAY_D10", "DISPLAY_D11", "DISPLAY_D12",
        "FITTING_ROOMS",
        "DISPLAY_WALL_BUFFER", "DISPLAY_WALL", "DISPLAY_GONDOLA_BUFFER", "DISPLAY_GONDOLA", "DISPLAY_TABLE_BUFFER_MIN", "DISPLAY_TABLE_BUFFER", "DISPLAY_TABLE", "DISPLAY_MANNEQUIN_BUFFER", "DISPLAY_MANNEQUIN",
        "INTERACTIVE_T1_BUFFER", "INTERACTIVE_T1_BUFFER_MIN", "INTERACTIVE_T1",
        "INTERACTIVE_T2_BUFFER", "INTERACTIVE_T2_BUFFER_MIN", "INTERACTIVE_T2",
        "INTERACTIVE_T3_BUFFER", "INTERACTIVE_T3_BUFFER_MIN", "INTERACTIVE_T3",
        "INTERACTIVE_T4_BUFFER", "INTERACTIVE_T4_BUFFER_MIN", "INTERACTIVE_T4",
        "INTERACTIVE_T5_BUFFER", "INTERACTIVE_T5_BUFFER_MIN", "INTERACTIVE_T5",
        "INTERACTIVE_T6_BUFFER", "INTERACTIVE_T6_BUFFER_MIN", "INTERACTIVE_T6",
        "INTERACTIVE_T7_BUFFER", "INTERACTIVE_T7_BUFFER_MIN", "INTERACTIVE_T7",
        "INTERACTIVE_T8_BUFFER", "INTERACTIVE_T8_BUFFER_MIN", "INTERACTIVE_T8",
        "INTERACTIVE_T9_BUFFER", "INTERACTIVE_T9_BUFFER_MIN", "INTERACTIVE_T9",
        "PATHS", "GRAPHIC_PATTERNS", "DIMENSIONS", "LABELS",
    ]

    for layer_name in ordered_layers:
        if layer_name not in layers:
            continue
        svg_parts.append(f'<g id="{escape(layer_name)}">')
        for obj in layers[layer_name]:
            if not isinstance(obj, dict):
                continue
            kind = obj.get("shape", obj.get("type", obj.get("entity", "rect")))
            if kind in {"wall", "line", "opening_line"} or all(k in obj for k in ("x1", "y1", "x2", "y2")):
                svg_parts.append(_svg_line(obj, layer_name))
            elif kind == "text" or "text" in obj:
                svg_parts.append(_svg_text(obj, layer_name))
            else:
                svg_parts.append(_svg_rect(obj, layer_name))
        svg_parts.append("</g>")
    svg_parts.append("</svg>")

    layer_styles = {
        layer: {"lineweight_mm": LINEWEIGHTS_MM.get(layer, 0.18), "dash": DASH_PATTERNS.get(layer)}
        for layer in ordered_layers if layer in layers
    }

    return {
        "canvas": {"width_px": round(view_w, 2), "height_px": round(view_h, 2)},
        "layer_styles": layer_styles,
        "layers": layers,
        "svg_markup": "\n".join(part for part in svg_parts if part),
    }


def render_png_bytes(drawing: Dict[str, List[Dict[str, Any]]], params: Optional[Dict[str, Any]] = None, output_width_px: int = 2400) -> bytes:
    """Render the current plan to PNG bytes for Streamlit download.

    Preferred path uses CairoSVG when available. If CairoSVG is not installed
    on the user's machine, a lightweight Pillow fallback draws the same core
    layer geometry directly. This keeps the PNG button usable without adding
    a hard dependency that can break the application import.
    """
    svg_payload = build_svg_payload(drawing, params)
    svg_markup = svg_payload.get("svg_markup", "")
    canvas = svg_payload.get("canvas", {}) if isinstance(svg_payload, dict) else {}
    view_w = max(1.0, float(canvas.get("width_px", 1200.0) or 1200.0))
    view_h = max(1.0, float(canvas.get("height_px", 900.0) or 900.0))
    output_width_px = max(800, int(output_width_px or 2400))
    output_height_px = max(600, int(round(output_width_px * (view_h / view_w))))

    try:
        import cairosvg  # type: ignore
        return cairosvg.svg2png(
            bytestring=svg_markup.encode("utf-8"),
            output_width=output_width_px,
            output_height=output_height_px,
        )
    except Exception:
        pass

    # Dependency-light fallback: draw rectangles, lines and labels with Pillow.
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont

    layers = svg_payload.get("layers", {}) if isinstance(svg_payload, dict) else _normalize_drawing_layers(drawing)
    scale = output_width_px / view_w
    margin_px = 80.0

    def tx(x: float) -> float:
        return (x * 100.0 + margin_px) * scale

    def ty(y: float) -> float:
        return (view_h - margin_px - y * 100.0) * scale

    image = Image.new("RGB", (output_width_px, output_height_px), "white")
    draw = ImageDraw.Draw(image)

    ordered_layers = [
        "WALL_EXT", "WALL_GLASS", "WALL_INT", "WALL_BOH", "WALL_FITTING", "OPENINGS",
        "ZONE_GUIDES", "ADDED_ZONES", "FITTING_AREA_BUFFER", "CHECKOUT_BUFFER", "CHECKOUT_COUNTER", "CHECKOUT_STAFF_BUFFER",
        "DISPLAY_D1", "DISPLAY_D2", "DISPLAY_D3", "DISPLAY_D4", "DISPLAY_D5", "DISPLAY_D6", "DISPLAY_D7", "DISPLAY_D8", "DISPLAY_D9", "DISPLAY_D10", "DISPLAY_D11", "DISPLAY_D12",
        "FITTING_ROOMS",
        "DISPLAY_WALL_BUFFER", "DISPLAY_WALL", "DISPLAY_GONDOLA_BUFFER", "DISPLAY_GONDOLA", "DISPLAY_TABLE_BUFFER_MIN", "DISPLAY_TABLE_BUFFER", "DISPLAY_TABLE", "DISPLAY_MANNEQUIN_BUFFER", "DISPLAY_MANNEQUIN",
        "INTERACTIVE_T1_BUFFER", "INTERACTIVE_T1_BUFFER_MIN", "INTERACTIVE_T1",
        "INTERACTIVE_T2_BUFFER", "INTERACTIVE_T2_BUFFER_MIN", "INTERACTIVE_T2",
        "INTERACTIVE_T3_BUFFER", "INTERACTIVE_T3_BUFFER_MIN", "INTERACTIVE_T3",
        "INTERACTIVE_T4_BUFFER", "INTERACTIVE_T4_BUFFER_MIN", "INTERACTIVE_T4",
        "INTERACTIVE_T5_BUFFER", "INTERACTIVE_T5_BUFFER_MIN", "INTERACTIVE_T5",
        "INTERACTIVE_T6_BUFFER", "INTERACTIVE_T6_BUFFER_MIN", "INTERACTIVE_T6",
        "INTERACTIVE_T7_BUFFER", "INTERACTIVE_T7_BUFFER_MIN", "INTERACTIVE_T7",
        "INTERACTIVE_T8_BUFFER", "INTERACTIVE_T8_BUFFER_MIN", "INTERACTIVE_T8",
        "INTERACTIVE_T9_BUFFER", "INTERACTIVE_T9_BUFFER_MIN", "INTERACTIVE_T9",
        "PATHS", "GRAPHIC_PATTERNS", "DIMENSIONS", "LABELS",
    ]

    fill_map = {
        "INTERACTIVE_T1": "red", "INTERACTIVE_T2": "green", "INTERACTIVE_T3": "blue",
        "INTERACTIVE_T4": "yellow", "INTERACTIVE_T5": "magenta", "INTERACTIVE_T6": "cyan",
        "INTERACTIVE_T7": "purple", "INTERACTIVE_T8": "orange", "INTERACTIVE_T9": "cyan",
        "WALL_EXT": "black",
    }

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", max(8, int(12 * scale)))
    except Exception:
        font = ImageFont.load_default()

    for layer_name in ordered_layers:
        for obj in (layers.get(layer_name, []) if isinstance(layers, dict) else []):
            if not isinstance(obj, dict):
                continue
            kind = obj.get("shape", obj.get("type", obj.get("entity", "rect")))
            line_w = max(1, int(round(_mm_to_svg_px(LINEWEIGHTS_MM.get(layer_name, 0.18)) * scale)))
            if kind in {"wall", "line", "opening_line"} or all(k in obj for k in ("x1", "y1", "x2", "y2")):
                draw.line((tx(_safe_float(obj.get("x1", 0.0))), ty(_safe_float(obj.get("y1", 0.0))), tx(_safe_float(obj.get("x2", 0.0))), ty(_safe_float(obj.get("y2", 0.0)))), fill="black", width=line_w)
            elif kind == "text" or "text" in obj:
                text = str(obj.get("text", ""))
                x = tx(_safe_float(obj.get("x", 0.0)))
                y = ty(_safe_float(obj.get("y", 0.0)))
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                except Exception:
                    tw, th = len(text) * 6, 10
                draw.text((x - tw / 2, y - th / 2), text, fill="black", font=font)
            else:
                x1 = tx(_rect_x(obj)); y1 = ty(_rect_y(obj) + _rect_width(obj))
                x2 = tx(_rect_x(obj) + _rect_length(obj)); y2 = ty(_rect_y(obj))
                fill = fill_map.get(layer_name, None)
                if fill == "black":
                    draw.rectangle((x1, y1, x2, y2), outline="black", fill="black", width=line_w)
                else:
                    draw.rectangle((x1, y1, x2, y2), outline="black", fill=fill, width=line_w)

    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _dxf_layer_name(base_layer: str, obj: Dict[str, Any]) -> str:
    if base_layer == "DIMENSIONS":
        return f"DIM_{str(obj.get('dim_class', 'general')).upper()}"
    if base_layer == "GRAPHIC_PATTERNS":
        return f"PATTERN_{str(obj.get('pattern_class', 'GENERIC')).upper()}"
    if base_layer == "DISPLAY_GONDOLA":
        return f"DISPLAY_{str(obj.get('graphic_class', 'GONDOLA')).upper()}"
    return base_layer


def build_dxf_payload(drawing: Dict[str, List[Dict[str, Any]]], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    layers = _normalize_drawing_layers(drawing)
    layers = _inject_center_labels(layers)
    dxf_layers: Dict[str, Dict[str, Any]] = {}
    entities: List[Dict[str, Any]] = []
    for base_layer, items in layers.items():
        for obj in items:
            if not isinstance(obj, dict):
                continue
            layer_name = _dxf_layer_name(base_layer, obj)
            if layer_name not in dxf_layers:
                dxf_layers[layer_name] = {
                    "name": layer_name,
                    "lineweight_mm": LINEWEIGHTS_MM.get(base_layer, 0.18),
                    "dash": DASH_PATTERNS.get(base_layer),
                    "text_size_pt": TEXT_SIZE_PT.get("fixture", 9.0),
                }
            kind = obj.get("shape", obj.get("type", obj.get("entity", "rect")))
            if kind in {"wall", "line", "opening_line"} or all(k in obj for k in ("x1", "y1", "x2", "y2")):
                entities.append({"entity": "LINE", "layer": layer_name, "x1": _safe_float(obj.get("x1", 0.0)), "y1": _safe_float(obj.get("y1", 0.0)), "x2": _safe_float(obj.get("x2", 0.0)), "y2": _safe_float(obj.get("y2", 0.0))})
            elif kind == "text" or "text" in obj:
                entities.append({"entity": "TEXT", "layer": layer_name, "x": _safe_float(obj.get("x", 0.0)), "y": _safe_float(obj.get("y", 0.0)), "text": str(obj.get("text", "")), "height_pt": _safe_float(obj.get("font_size_pt", TEXT_SIZE_PT["fixture"])), "align": obj.get("anchor", "middle")})
            else:
                x = _rect_x(obj); y = _rect_y(obj); length = _rect_length(obj); width = _rect_width(obj)
                entities.append({"entity": "LWPOLYLINE_CLOSED", "layer": layer_name, "points": [[x, y], [x+length, y], [x+length, y+width], [x, y+width]]})
    return {"layers": dxf_layers, "entities": entities}


def build_baseline_json_payload(state: Any) -> Dict[str, Any]:
    return {
        "status": getattr(state, "status", None),
        "inputs": getattr(state, "inputs", {}),
        "shell": getattr(state, "shell", {}),
        "zones": getattr(state, "zones", {}),
        "bands": getattr(state, "bands", {}),
        "display": getattr(state, "display", {}),
        "validation": getattr(state, "validation", {}),
        "drawing_summary": getattr(state, "drawing", {}).get("DRAWING_SUMMARY", []) if isinstance(getattr(state, "drawing", {}), dict) else [],
    }


def build_baseline_report_payload(state: Any) -> Dict[str, Any]:
    inputs = getattr(state, "inputs", {})
    shell = getattr(state, "shell", {})
    zones = getattr(state, "zones", {})
    validation = getattr(state, "validation", {})
    display = getattr(state, "display", {})

    zone_schedule = {}
    for name in ("decompression", "sales", "fitting", "checkout", "back_of_house"):
        zone = zones.get(name)
        if isinstance(zone, dict):
            zone_schedule[name] = {
                "x": _rect_x(zone), "y": _rect_y(zone), "length": _rect_length(zone), "width": _rect_width(zone),
                "area_m2": round(_rect_length(zone) * _rect_width(zone), 3),
            }

    return {
        "title": "Fashion Store Layout – Baseline Plan",
        "scale_note": "Scale: 1:100",
        "input_summary": inputs,
        "derived_geometry": {"store_length_m": shell.get("length_m"), "store_width_m": shell.get("width_m"), "store_area_m2": shell.get("area_m2")},
        "zone_schedule": zone_schedule,
        "fitting_checkout_decisions": {"fitting_position": inputs.get("fitting_position"), "checkout_position": inputs.get("checkout_position"), "fitting_size_preset": inputs.get("fitting_room_size_preset")},
        "display_counts": display.get("summary", {}),
        "circulation_summary": {"primary_path_width_m": inputs.get("primary_path_width_m")},
        "validation_results": validation,
        "warnings_assumptions": validation.get("soft_flags", []),
        "traceable_parameter_summary": {"lineweights_mm": LINEWEIGHTS_MM, "text_sizes_pt": TEXT_SIZE_PT, "dash_patterns": DASH_PATTERNS},
    }


def assemble_baseline_export_payloads(state: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    drawing = getattr(state, "drawing", {}) if state is not None else {}
    return {
        "svg_payload": build_svg_payload(drawing, params),
        "dxf_payload": build_dxf_payload(drawing, params),
        "json_payload": build_baseline_json_payload(state),
        "report_payload": build_baseline_report_payload(state),
    }


def _dxf_escape_text(value: Any) -> str:
    return str(value).replace("\n", " ")


def render_dxf_bytes(drawing: Dict[str, List[Dict[str, Any]]], params: Optional[Dict[str, Any]] = None) -> bytes:
    """Render a conservative ASCII DXF that opens reliably in AutoCAD.

    This writer intentionally targets a simple R12-style entity set (LINE/TEXT)
    instead of lightweight polylines. It is more verbose but significantly more
    tolerant across CAD viewers and avoids the recovery prompt the prior export
    triggered.
    """
    payload = build_dxf_payload(drawing, params)

    def pair(code: int, value: Any) -> str:
        return f"{code}\n{value}\n"

    def add_line(out: List[str], layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        out += [
            pair(0, 'LINE'),
            pair(8, layer),
            pair(10, float(x1)), pair(20, float(y1)), pair(30, 0.0),
            pair(11, float(x2)), pair(21, float(y2)), pair(31, 0.0),
        ]

    out: List[str] = []
    layers = payload.get('layers', {}) or {}
    entities = payload.get('entities', []) or []

    out += [
        pair(0, 'SECTION'), pair(2, 'HEADER'),
        pair(9, '$ACADVER'), pair(1, 'AC1009'),
        pair(9, '$INSBASE'), pair(10, 0.0), pair(20, 0.0), pair(30, 0.0),
        pair(9, '$EXTMIN'), pair(10, 0.0), pair(20, 0.0), pair(30, 0.0),
        pair(9, '$EXTMAX'), pair(10, 1000.0), pair(20, 1000.0), pair(30, 0.0),
        pair(0, 'ENDSEC'),
    ]

    out += [pair(0, 'SECTION'), pair(2, 'TABLES')]
    out += [pair(0, 'TABLE'), pair(2, 'LAYER'), pair(70, max(1, len(layers) + 1))]
    out += [pair(0, 'LAYER'), pair(2, '0'), pair(70, 0), pair(62, 7), pair(6, 'CONTINUOUS')]
    for lname in layers:
        out += [pair(0, 'LAYER'), pair(2, lname), pair(70, 0), pair(62, 7), pair(6, 'CONTINUOUS')]
    out += [pair(0, 'ENDTAB'), pair(0, 'ENDSEC')]

    out += [pair(0, 'SECTION'), pair(2, 'ENTITIES')]
    for ent in entities:
        etype = ent.get('entity')
        layer = ent.get('layer', '0')
        if etype == 'LINE':
            add_line(out, layer, ent.get('x1', 0.0), ent.get('y1', 0.0), ent.get('x2', 0.0), ent.get('y2', 0.0))
        elif etype == 'TEXT':
            text_h = max(0.15, float(ent.get('height_pt', 9.0)) * 0.3528 / 2.5)
            out += [
                pair(0, 'TEXT'),
                pair(8, layer),
                pair(10, float(ent.get('x', 0.0))), pair(20, float(ent.get('y', 0.0))), pair(30, 0.0),
                pair(40, text_h),
                pair(1, _dxf_escape_text(ent.get('text', ''))),
            ]
        elif etype == 'LWPOLYLINE_CLOSED':
            pts = ent.get('points', []) or []
            if len(pts) >= 2:
                for i, (x1, y1) in enumerate(pts):
                    x2, y2 = pts[(i + 1) % len(pts)]
                    add_line(out, layer, x1, y1, x2, y2)
    out += [pair(0, 'ENDSEC'), pair(0, 'EOF')]
    return ''.join(out).encode('ascii', errors='replace')
