from __future__ import annotations

from io import BytesIO
import re
from typing import Any, Dict, List

from PIL import Image as PILImage, ImageDraw, ImageFont

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image, PageBreak


def _rect_area(rect: dict | None) -> float:
    if not isinstance(rect, dict):
        return 0.0
    return float(rect.get("length", 0.0)) * float(rect.get("width", 0.0))




def _normalize_family_name(name: str) -> str:
    fam = str(name or '').strip().upper()
    return 'F7' if fam.startswith('F7') else fam


def _infer_f_family(obj: Dict[str, Any]) -> str:
    fam_raw = _normalize_family_name(obj.get('family', ''))
    if fam_raw in {f'F{i}' for i in range(1, 9)}:
        return fam_raw

    variant = str(obj.get('variant', '') or '').strip().lower()
    subfamily = str(obj.get('subfamily', '') or '').strip().lower()
    length = float(obj.get('length', 0.0) or 0.0)
    width = float(obj.get('width', 0.0) or 0.0)
    depth = min(length, width) if length and width else 0.0

    if fam_raw == 'WALL_BAYS':
        if variant == 'shirts_wall_bay':
            return 'F1'
        if variant == 'coats_wall_bay':
            return 'F2'
        if variant in {'folded_apparel_wall_bay', 'freestanding_wall_bay'}:
            return 'F3'
        if depth <= 0.35 + 1e-6:
            return 'F1'
        if depth <= 0.45 + 1e-6:
            return 'F2'
        return 'F3'

    if fam_raw == 'GONDOLA_RACK_SYSTEM':
        if variant == 'double_sided_gondola':
            return 'F4'
        if variant in {'single_sided_gondola', 'shirts_straight_rack', 'coats_straight_rack'}:
            return 'F5'
        if variant == 'two_way_rack':
            return 'F6'
        if subfamily == 'rack':
            return 'F5'
        if subfamily == 'gondola':
            return 'F4' if max(length, width) >= 1.0 and min(length, width) >= 0.9 else 'F5'

    if fam_raw == 'TABLES':
        return 'F8'
    if fam_raw == 'MANNEQUINS':
        return 'F7'
    return fam_raw


def _f_family_label_map() -> Dict[str, str]:
    return {
        'F1': 'Wall bay — shirts',
        'F2': 'Wall bay — coats',
        'F3': 'Wall bay — folded apparel',
        'F4': 'Double-sided gondola — apparel display',
        'F5': 'Single-sided rack — hanging apparel',
        'F6': 'Square island rack — central display',
        'F7': 'Mannequin display — feature presentation',
        'F8': 'Display table — folded / featured products',
    }


def _t_family_label_map() -> Dict[str, str]:
    return {
        'T1': 'Interactive screen',
        'T2': 'Interactive kiosk',
        'T3': 'Smart / magic mirror',
        'T4': 'Free-standing smart / magic mirror',
        'T5': '3D body scanner',
        'T6': 'Seated VR station',
        'T7': 'Standing VR station',
        'T8': 'Express checkout',
        'T9': 'Fixed self-checkout',
    }


def _normalize_t_family_name(name: str) -> str:
    fam = str(name or '').strip().upper().split('.')[0]
    return fam if fam in {f'T{i}' for i in range(1, 10)} else fam


def _build_t_family_rows(interactive_items: List[Dict[str, Any]] | None = None, interactive_counts: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    labels = _t_family_label_map()
    rows: Dict[str, Dict[str, Any]] = {
        fam: {"family": fam, "label": labels[fam], "width_m": None, "depth_m": None, "count": 0}
        for fam in [f'T{i}' for i in range(1, 10)]
    }
    if interactive_counts:
        for raw_fam, raw_count in interactive_counts.items():
            fam = _normalize_t_family_name(raw_fam)
            if fam in rows:
                rows[fam]["count"] = int(raw_count or 0)
    for obj in (interactive_items or []):
        if not isinstance(obj, dict):
            continue
        fam = _normalize_t_family_name(obj.get('family', ''))
        if fam not in rows:
            continue
        row = rows[fam]
        if not interactive_counts:
            row['count'] += 1
        if row['width_m'] is None and all(k in obj for k in ('length', 'width')):
            row['width_m'] = float(obj.get('length', 0.0) or 0.0)
            row['depth_m'] = float(obj.get('width', 0.0) or 0.0)
    return [rows[fam] for fam in [f'T{i}' for i in range(1, 10)] if rows[fam]['count'] > 0]


def _iter_fixture_objs(fixture_lists: Dict[str, List[Dict[str, Any]]] | None = None, fixture_items: List[Dict[str, Any]] | None = None):
    if fixture_items:
        for obj in fixture_items:
            if isinstance(obj, dict):
                yield obj
    for items in (fixture_lists or {}).values():
        for obj in items or []:
            if isinstance(obj, dict):
                yield obj


def _build_f_family_rows(fixture_lists: Dict[str, List[Dict[str, Any]]] | None = None, fixture_items: List[Dict[str, Any]] | None = None, fixture_counts: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    labels = _f_family_label_map()
    rows: Dict[str, Dict[str, Any]] = {
        fam: {"family": fam, "label": labels[fam], "width_m": None, "depth_m": None, "count": 0}
        for fam in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]
    }
    if fixture_counts:
        for raw_fam, raw_count in fixture_counts.items():
            fam = _normalize_family_name(raw_fam)
            if fam in rows:
                rows[fam]["count"] = int(raw_count or 0)
    for obj in _iter_fixture_objs(fixture_lists, fixture_items):
        fam = _infer_f_family(obj)
        if fam not in rows:
            continue
        row = rows[fam]
        if not fixture_counts:
            row["count"] += 1
        if row["width_m"] is None and all(k in obj for k in ("length", "width")):
            row["width_m"] = float(obj.get("length", 0.0))
            row["depth_m"] = float(obj.get("width", 0.0))
    return [rows[fam] for fam in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]]



def _dash_line(draw: ImageDraw.ImageDraw, p1, p2, dash_px: int = 8, gap_px: int = 6, fill=(120,120,120), width: int = 1):
    x1, y1 = p1; x2, y2 = p2
    dx = x2 - x1; dy = y2 - y1
    dist = max((dx*dx + dy*dy) ** 0.5, 1e-6)
    ux, uy = dx / dist, dy / dist
    pos = 0.0
    while pos < dist:
        seg_end = min(pos + dash_px, dist)
        sx1, sy1 = x1 + ux * pos, y1 + uy * pos
        sx2, sy2 = x1 + ux * seg_end, y1 + uy * seg_end
        draw.line((sx1, sy1, sx2, sy2), fill=fill, width=width)
        pos += dash_px + gap_px


def _render_preview_png_from_layers(drawing_layers: Dict[str, List[Dict[str, Any]]] | None) -> bytes | None:
    if not isinstance(drawing_layers, dict) or not drawing_layers:
        return None

    max_x = 0.0
    max_y = 0.0
    for items in drawing_layers.values():
        for obj in items or []:
            if not isinstance(obj, dict):
                continue
            if all(k in obj for k in ('x','y','length','width')):
                max_x = max(max_x, float(obj.get('x',0))+float(obj.get('length',0)))
                max_y = max(max_y, float(obj.get('y',0))+float(obj.get('width',0)))
            if all(k in obj for k in ('x1','y1','x2','y2')):
                max_x = max(max_x, float(obj.get('x1',0)), float(obj.get('x2',0)))
                max_y = max(max_y, float(obj.get('y1',0)), float(obj.get('y2',0)))
    if max_x <= 0 or max_y <= 0:
        return None

    scale = 40
    margin = 40
    img_w = int(max_x * scale + margin * 2)
    img_h = int(max_y * scale + margin * 2)
    img = PILImage.new('RGB', (img_w, img_h), 'white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    def tx(x):
        return margin + float(x) * scale
    def ty(y):
        return img_h - margin - float(y) * scale

    ordered_layers = [
        'WALL_EXT','WALL_GLASS','WALL_INT','WALL_BOH','WALL_FITTING','OPENINGS',
        'ZONE_GUIDES','ADDED_ZONES','FITTING_AREA_BUFFER','CHECKOUT_BUFFER','CHECKOUT_COUNTER','CHECKOUT_STAFF_BUFFER',
        'DISPLAY_D1','DISPLAY_D2','DISPLAY_D3','DISPLAY_D4','DISPLAY_D5','DISPLAY_D6','DISPLAY_D7','DISPLAY_D8','DISPLAY_D9','DISPLAY_D10','DISPLAY_D11','DISPLAY_D12',
        'FITTING_ROOMS','DISPLAY_WALL_BUFFER','DISPLAY_WALL','DISPLAY_GONDOLA_BUFFER','DISPLAY_GONDOLA','DISPLAY_TABLE_BUFFER_MIN','DISPLAY_TABLE_BUFFER','DISPLAY_TABLE','DISPLAY_MANNEQUIN_BUFFER','DISPLAY_MANNEQUIN',
    ] + [f'INTERACTIVE_T{i}_BUFFER' for i in range(1,10)] + [f'INTERACTIVE_T{i}_BUFFER_MIN' for i in range(1,10)] + [f'INTERACTIVE_T{i}' for i in range(1,10)] + ['PATHS','DIMENSIONS','LABELS']

    for layer in ordered_layers:
        for obj in drawing_layers.get(layer, []) or []:
            if not isinstance(obj, dict):
                continue
            dashed = ('BUFFER' in layer) or layer in {'PATHS','ZONE_GUIDES','FITTING_AREA_BUFFER','CHECKOUT_BUFFER','CHECKOUT_STAFF_BUFFER'}
            width = 1 if dashed else (4 if layer == 'WALL_EXT' else 2)
            color = (0,0,0)
            if dashed:
                color = (150,150,150)
            if layer == 'WALL_EXT' and all(k in obj for k in ('x','y','length','width')):
                x1 = tx(obj['x']); x2 = tx(float(obj['x']) + float(obj['length']))
                y1 = ty(float(obj['y']) + float(obj['width'])); y2 = ty(obj['y'])
                draw.rectangle((x1,y1,x2,y2), outline=(0,0,0), fill=(0,0,0), width=1)
                continue
            if all(k in obj for k in ('x1','y1','x2','y2')):
                p1=(tx(obj['x1']), ty(obj['y1'])); p2=(tx(obj['x2']), ty(obj['y2']))
                if dashed:
                    _dash_line(draw,p1,p2,fill=color,width=width)
                else:
                    draw.line((*p1,*p2), fill=color, width=width)
            elif all(k in obj for k in ('x','y','length','width')):
                x1 = tx(obj['x']); x2 = tx(float(obj['x']) + float(obj['length']))
                y1 = ty(float(obj['y']) + float(obj['width'])); y2 = ty(obj['y'])
                if dashed:
                    # rect dashed
                    _dash_line(draw,(x1,y1),(x2,y1),fill=color,width=width)
                    _dash_line(draw,(x2,y1),(x2,y2),fill=color,width=width)
                    _dash_line(draw,(x2,y2),(x1,y2),fill=color,width=width)
                    _dash_line(draw,(x1,y2),(x1,y1),fill=color,width=width)
                else:
                    fill = None
                    if layer.startswith('INTERACTIVE_T') and 'BUFFER' not in layer:
                        fam = str(obj.get('family','')).upper().split('.')[0]
                        cmap = {'T1':(0,0,255),'T2':(255,255,0),'T3':(255,0,0),'T4':(255,0,255),'T5':(128,0,128),'T6':(0,255,255),'T7':(0,128,0),'T8':(255,165,0),'T9':(255,0,0)}
                        fill = cmap.get(fam,(220,220,220))
                    draw.rectangle((x1,y1,x2,y2), outline=color, fill=fill, width=width)
            if ('text' in obj or obj.get('shape')=='text') and font is not None:
                text = str(obj.get('text','')).strip()
                if text:
                    x = tx(obj.get('x',0)); y = ty(obj.get('y',0))
                    draw.text((x,y), text, fill=(80,80,80), font=font, anchor='mm')

    out = BytesIO()
    img.save(out, format='PNG')
    return out.getvalue()

def build_baseline_report_payload(state) -> dict:
    zones = state.zones or {}
    validation = state.validation or {}
    band_summary = validation.get("band_summary", {})
    zoning_meta = validation.get("zoning_meta", {})

    zone_schedule = {}
    for key, zone in zones.items():
        if key.startswith("_") or not isinstance(zone, dict):
            continue
        if all(k in zone for k in ("x", "y", "length", "width")):
            zone_schedule[key] = {
                "area_m2": round(zone["length"] * zone["width"], 3),
                "x": round(zone["x"], 3),
                "y": round(zone["y"], 3),
                "length": round(zone["length"], 3),
                "width": round(zone["width"], 3),
            }

    return {
        "status": state.status,
        "inputs": state.inputs,
        "shell": {
            "area_m2": state.shell.get("area_m2") if state.shell else None,
            "length_m": state.shell.get("length_m") if state.shell else None,
            "width_m": state.shell.get("width_m") if state.shell else None,
        },
        "zone_schedule": zone_schedule,
        "zoning_meta": zoning_meta,
        "fitting_summary": validation.get("fitting_summary", {}),
        "fitting_room_size_preset": (validation.get("fitting_summary", {}) or {}).get("room_size_preset"),
        "band_summary": band_summary,
        "validation_checks": validation.get("checks", {}),
        "validation_soft_flags": validation.get("soft_flags", []),
        "band_errors": validation.get("band_errors", []),
        "display_summary": validation.get("display_summary", {}),
        "display_variant_counts": validation.get("display_summary", {}).get("variant_counts", {}),
    }


def build_zone_ratio_report_payload(shell: Dict[str, Any], zoning: Dict[str, Any], store_band: str, program_intent_ui: str, added: Dict[str, Any] | None = None, display_classes: Dict[str, Any] | None = None, fixture_lists: Dict[str, List[Dict[str, Any]]] | None = None, fixture_items: List[Dict[str, Any]] | None = None, fixture_counts: Dict[str, Any] | None = None, interactive_items: List[Dict[str, Any]] | None = None, interactive_counts: Dict[str, Any] | None = None, preview_drawing_layers: Dict[str, List[Dict[str, Any]]] | None = None) -> Dict[str, Any]:
    net_rect = (shell or {}).get("inner_clear_boundary", {})
    total_net_area = _rect_area(net_rect)

    def pct(area: float, total: float) -> float:
        return round((area / total) * 100.0, 2) if total > 0 else 0.0

    zone_rows = []
    for key, zone in (zoning or {}).items():
        if key.startswith("_") or not isinstance(zone, dict):
            continue
        if all(k in zone for k in ("x", "y", "length", "width")):
            area = round(_rect_area(zone), 3)
            zone_rows.append({
                "zone_key": key,
                "zone_label": key.replace("_", " ").upper(),
                "area_m2": area,
                "share_pct": pct(area, total_net_area),
            })

    preferred_order = [
        "entry_zone",
        "frontage_zone_left",
        "frontage_zone_right",
        "sales_zone",
        "checkout_zone",
        "fitting_zone",
        "boh_zone",
        "service_connector",
    ]
    rank = {name: i for i, name in enumerate(preferred_order)}
    zone_rows.sort(key=lambda r: (rank.get(r["zone_key"], 999), r["zone_key"]))



    display_island_area_m2 = 0.0
    for key in [f"D{i}" for i in range(1, 13)]:
        for item in (display_classes or {}).get(key, []):
            rect = item.get("rect") if isinstance(item, dict) else None
            if isinstance(rect, dict):
                display_island_area_m2 += _rect_area(rect)
    display_island_area_m2 = round(display_island_area_m2, 3)

    f_family_rows = _build_f_family_rows(fixture_lists, fixture_items, fixture_counts)
    t_family_rows = _build_t_family_rows(interactive_items, interactive_counts)

    added_meta = (added or {}).get("report_meta", {}) if isinstance(added, dict) else {}
    added_zone_rows: List[Dict[str, Any]] = list(added_meta.get("added_zone_rows", []))
    removed_fixture_ids: List[str] = list(added_meta.get("removed_fixture_ids", []))

    plan_preview_png = _render_preview_png_from_layers(preview_drawing_layers)

    return {
        "title": "Baseline Zone Ratio Report",
        "store_band": str(store_band).upper(),
        "program_intent": program_intent_ui,
        "total_net_area_m2": round(total_net_area, 3),
        "zone_rows": zone_rows,
        "display_island_area_m2": display_island_area_m2,
        "display_island_share_pct": pct(display_island_area_m2, total_net_area),
        "f_family_rows": f_family_rows,
        "t_family_rows": t_family_rows,
        "plan_preview_png": plan_preview_png,
        "added_display_area_m2": float(added_meta.get("display_area_m2", 0.0) or 0.0),
        "added_zone_rows": added_zone_rows,
        "total_added_area_m2": float(added_meta.get("total_added_area_m2", 0.0) or 0.0),
        "total_added_share_pct": float(added_meta.get("total_added_share_pct", 0.0) or 0.0),
        "removed_fixture_ids": removed_fixture_ids,
        "removed_fixture_count": int(added_meta.get("removed_fixture_count", len(removed_fixture_ids)) or 0),
    }


def render_zone_ratio_report_pdf(payload: Dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=payload.get("title", "Baseline Zone Ratio Report"),
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.textColor = colors.HexColor("#1f2937")
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "Small",
        parent=body,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4b5563"),
    )
    header = ParagraphStyle(
        "Header",
        parent=styles["Heading2"],
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#111827"),
        spaceBefore=8,
        spaceAfter=8,
    )

    story = []
    story.append(Paragraph(payload.get("title", "Baseline Zone Ratio Report"), title_style))
    story.append(Paragraph(
        f"Store band: <b>{payload.get('store_band', '-')}</b> &nbsp;&nbsp;&nbsp; Program intent: <b>{payload.get('program_intent', '-')}</b>",
        body,
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Zone area summary", header))

    data = [["Zone / Metric", "Area (m²)", "Share (%)"]]
    data.append(["Total net area", f"{payload.get('total_net_area_m2', 0.0):.3f}", "100.00"])
    data.append([
        "DISPLAY ISLANDS TOTAL (D1–D12)",
        f"{payload.get('display_island_area_m2', 0.0):.3f}",
        f"{payload.get('display_island_share_pct', 0.0):.2f}",
    ])
    for row in payload.get("zone_rows", []):
        data.append([
            row.get("zone_label", "-"),
            f"{row.get('area_m2', 0.0):.3f}",
            f"{row.get('share_pct', 0.0):.2f}",
        ])
    table = Table(data, colWidths=[64 * mm, 42 * mm, 34 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LEADING", (0, 0), (-1, -1), 13),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ca3af")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Display fixtures schedule", header))
    ff_data = [["F-Family", "What it stands for", "W × D (m)", "Count"]]
    for row in payload.get("f_family_rows", []):
        w = row.get("width_m")
        d = row.get("depth_m")
        dims = f"{float(w):.2f} × {float(d):.2f}" if w is not None and d is not None else "-"
        ff_data.append([
            row.get("family", "-"),
            row.get("label", "-"),
            dims,
            str(int(row.get("count", 0) or 0)),
        ])
    ff_table = Table(ff_data, colWidths=[22 * mm, 76 * mm, 28 * mm, 20 * mm], hAlign="LEFT")
    ff_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("LEADING", (0, 0), (-1, -1), 12),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ca3af")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(ff_table)
    story.append(Spacer(1, 4 * mm))

    if payload.get("t_family_rows"):
        story.append(Paragraph("Interactive devices schedule", header))
        tf_data = [["T-Family", "What it stands for", "W × D (m)", "Count"]]
        for row in payload.get("t_family_rows", []):
            _w = row.get("width_m")
            _d = row.get("depth_m")
            _dims = f"{_w:.2f} × {_d:.2f}" if isinstance(_w, (int, float)) and isinstance(_d, (int, float)) and (_w > 0 or _d > 0) else "-"
            tf_data.append([
                row.get("family", "-"),
                row.get("label", "-"),
                _dims,
                str(int(row.get("count", 0) or 0)),
            ])
        tf_table = Table(tf_data, colWidths=[22 * mm, 72 * mm, 28 * mm, 20 * mm], hAlign="LEFT")
        tf_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("LEADING", (0, 0), (-1, -1), 12),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ca3af")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tf_table)
        story.append(Spacer(1, 6 * mm))
    else:
        story.append(Spacer(1, 6 * mm))

    if payload.get("added_zone_rows"):
        story.append(Paragraph("Added value zones impact", header))
        az_data = [["Added zone", "Area (m²)", "Share of display area (%)"]]
        for row in payload.get("added_zone_rows", []):
            az_data.append([
                row.get("label", "-"),
                f"{row.get('area_m2', 0.0):.3f}",
                f"{row.get('share_pct', 0.0):.2f}",
            ])
        az_data.append([
            "TOTAL",
            f"{payload.get('total_added_area_m2', 0.0):.3f}",
            f"{payload.get('total_added_share_pct', 0.0):.2f}",
        ])
        az_table = Table(az_data, colWidths=[72 * mm, 34 * mm, 42 * mm], hAlign="LEFT")
        az_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LEADING", (0, 0), (-1, -1), 13),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ca3af")),
            ("BACKGROUND", (0, 1), (-1, -2), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f3f4f6")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(az_table)
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(
            f"Display area basis for added-value percentages: <b>{payload.get('added_display_area_m2', 0.0):.3f} m²</b>.",
            small,
        ))
        story.append(Spacer(1, 3 * mm))
        removed_ids = list(payload.get("removed_fixture_ids", []))
        story.append(Paragraph(
            f"Removed display fixtures due to added-value zones: <b>{payload.get('removed_fixture_count', 0)}</b>",
            body,
        ))
        families = [f"F{i}" for i in range(1, 9)]
        family_counts = {fam: 0 for fam in families}
        for fixture_id in removed_ids:
            m = re.match(r"^(F\d+)", str(fixture_id).strip())
            if m and m.group(1) in family_counts:
                family_counts[m.group(1)] += 1
        rf_data = [["Family", "Count Removed"]]
        for fam in families:
            rf_data.append([fam, str(family_counts.get(fam, 0))])
        rf_table = Table(rf_data, colWidths=[36 * mm, 44 * mm], hAlign="LEFT")
        rf_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LEADING", (0, 0), (-1, -1), 13),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ca3af")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(rf_table)
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"Total removed fixtures: <b>{payload.get('removed_fixture_count', 0)}</b>",
            small,
        ))
        story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(
        "This report summarizes the current test case using the generated net store area and the computed area/share for each active zone in the baseline engine.",
        small,
    ))



    _plan_png = payload.get("plan_preview_png")
    if _plan_png:
        story.append(PageBreak())
        story.append(Paragraph("The Proposed Plan", header))
        try:
            _img_buf = BytesIO(_plan_png)
            _img = Image(_img_buf)
            max_w = doc.width
            max_h = A4[1] - doc.topMargin - doc.bottomMargin - 24 * mm
            iw, ih = _img.imageWidth, _img.imageHeight
            if iw > 0 and ih > 0:
                scale = min(max_w / iw, max_h / ih)
                _img.drawWidth = iw * scale
                _img.drawHeight = ih * scale
            story.append(_img)
        except Exception:
            story.append(Paragraph("Plan preview could not be rendered.", small))

    doc.build(story)
    return buffer.getvalue()
