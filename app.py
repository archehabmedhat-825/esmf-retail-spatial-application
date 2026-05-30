
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from config import load_parameters
from shell import generate_store_shell, classify_store_band, validate_step1_inputs
from export import build_svg_payload, render_dxf_bytes, render_png_bytes
from zoning import build_zoning, validate_zoning
from addzones import build_added_zones, validate_added_zones, UI_NAME_TO_KEY
from circulation import build_circulation, validate_circulation
from spacing import analyze_spacing
from frontage import build_frontage_zones
from display_islands import build_display_classification
from report import build_zone_ratio_report_payload, render_zone_ratio_report_pdf

st.set_page_config(page_title="ESMF Retail Spatial Application", page_icon="🏬", layout="wide")


def _runtime_exports_dir() -> Path:
    """Return a writable export folder for the desktop-packaged application.

    Streamlit download buttons work normally in a browser/Edge app window. Some
    native WebView shells can block browser-style downloads, so every exported
    file is also written automatically to this folder as a reliable fallback.
    """
    configured = os.environ.get("ESMF_EXPORTS_DIR", "").strip()
    if configured:
        root = Path(configured)
    else:
        root = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "ESMF_Retail_Spatial_Application" / "exports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _export_bytes(data: Any) -> bytes:
    """Normalize Streamlit download data to bytes for the local fallback copy."""
    if data is None:
        return b""
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    if hasattr(data, "getvalue"):
        value = data.getvalue()
        return value if isinstance(value, bytes) else str(value).encode("utf-8")
    return bytes(data)


def _safe_export_filename(file_name: str) -> str:
    name = str(file_name or "export.bin").strip().replace("/", "_").replace("\\", "_")
    return name or "export.bin"


def _save_local_export_copy(file_name: str, data: Any) -> Path | None:
    """Save a local copy beside the desktop application runtime.

    This does not replace Streamlit's download behavior; it only guarantees that
    PDF/SVG/PNG/DXF outputs exist even when a desktop webview blocks downloads.
    """
    try:
        path = _runtime_exports_dir() / _safe_export_filename(file_name)
        path.write_bytes(_export_bytes(data))
        return path
    except Exception:
        return None


def _download_button_export(*args: Any, **kwargs: Any):
    """Wrapper around st.download_button with an automatic local export copy."""
    data = kwargs.get("data")
    if data is None and len(args) >= 2:
        data = args[1]
    file_name = kwargs.get("file_name", "export.bin")
    saved_path = _save_local_export_copy(str(file_name), data)
    if saved_path is not None:
        kwargs.setdefault("help", f"Downloads normally through the browser. A fallback copy is also saved to: {saved_path}")
    return st.download_button(*args, **kwargs)


def _apply_professional_desktop_style() -> None:
    """Hide Streamlit chrome and apply the Version 2C desktop-shell visual identity."""
    st.markdown(
        """
        <style>
        /* Remove default Streamlit chrome for a desktop-application feeling. */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {visibility: hidden; height: 0rem;}
        [data-testid="stToolbar"] {display: none;}
        [data-testid="stDecoration"] {display: none;}
        [data-testid="stStatusWidget"] {display: none;}
        [data-testid="stDeployButton"] {display: none;}
        .viewerBadge_container__1QSob {display: none;}

        /* Application canvas. */
        .stApp {
            background: #f6f7f9;
        }
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2.25rem;
            padding-left: 2.25rem;
            padding-right: 2.25rem;
            max-width: 100%;
        }

        /* Sidebar identity panel. */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        [data-testid="stSidebar"] * {
            color: #f8fafc;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #cbd5e1;
        }
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stRadio label,
        [data-testid="stSidebar"] .stCheckbox label {
            color: #e5e7eb !important;
            font-weight: 500;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #ffffff;
            letter-spacing: 0.01em;
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.12);
        }

        /* Input fields: keep values readable inside white controls on the dark sidebar. */
        div[data-baseweb="input"],
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
        }
        div[data-baseweb="input"] input,
        div[data-baseweb="select"] input,
        div[data-baseweb="select"] span,
        div[data-baseweb="textarea"] textarea,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            caret-color: #0f172a !important;
        }
        div[data-baseweb="input"] input::placeholder,
        div[data-baseweb="select"] input::placeholder,
        div[data-baseweb="textarea"] textarea::placeholder {
            color: #64748b !important;
            -webkit-text-fill-color: #64748b !important;
            opacity: 1 !important;
        }
        div[data-baseweb="input"] input:disabled,
        div[data-baseweb="select"] input:disabled,
        div[data-baseweb="textarea"] textarea:disabled,
        [data-testid="stNumberInput"] input:disabled {
            color: #334155 !important;
            -webkit-text-fill-color: #334155 !important;
            opacity: 1 !important;
        }
        [data-testid="stNumberInput"] button,
        div[data-baseweb="select"] svg {
            color: #0f172a !important;
            fill: #0f172a !important;
        }
        div[data-baseweb="popover"] *,
        ul[role="listbox"] *,
        div[role="listbox"] * {
            color: #0f172a !important;
        }

        /* Cards and control blocks. */
        div[data-testid="stExpander"] {
            border: 1px solid #dbe1ea;
            border-radius: 12px;
            background: #ffffff;
            box-shadow: 0 1px 2px rgba(15,23,42,0.05);
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 0.65rem 0.8rem;
            box-shadow: 0 1px 2px rgba(15,23,42,0.04);
        }

        /* Typography hierarchy. */
        h1 {
            font-size: 2rem !important;
            line-height: 1.15 !important;
            letter-spacing: -0.02em;
            color: #0f172a;
            margin-bottom: 0.35rem !important;
        }
        h2, h3 {
            color: #111827;
            letter-spacing: -0.01em;
        }
        .stCaptionContainer, small {
            color: #64748b !important;
        }

        /* Buttons and download actions. */
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 10px;
            border: 1px solid #cbd5e1;
            box-shadow: 0 1px 2px rgba(15,23,42,0.08);
            font-weight: 600;
        }

        /* Keep text readable on dark buttons. */
        .stButton > button,
        .stButton > button p,
        .stButton > button span,
        .stDownloadButton > button,
        .stDownloadButton > button p,
        .stDownloadButton > button span {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"] {
            background: #0f172a !important;
            border-color: #0f172a !important;
            color: #ffffff !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: #334155;
            color: #ffffff !important;
        }
        .stButton > button:disabled,
        .stDownloadButton > button:disabled {
            color: #e5e7eb !important;
            -webkit-text-fill-color: #e5e7eb !important;
        }

        /* Data tables. */
        [data-testid="stTable"] {
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e5e7eb;
        }

        /* Reduce top white gap after hidden Streamlit header. */
        div[data-testid="stAppViewContainer"] > .main {
            padding-top: 0rem;
        }


        /* V2E2 responsive tablet/mobile layer: preserves the real desktop app while making controls touch-friendly. */
        :root {
            --esmf-card-radius: 14px;
            --esmf-touch-target: 44px;
        }
        .esmf-mobile-note {
            border: 1px solid #dbeafe;
            background: #eff6ff;
            color: #0f172a;
            border-radius: 12px;
            padding: 0.75rem 0.9rem;
            margin: 0.5rem 0 1rem 0;
            font-size: 0.92rem;
        }
        [data-testid="stImage"],
        [data-testid="stVegaLiteChart"],
        [data-testid="stDeckGlJsonChart"],
        iframe {
            max-width: 100% !important;
        }
        .stDownloadButton > button,
        .stButton > button {
            min-height: var(--esmf-touch-target);
        }

        @media (max-width: 1100px) {
            .block-container {
                padding-left: 1.05rem;
                padding-right: 1.05rem;
                padding-top: 0.9rem;
            }
            h1 { font-size: 1.65rem !important; }
            h2 { font-size: 1.35rem !important; }
            h3 { font-size: 1.12rem !important; }
            div[data-testid="stMetric"] {
                padding: 0.55rem 0.65rem;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 0.35rem;
                overflow-x: auto;
                flex-wrap: nowrap;
            }
            .stTabs [data-baseweb="tab"] {
                min-width: max-content;
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 0.65rem;
                padding-right: 0.65rem;
                padding-top: 0.65rem;
            }
            h1 { font-size: 1.35rem !important; }
            h2 { font-size: 1.15rem !important; }
            h3 { font-size: 1.02rem !important; }
            p, li, label, div[data-testid="stMarkdownContainer"] {
                font-size: 0.95rem;
            }
            [data-testid="stSidebar"] {
                min-width: min(92vw, 25rem) !important;
                max-width: min(92vw, 25rem) !important;
            }
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                gap: 0.6rem !important;
            }
            .stButton > button,
            .stDownloadButton > button {
                width: 100%;
                min-height: 48px;
                font-size: 0.96rem;
            }
            [data-testid="stNumberInput"] input,
            [data-testid="stTextInput"] input,
            div[data-baseweb="select"] > div,
            textarea {
                min-height: 44px !important;
                font-size: 16px !important; /* prevents mobile browser zoom on input focus */
            }
            div[data-testid="stExpander"] {
                border-radius: var(--esmf-card-radius);
            }
            [data-testid="stTable"],
            [data-testid="stDataFrame"] {
                overflow-x: auto !important;
                display: block;
            }
            [data-testid="stMarkdownContainer"] svg,
            svg {
                max-width: none;
            }
            /* Let architectural previews keep their real scale while the phone can pan horizontally. */
            [data-testid="stHtml"] {
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }
            iframe[title="streamlit_component"] {
                width: 100% !important;
                min-height: 520px;
            }
        }

        @media (max-width: 480px) {
            .block-container {
                padding-left: 0.45rem;
                padding-right: 0.45rem;
            }
            h1 { font-size: 1.18rem !important; }
            .stTabs [data-baseweb="tab"] {
                font-size: 0.86rem;
                padding-left: 0.65rem;
                padding-right: 0.65rem;
            }
            div[data-testid="stMetric"] label,
            div[data-testid="stMetric"] [data-testid="stMetricValue"] {
                font-size: 0.88rem !important;
            }
        }


        /* V2E2 UI contrast correction: dark controls must always show white text. */
        .stButton > button,
        .stButton > button *,
        .stDownloadButton > button,
        .stDownloadButton > button *,
        button[kind="primary"],
        button[kind="primary"] *,
        button[data-testid="baseButton-primary"],
        button[data-testid="baseButton-primary"] * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
        }

        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            background-color: #0f172a !important;
            border-color: #0f172a !important;
        }

        /* Sidebar dark inputs: keep values visible. */
        [data-testid="stSidebar"] [data-testid="stNumberInput"] input,
        [data-testid="stSidebar"] [data-testid="stTextInput"] input,
        [data-testid="stSidebar"] [data-testid="stTextArea"] textarea {
            background-color: #020617 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #ffffff !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] [data-testid="stNumberInput"] button,
        [data-testid="stSidebar"] [data-testid="stNumberInput"] button *,
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-baseweb="select"] span,
        [data-testid="stSidebar"] div[data-baseweb="select"] svg {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            fill: #ffffff !important;
            opacity: 1 !important;
        }

        /* Keep white dropdown/listbox menus readable when opened over the page. */
        div[data-baseweb="popover"] *,
        ul[role="listbox"] *,
        div[role="listbox"] * {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
        }

        /* Disabled dark controls should still be readable, not black-on-dark. */
        .stButton > button:disabled,
        .stButton > button:disabled *,
        .stDownloadButton > button:disabled,
        .stDownloadButton > button:disabled *,
        [data-testid="stSidebar"] input:disabled {
            color: #e5e7eb !important;
            -webkit-text-fill-color: #e5e7eb !important;
            opacity: 1 !important;
        }



        /* V2E2 left-controller controls fix: sidebar inputs/selects must stay readable. */
        [data-testid="stSidebar"] [data-testid="stNumberInput"] > div,
        [data-testid="stSidebar"] [data-testid="stTextInput"] > div,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div,
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] > div,
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-baseweb="input"],
        [data-testid="stSidebar"] div[data-baseweb="base-input"] {
            background: #ffffff !important;
            border-color: #cbd5e1 !important;
            color: #0f172a !important;
        }
        [data-testid="stSidebar"] [data-testid="stNumberInput"] input,
        [data-testid="stSidebar"] [data-testid="stTextInput"] input,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] input,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] input,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] *:not(svg),
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] div[data-baseweb="select"] input,
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] div[data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] div[data-baseweb="select"] *:not(svg),
        [data-testid="stSidebar"] [data-testid="stNumberInput"] *:not(svg),
        [data-testid="stSidebar"] [data-testid="stTextInput"] *:not(svg) {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            opacity: 1 !important;
        }
        [data-testid="stSidebar"] [data-testid="stNumberInput"] input::placeholder,
        [data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] input::placeholder {
            color: #64748b !important;
            -webkit-text-fill-color: #64748b !important;
            opacity: 1 !important;
        }
        [data-testid="stSidebar"] [data-testid="stNumberInput"] button,
        [data-testid="stSidebar"] [data-testid="stNumberInput"] button *,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] svg,
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] svg {
            color: #0f172a !important;
            fill: #0f172a !important;
            opacity: 1 !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
            background: #ffffff !important;
        }
        div[data-baseweb="popover"] [role="listbox"],
        div[data-baseweb="popover"] ul,
        div[data-baseweb="popover"] [role="option"] {
            background: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            opacity: 1 !important;
        }
        div[data-baseweb="popover"] [role="option"]:hover,
        div[data-baseweb="popover"] li:hover {
            background: #f1f5f9 !important;
        }
        div[data-baseweb="popover"] [aria-selected="true"] {
            background: #e2e8f0 !important;
            color: #0f172a !important;
        }


        /* FINAL FIX: sidebar number-input fields are dark, so values and +/- icons must be white. */
        [data-testid="stSidebar"] [data-testid="stNumberInput"] div[data-baseweb="input"],
        [data-testid="stSidebar"] [data-testid="stNumberInput"] div[data-baseweb="base-input"],
        [data-testid="stSidebar"] [data-testid="stNumberInput"] input {
            background-color: #020617 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #ffffff !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] [data-testid="stNumberInput"] input::placeholder {
            color: #cbd5e1 !important;
            -webkit-text-fill-color: #cbd5e1 !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] [data-testid="stNumberInput"] button,
        [data-testid="stSidebar"] [data-testid="stNumberInput"] button *,
        [data-testid="stSidebar"] [data-testid="stNumberInput"] svg {
            background-color: #020617 !important;
            color: #ffffff !important;
            fill: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] [data-testid="stNumberInput"] input:disabled {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
        }


        /* FINAL EXACT FIX: requested main-canvas texts must be black on light background. */
        section.main h1,
        section.main h2,
        section.main h3,
        section.main h4,
        section.main p,
        section.main label,
        section.main span:not([data-testid="stIconMaterial"]),
        section.main div[data-testid="stMarkdownContainer"],
        section.main div[data-testid="stMarkdownContainer"] *,
        section.main div[data-testid="stCaptionContainer"],
        section.main div[data-testid="stCaptionContainer"] *,
        section.main div[data-testid="stExpander"] summary,
        section.main div[data-testid="stExpander"] summary *,
        section.main div[data-testid="stExpander"] div[role="button"],
        section.main div[data-testid="stExpander"] div[role="button"] *,
        div[data-testid="stAppViewContainer"] h1,
        div[data-testid="stAppViewContainer"] h2,
        div[data-testid="stAppViewContainer"] h3,
        div[data-testid="stAppViewContainer"] h4,
        div[data-testid="stAppViewContainer"] p,
        div[data-testid="stAppViewContainer"] div[data-testid="stMarkdownContainer"] *,
        div[data-testid="stAppViewContainer"] div[data-testid="stCaptionContainer"] * {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            opacity: 1 !important;
        }

        /* Preserve sidebar contrast after the main text override. */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] *,
        [data-testid="stSidebar"] div[data-testid="stCaptionContainer"] * {
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
        }

        /* Preserve sidebar dark number fields as white text. */
        [data-testid="stSidebar"] [data-testid="stNumberInput"] input,
        [data-testid="stSidebar"] [data-testid="stNumberInput"] input:disabled,
        [data-testid="stSidebar"] [data-testid="stNumberInput"] button,
        [data-testid="stSidebar"] [data-testid="stNumberInput"] button *,
        [data-testid="stSidebar"] [data-testid="stNumberInput"] svg {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            fill: #ffffff !important;
            opacity: 1 !important;
        }

        /* Preserve white/dropdown control readability on the sidebar. */
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-baseweb="select"] span,
        [data-testid="stSidebar"] div[data-baseweb="select"] input {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


_apply_professional_desktop_style()

# ESMF_V2E2_RESPONSIVE_NOTE: layout/CSS only; computation and exports remain the original V2E logic.


def _normalize_inputs(size_mode_ui: str, area_m2: float, length_m: float, width_m: float, entrance_position_ui: str) -> dict:
    size_mode = "AW" if size_mode_ui == "Area + Width" else "LW"
    entrance_position = entrance_position_ui.lower()
    if size_mode == "AW":
        length_m = area_m2 / width_m if width_m > 0 else 0.0
    else:
        area_m2 = length_m * width_m
    return {
        "size_mode": size_mode,
        "area_m2": float(area_m2),
        "length_m": float(length_m),
        "width_m": float(width_m),
        "entrance_position": entrance_position,
    }


def _computed_spine_width(store_band: str, program_intent_ui: str) -> float:
    band_map = {"micro": 1.60, "small": 1.70, "normal": 1.80, "large": 2.00, "xl": 2.20}
    bonus_map = {"Balanced": 0.00, "Sales-first": 0.10, "Fitting-first": 0.00, "Service-first": 0.10}
    base = band_map.get(store_band, 1.80)
    bonus = bonus_map.get(program_intent_ui, 0.0)
    return max(1.60, min(2.40, base + bonus))


def _line_obj(x1: float, y1: float, x2: float, y2: float, role: str, **extra) -> dict:
    obj = {"shape": "line", "role": role, "x1": x1, "y1": y1, "x2": x2, "y2": y2}
    obj.update(extra)
    return obj


def _rect_obj(rect: dict, role: str, **extra) -> dict:
    obj = {
        "shape": "rect",
        "role": role,
        "x": rect["x"],
        "y": rect["y"],
        "length": rect["length"],
        "width": rect["width"],
        "draw_mode": "closed_polygon",
        "dash": False,
        "fill": "none",
    }
    obj.update(extra)
    return obj


def _text_obj(x: float, y: float, text: str, role: str = "label", **extra) -> dict:
    obj = {"shape": "text", "role": role, "x": x, "y": y, "text": text}
    obj.update(extra)
    return obj


def _center(rect: dict) -> tuple[float, float]:
    return rect["x"] + rect["length"] / 2.0, rect["y"] + rect["width"] / 2.0



def _point_in_rect(x: float, y: float, rect: dict, tol: float = 1e-6) -> bool:
    return (
        x >= rect["x"] - tol and y >= rect["y"] - tol and
        x <= rect["x"] + rect["length"] + tol and
        y <= rect["y"] + rect["width"] + tol
    )


def _line_bbox(obj: dict) -> dict:
    x1, y1, x2, y2 = float(obj.get("x1", 0.0)), float(obj.get("y1", 0.0)), float(obj.get("x2", 0.0)), float(obj.get("y2", 0.0))
    return {"x": min(x1, x2), "y": min(y1, y2), "length": abs(x2 - x1), "width": abs(y2 - y1)}


def _nearest_display_island_rect(display_classes: dict | None, target_rect: dict) -> tuple[str | None, dict | None]:
    if not display_classes:
        return None, None
    tx, ty = _center(target_rect)
    best_key, best_rect, best_dist = None, None, None
    for key in ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"]:
        for item in display_classes.get(key, []):
            rect = item.get("rect")
            if not rect:
                continue
            cx, cy = _center(rect)
            dist = (cx - tx) ** 2 + (cy - ty) ** 2
            if best_dist is None or dist < best_dist:
                best_key, best_rect, best_dist = key, rect, dist
    return best_key, best_rect


def _rect_area(rect: dict) -> float:
    return max(0.0, float(rect.get("length", 0.0))) * max(0.0, float(rect.get("width", 0.0)))


def _island_candidate_order(display_classes: dict | None, target_rect: dict, priority_rect: dict | None = None, allowed_keys: list[str] | None = None, prefer_front_glass: bool = False) -> list[tuple[str, dict]]:
    if not display_classes:
        return []
    tx, ty = _center(target_rect)
    px, py = _center(priority_rect) if priority_rect else (tx, ty)
    allowed = allowed_keys or ["D1", "D2", "D3", "D4", "D9", "D10", "D11", "D12"]
    items: list[tuple[float, float, float, str, dict]] = []
    front_y = min((float(item.get("rect", {}).get("y", 0.0)) for key in allowed for item in display_classes.get(key, []) if item.get("rect")), default=0.0)
    for key in allowed:
        for item in display_classes.get(key, []):
            rect = item.get("rect")
            if not rect:
                continue
            cx, cy = _center(rect)
            priority_dist = (cx - px) ** 2 + (cy - py) ** 2
            target_dist = (cx - tx) ** 2 + (cy - ty) ** 2
            glass_rank = 0.0 if (not prefer_front_glass or float(rect.get("y", 0.0)) <= front_y + 1e-6) else 1.0
            items.append((glass_rank, priority_dist, target_dist, key, rect))
    items.sort(key=lambda t: (t[0], t[1], t[2]))
    return [(k, r) for _, _, _, k, r in items]


def _fit_requested_rect_inside_island(request_rect: dict, island_rect: dict) -> dict | None:
    req_l = float(request_rect.get("length", 0.0))
    req_w = float(request_rect.get("width", 0.0))
    isl_l = float(island_rect.get("length", 0.0))
    isl_w = float(island_rect.get("width", 0.0))
    if req_l <= isl_l + 1e-6 and req_w <= isl_w + 1e-6:
        return {
            "x": island_rect["x"] + (isl_l - req_l) / 2.0,
            "y": island_rect["y"] + (isl_w - req_w) / 2.0,
            "length": req_l,
            "width": req_w,
        }
    if req_w <= isl_l + 1e-6 and req_l <= isl_w + 1e-6:
        return {
            "x": island_rect["x"] + (isl_l - req_w) / 2.0,
            "y": island_rect["y"] + (isl_w - req_l) / 2.0,
            "length": req_w,
            "width": req_l,
        }
    return None


def _piece_for_remaining_area_in_island(remaining_area: float, island_rect: dict, anchor_point: tuple[float, float] | None = None) -> dict | None:
    isl_l = float(island_rect.get("length", 0.0))
    isl_w = float(island_rect.get("width", 0.0))
    isl_area = isl_l * isl_w
    if remaining_area <= 1e-6 or isl_area <= 1e-6:
        return None
    if remaining_area >= isl_area - 1e-6:
        return dict(island_rect)

    anchor_x, anchor_y = anchor_point if anchor_point else _center(island_rect)
    isl_cx, isl_cy = _center(island_rect)

    # Prefer preserving the full island width and shortening the length.
    cand_l = remaining_area / max(isl_w, 1e-6)
    if cand_l <= isl_l + 1e-6:
        x = island_rect["x"] if anchor_x <= isl_cx else island_rect["x"] + (isl_l - cand_l)
        return {
            "x": x,
            "y": island_rect["y"],
            "length": cand_l,
            "width": isl_w,
        }

    # Otherwise preserve full island length and shorten the width.
    cand_w = remaining_area / max(isl_l, 1e-6)
    if cand_w <= isl_w + 1e-6:
        y = island_rect["y"] if anchor_y <= isl_cy else island_rect["y"] + (isl_w - cand_w)
        return {
            "x": island_rect["x"],
            "y": y,
            "length": isl_l,
            "width": cand_w,
        }
    return dict(island_rect)


def _host_added_zone_by_islands(display_classes: dict | None, zone_item: dict, priority_rect: dict | None = None, allowed_keys: list[str] | None = None, prefer_front_glass: bool = False) -> tuple[list[dict], list[dict]]:
    target_rect = zone_item.get("rect")
    if not target_rect or not display_classes:
        return ([target_rect] if target_rect else []), []

    target_area = _rect_area(target_rect)
    candidates = _island_candidate_order(display_classes, target_rect, priority_rect=priority_rect, allowed_keys=allowed_keys, prefer_front_glass=prefer_front_glass)
    if not candidates:
        return [target_rect], []

    # First try fitting the requested zone inside a single host island.
    for _, island_rect in candidates:
        fitted = _fit_requested_rect_inside_island(target_rect, island_rect)
        if fitted is not None:
            return [fitted], [island_rect]

    # Otherwise distribute the required area across multiple nearest islands.
    pieces: list[dict] = []
    host_islands: list[dict] = []
    remaining = target_area
    anchor_point = _center(target_rect)
    for _, island_rect in candidates:
        if remaining <= 1e-6:
            break
        piece = _piece_for_remaining_area_in_island(remaining, island_rect, anchor_point=anchor_point)
        if piece is None:
            continue
        pieces.append(piece)
        host_islands.append(island_rect)
        remaining -= _rect_area(piece)
        anchor_point = _center(piece)

    if not pieces:
        return [target_rect], []
    return pieces, host_islands


def _filter_fixture_family_by_islands(fixtures: list[dict], buffers: list[dict], islands: list[dict], remove_surviving_buffers_on_overlap: bool = True) -> tuple[list[dict], list[dict], set[tuple[str, int]]]:
    removed_ids: set[tuple[str, int]] = set()
    kept_fixtures: list[dict] = []
    for obj in fixtures or []:
        rect = obj if obj.get("shape") == "rect" else _line_bbox(obj)
        if any(_rects_overlap(rect, isl) for isl in islands):
            fam = str(obj.get("family", ""))
            idx = int(obj.get("module_index", -1))
            if fam and idx >= 0:
                removed_ids.add((fam, idx))
        else:
            kept_fixtures.append(obj)
    kept_buffers: list[dict] = []
    for obj in buffers or []:
        fam = str(obj.get("family", ""))
        idx = int(obj.get("module_index", -1)) if obj.get("module_index") is not None else -1
        if fam and idx >= 0 and (fam, idx) in removed_ids:
            continue
        if remove_surviving_buffers_on_overlap:
            rect = obj if obj.get("shape") == "rect" else _line_bbox(obj)
            if any(_rects_overlap(rect, isl) for isl in islands):
                continue
        kept_buffers.append(obj)
    return kept_fixtures, kept_buffers, removed_ids


def _filter_selected_fixture_families_by_islands(fixtures: list[dict], buffers: list[dict], islands: list[dict], target_families: set[str], remove_surviving_buffers_on_overlap: bool = True) -> tuple[list[dict], list[dict], set[tuple[str, int]]]:
    target_families = {str(f) for f in (target_families or set())}
    removed_ids: set[tuple[str, int]] = set()
    kept_fixtures: list[dict] = []
    for obj in fixtures or []:
        fam = str(obj.get("family", ""))
        rect = obj if obj.get("shape") == "rect" else _line_bbox(obj)
        if fam in target_families and any(_rects_overlap(rect, isl) for isl in islands):
            idx = int(obj.get("module_index", -1))
            if idx >= 0:
                removed_ids.add((fam, idx))
        else:
            kept_fixtures.append(obj)
    kept_buffers: list[dict] = []
    for obj in buffers or []:
        fam = str(obj.get("family", ""))
        idx = int(obj.get("module_index", -1)) if obj.get("module_index") is not None else -1
        if fam and idx >= 0 and (fam, idx) in removed_ids:
            continue
        if remove_surviving_buffers_on_overlap and fam in target_families:
            rect = obj if obj.get("shape") == "rect" else _line_bbox(obj)
            if any(_rects_overlap(rect, isl) for isl in islands):
                continue
        kept_buffers.append(obj)
    return kept_fixtures, kept_buffers, removed_ids


def _remove_d1_fixture_overlaps_for_interactive_hard(display_wall: list[dict], display_wall_buffer: list[dict], display_gondola: list[dict], display_gondola_buffer: list[dict], display_mannequin: list[dict], display_mannequin_buffer: list[dict], display_table: list[dict], display_table_buffer_min: list[dict], display_table_buffer: list[dict], labels: list[dict], removed_fixture_ids: set[tuple[str, int]], hard_rects: list[dict], clear_surviving_buffers_on_overlap: bool = False) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], set[tuple[str, int]]]:
    """Inside D1/D2, remove any F-family hard footprint that overlaps an interactive hard footprint.

    D2 pressure-resolution patch: D2 behaves as an entrance/transition island,
    so T-family hard footprints have priority over all F-family hard footprints.
    """
    d1_hard_rects = [
        obj for obj in (hard_rects or [])
        if isinstance(obj, dict) and obj.get("shape") == "rect" and str(obj.get("host_key", "")) in ("D1", "D2")
    ]
    if not d1_hard_rects:
        return display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids

    display_wall, display_wall_buffer, removed_wall = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, d1_hard_rects, remove_surviving_buffers_on_overlap=clear_surviving_buffers_on_overlap)
    display_gondola, display_gondola_buffer, removed_gondola = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, d1_hard_rects, remove_surviving_buffers_on_overlap=clear_surviving_buffers_on_overlap)
    display_mannequin, display_mannequin_buffer, removed_mannequin = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, d1_hard_rects, remove_surviving_buffers_on_overlap=clear_surviving_buffers_on_overlap)
    display_table, display_table_buffer_min, removed_table_min = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, d1_hard_rects, remove_surviving_buffers_on_overlap=clear_surviving_buffers_on_overlap)

    removed_now = set(removed_wall) | set(removed_gondola) | set(removed_mannequin) | set(removed_table_min)
    if removed_now:
        removed_fixture_ids |= removed_now
        display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_now]
        labels = [
            obj for obj in labels
            if not (
                obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                isinstance(obj.get("text"), str) and "-" in str(obj.get("text")) and
                (lambda _parts: (_parts[0], int(_parts[1])) if len(_parts) == 2 and _parts[1].isdigit() else (None, -1))(str(obj.get("text")).split("-", 1)) in removed_now
            )
        ]
    return display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids


def _clear_d1_fixture_area_for_interactive_min(display_wall: list[dict], display_wall_buffer: list[dict], display_gondola: list[dict], display_gondola_buffer: list[dict], display_mannequin: list[dict], display_mannequin_buffer: list[dict], display_table: list[dict], display_table_buffer_min: list[dict], display_table_buffer: list[dict], labels: list[dict], removed_fixture_ids: set[tuple[str, int]], min_rects: list[dict], clear_surviving_buffers_on_overlap: bool = False) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], set[tuple[str, int]]]:
    """Inside D1/D2, clear fixture area using the interactive minimum buffer footprint.

    D2 pressure-resolution patch: the T-family minimum buffer is treated as a
    protected zone in D2, preventing F7/F8/F4-F6 residues from visually or
    geometrically colliding with the inserted device.
    """
    d1_min_rects = [
        obj for obj in (min_rects or [])
        if isinstance(obj, dict) and obj.get("shape") == "rect" and str(obj.get("host_key", "")) in ("D1", "D2")
    ]
    if not d1_min_rects:
        return display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids

    display_wall, display_wall_buffer, removed_wall = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, d1_min_rects, remove_surviving_buffers_on_overlap=clear_surviving_buffers_on_overlap)
    display_gondola, display_gondola_buffer, removed_gondola = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, d1_min_rects, remove_surviving_buffers_on_overlap=clear_surviving_buffers_on_overlap)
    display_mannequin, display_mannequin_buffer, removed_mannequin = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, d1_min_rects, remove_surviving_buffers_on_overlap=clear_surviving_buffers_on_overlap)
    display_table, display_table_buffer_min, removed_table_min = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, d1_min_rects, remove_surviving_buffers_on_overlap=clear_surviving_buffers_on_overlap)

    removed_now = set(removed_wall) | set(removed_gondola) | set(removed_mannequin) | set(removed_table_min)
    if removed_now:
        removed_fixture_ids |= removed_now
        display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_now]
        labels = [
            obj for obj in labels
            if not (
                obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                isinstance(obj.get("text"), str) and "-" in str(obj.get("text")) and
                (lambda _parts: (_parts[0], int(_parts[1])) if len(_parts) == 2 and _parts[1].isdigit() else (None, -1))(str(obj.get("text")).split("-", 1)) in removed_now
            )
        ]
    return display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids


def _build_t1_placements(display_classes: dict | None, zoning: dict, count: int, width_m: float, depth_m: float, side_offset_m: float = 0.50, front_soft_m: float = 1.60, front_min_m: float = 1.20) -> dict:
    """Place T1 Interactive Screen inside D6 first then D5.
    The hard footprint stays inside the display island strip. Soft buffers project inward toward the store.
    Fixtures are cleared only within the host strip band needed by the device.
    """
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
    if not display_classes or count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    sales = zoning.get("sales_zone", {})
    candidates = []
    for key in ("D6", "D5"):
        for item in display_classes.get(key, []) or []:
            rect = item.get("rect") if isinstance(item, dict) else None
            if rect:
                candidates.append((key, rect))

    placed = 0
    total_capacity = 0
    idx = 1
    unit_h = width_m + 2.0 * side_offset_m
    for key, host in candidates:
        if placed >= count:
            break
        host_len = float(host.get("length", 0.0))
        host_w = float(host.get("width", 0.0))
        if host_len + 1e-6 < depth_m or host_w + 1e-6 < unit_h:
            continue
        cap = max(0, int(host_w // unit_h))
        total_capacity += cap
        if cap <= 0:
            continue
        n = min(cap, count - placed)
        y_cursor = float(host["y"]) + max(0.0, (host_w - n * unit_h) / 2.0)
        side = _host_side(host, sales)
        for _ in range(n):
            hard_y = y_cursor + side_offset_m
            if side == "left":
                hard_x = float(host["x"])
                hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                min_buf = {"x": hard_x, "y": hard_y - side_offset_m, "length": depth_m + front_min_m, "width": width_m + 2.0 * side_offset_m}
                soft_buf = {"x": hard_x, "y": hard_y - side_offset_m, "length": depth_m + front_soft_m, "width": width_m + 2.0 * side_offset_m}
            else:
                hard_x = float(host["x"] + host_len - depth_m)
                hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                min_buf = {"x": hard_x - front_min_m, "y": hard_y - side_offset_m, "length": depth_m + front_min_m, "width": width_m + 2.0 * side_offset_m}
                soft_buf = {"x": hard_x - front_soft_m, "y": hard_y - side_offset_m, "length": depth_m + front_soft_m, "width": width_m + 2.0 * side_offset_m}

            clear_rect = {"x": float(host["x"]), "y": hard_y - side_offset_m, "length": host_len, "width": width_m + 2.0 * side_offset_m}
            result["hard"].append(_rect_obj(hard, "interactive_t1", family="T1", module_index=idx, host_key=key, host_side=side, lineweight="heavy"))
            result["min"].append(_rect_obj(min_buf, "interactive_t1_buffer_min", family="T1", module_index=idx, host_key=key, host_side=side))
            result["soft"].append(_rect_obj(soft_buf, "interactive_t1_buffer", family="T1", module_index=idx, host_key=key, host_side=side))
            cx, cy = _center(hard)
            result["labels"].append(_text_obj(cx, cy, f"T1-{idx}", role="fixture_label", text_size="small"))
            result["clear"].append(clear_rect)
            idx += 1
            placed += 1
            y_cursor += unit_h
            if placed >= count:
                break
    result["placed"] = placed
    result["capacity"] = total_capacity
    return result


def _compute_fitting_area_buffer_rects(zoning: dict, circulation: dict | None, fitting_rooms: list[dict] | None = None) -> list[dict]:
    fitting = zoning["fitting_zone"]
    fitting_top_y = float(fitting["y"] + fitting["width"])
    connector_top_y = float(fitting["y"])
    if circulation and circulation.get("service_connector"):
        connector = circulation["service_connector"]
        connector_top_y = float(connector["y"] + connector["width"])
    if fitting_top_y <= connector_top_y + 1e-6:
        return []
    x0 = float(fitting["x"])
    x1 = float(fitting["x"] + fitting["length"])
    intervals = [(x0, x1)]
    for room in fitting_rooms or []:
        rx0 = max(x0, float(room.get("x", x0)))
        rx1 = min(x1, float(room.get("x", x0)) + float(room.get("length", 0.0)))
        if rx1 <= rx0 + 1e-6:
            continue
        updated = []
        for a, b in intervals:
            if rx1 <= a + 1e-6 or rx0 >= b - 1e-6:
                updated.append((a, b))
            else:
                if a < rx0 - 1e-6:
                    updated.append((a, rx0))
                if rx1 < b - 1e-6:
                    updated.append((rx1, b))
        intervals = updated
    rects = []
    for a, b in intervals:
        if b > a + 1e-6:
            rects.append({"x": a, "y": connector_top_y, "length": b - a, "width": fitting_top_y - connector_top_y})
    return rects


def _build_t3_placements(display_classes: dict | None, zoning: dict, circulation: dict | None, fitting_rooms: list[dict] | None, count: int, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 1.60, front_min_m: float = 1.20, allow_d7: bool = False, blocked_soft_rects: list[dict] | None = None) -> dict:
    """Place T3 Smart / Magic Mirror along the top boundary of the fitting area buffer first.
    If needed, fitting rooms Fit2..Fit10 may be removed progressively to enlarge the available top-edge span.
    If additional capacity is still needed, T3 may also fit inside D7 boundaries.
    """
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0, "kept_rooms": list(fitting_rooms or []), "removed_room_ids": []}
    if count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    original_rooms = list(fitting_rooms or [])
    blocked_soft_rects = list(blocked_soft_rects or [])

    def _candidate_sets(rooms: list[dict]) -> list[tuple[list[dict], list[str]]]:
        removable = sorted([r for r in rooms if int(r.get("index", 0) or 0) >= 2], key=lambda r: int(r.get("index", 0) or 0), reverse=True)
        out = [(list(rooms), [])]
        for i in range(1, len(removable) + 1):
            removed = removable[:i]
            removed_ids = [str(r.get("id", f"Fit{r.get('index', '?')}")) for r in removed]
            removed_idx = {int(r.get("index", 0) or 0) for r in removed}
            kept = [r for r in rooms if int(r.get("index", 0) or 0) not in removed_idx]
            out.append((kept, removed_ids))
        return out

    def _pack_top_buffer(rects: list[dict], start_idx: int, remaining: int):
        pack = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
        idx = start_idx
        span = width_m + 2.0 * side_offset_m
        for rect in rects:
            host_len = float(rect.get("length", 0.0))
            host_top = float(rect.get("y", 0.0) + rect.get("width", 0.0))
            cap = max(0, int(host_len // span))
            pack["capacity"] += cap
            if pack["placed"] >= remaining or cap <= 0:
                continue
            n = min(cap, remaining - pack["placed"])
            x_cursor = float(rect.get("x", 0.0)) + max(0.0, (host_len - n * span) / 2.0)
            hard_y = host_top - depth_m
            for _ in range(n):
                hard_x = x_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    x_cursor += span
                    continue
                min_buf = {"x": x_cursor, "y": hard_y - front_min_m, "length": span, "width": depth_m + front_min_m}
                soft_buf = {"x": x_cursor, "y": hard_y - front_soft_m, "length": span, "width": depth_m + front_soft_m}
                clear_rect = {"x": x_cursor, "y": hard_y - front_soft_m, "length": span, "width": depth_m + front_soft_m}
                pack["hard"].append(_rect_obj(hard, "interactive_t3", family="T3", module_index=idx, host_key="FITTING_AREA_BUFFER", orientation="S", lineweight="heavy"))
                pack["min"].append(_rect_obj(min_buf, "interactive_t3_buffer_min", family="T3", module_index=idx, host_key="FITTING_AREA_BUFFER"))
                pack["soft"].append(_rect_obj(soft_buf, "interactive_t3_buffer", family="T3", module_index=idx, host_key="FITTING_AREA_BUFFER"))
                cx, cy = _center(hard)
                pack["labels"].append(_text_obj(cx, cy, f"T3-{idx}", role="fixture_label", text_size="small"))
                pack["clear"].append(clear_rect)
                idx += 1
                pack["placed"] += 1
                x_cursor += span
                if pack["placed"] >= remaining:
                    break
        return pack, idx

    def _pack_d7(start_idx: int, remaining: int):
        pack = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
        idx = start_idx
        sales = zoning.get("sales_zone", {})
        unit_h = width_m + 2.0 * side_offset_m
        for item in (display_classes or {}).get("D7", []) or []:
            host = item.get("rect") if isinstance(item, dict) else None
            if not host:
                continue
            host_len = float(host.get("length", 0.0))
            host_w = float(host.get("width", 0.0))
            if host_len + 1e-6 < depth_m or host_w + 1e-6 < unit_h:
                continue
            cap = max(0, int(host_w // unit_h))
            pack["capacity"] += cap
            if pack["placed"] >= remaining or cap <= 0:
                continue
            n = min(cap, remaining - pack["placed"])
            y_cursor = float(host["y"]) + max(0.0, (host_w - n * unit_h) / 2.0)
            side = _host_side(host, sales)
            for _ in range(n):
                hard_y = y_cursor + side_offset_m
                if side == "left":
                    hard_x = float(host["x"])
                    hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                    min_buf = {"x": hard_x, "y": hard_y - side_offset_m, "length": depth_m + front_min_m, "width": width_m + 2.0 * side_offset_m}
                    soft_buf = {"x": hard_x, "y": hard_y - side_offset_m, "length": depth_m + front_soft_m, "width": width_m + 2.0 * side_offset_m}
                else:
                    hard_x = float(host["x"] + host_len - depth_m)
                    hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                    min_buf = {"x": hard_x - front_min_m, "y": hard_y - side_offset_m, "length": depth_m + front_min_m, "width": width_m + 2.0 * side_offset_m}
                    soft_buf = {"x": hard_x - front_soft_m, "y": hard_y - side_offset_m, "length": depth_m + front_soft_m, "width": width_m + 2.0 * side_offset_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    y_cursor += unit_h
                    continue
                clear_rect = {"x": float(host["x"]), "y": hard_y - side_offset_m, "length": host_len, "width": width_m + 2.0 * side_offset_m}
                pack["hard"].append(_rect_obj(hard, "interactive_t3", family="T3", module_index=idx, host_key="D7", host_side=side, lineweight="heavy"))
                pack["min"].append(_rect_obj(min_buf, "interactive_t3_buffer_min", family="T3", module_index=idx, host_key="D7", host_side=side))
                pack["soft"].append(_rect_obj(soft_buf, "interactive_t3_buffer", family="T3", module_index=idx, host_key="D7", host_side=side))
                cx, cy = _center(hard)
                pack["labels"].append(_text_obj(cx, cy, f"T3-{idx}", role="fixture_label", text_size="small"))
                pack["clear"].append(clear_rect)
                idx += 1
                pack["placed"] += 1
                y_cursor += unit_h
                if pack["placed"] >= remaining:
                    break
        return pack

    def _room_rect(room: dict) -> dict:
        return {"x": float(room.get("x", 0.0)), "y": float(room.get("y", 0.0)), "length": float(room.get("length", 0.0)), "width": float(room.get("width", 0.0))}

    def _resolve_pack_with_room_feedback(base_rooms: list[dict], base_removed_ids: list[str]) -> dict:
        rooms_state = list(base_rooms)
        removed_ids = list(base_removed_ids)
        max_loops = max(1, len(rooms_state) + 2)
        final_pack = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
        next_idx = 1
        for _ in range(max_loops):
            rects = sorted(_compute_fitting_area_buffer_rects(zoning, circulation, rooms_state), key=lambda r: (float(r.get("y",0))+float(r.get("width",0)), float(r.get("length",0))), reverse=True)
            pack = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0, "kept_rooms": list(rooms_state), "removed_room_ids": list(removed_ids)}
            top_pack, next_idx = _pack_top_buffer(rects, 1, count)
            for k in ["hard", "min", "soft", "labels", "clear"]:
                pack[k].extend(top_pack.get(k, []))
            pack["placed"] += top_pack.get("placed", 0)
            pack["capacity"] += top_pack.get("capacity", 0)
            if allow_d7 and pack["placed"] < count:
                d7_pack = _pack_d7(next_idx, count - pack["placed"])
                for k in ["hard", "min", "soft", "labels", "clear"]:
                    pack[k].extend(d7_pack.get(k, []))
                pack["placed"] += d7_pack.get("placed", 0)
                pack["capacity"] += d7_pack.get("capacity", 0)

            removable_hits = []
            for room in rooms_state:
                idx = int(room.get("index", 0) or 0)
                if idx < 2:
                    continue
                rr = _room_rect(room)
                if any(_rects_overlap(rr, soft) for soft in pack.get("soft", [])):
                    removable_hits.append(room)
            if not removable_hits:
                final_pack = pack
                break
            hit_idx = {int(r.get("index", 0) or 0) for r in removable_hits}
            hit_ids = [str(r.get("id", f"Fit{r.get('index', '?')}")) for r in removable_hits]
            for rid in hit_ids:
                if rid not in removed_ids:
                    removed_ids.append(rid)
            new_rooms = [r for r in rooms_state if int(r.get("index", 0) or 0) not in hit_idx]
            if len(new_rooms) == len(rooms_state):
                final_pack = pack
                break
            rooms_state = new_rooms
            final_pack = pack
        final_pack["kept_rooms"] = list(rooms_state)
        final_pack["removed_room_ids"] = list(removed_ids)
        return final_pack

    best_payload = None
    best_score = (-1, -1, -999999)
    for kept_rooms, removed_ids in _candidate_sets(original_rooms):
        pack = _resolve_pack_with_room_feedback(kept_rooms, removed_ids)
        score = (int(pack.get("placed", 0) or 0), int(pack.get("capacity", 0) or 0), -len(pack.get("removed_room_ids", [])))
        if score > best_score:
            best_score = score
            best_payload = pack
        if int(pack.get("placed", 0) or 0) >= count:
            break
    if best_payload is None:
        return result
    return best_payload



def _reduce_fitting_by_t4(fitting_rooms: list[dict] | None, t4_count: int) -> list[dict]:
    """Remove fitting rooms by descending fit index.
    Rule: remove 1 fitting per 2 T4; Fit1 is always preserved.
    Removal starts from the largest fit count first (Fit10, Fit9, Fit8, ...),
    while Fit1 is never removed regardless of T4 count.
    """
    rooms = list(fitting_rooms or [])
    if not rooms or t4_count <= 1:
        return rooms

    remove_n = int(t4_count) // 2
    if remove_n <= 0:
        return rooms

    fit1 = []
    others = []
    for fr in rooms:
        name = str(fr.get("name", fr.get("id", "")))
        if name == "Fit1":
            fit1.append(fr)
        else:
            others.append(fr)

    def _fit_index(fr: dict) -> int:
        try:
            return int(str(fr.get("name", fr.get("id", ""))).replace("Fit", ""))
        except Exception:
            return 0

    others_sorted = sorted(others, key=_fit_index, reverse=True)
    remaining = others_sorted[remove_n:]
    remaining_sorted = sorted(remaining, key=_fit_index)
    return fit1 + remaining_sorted


def _filter_fitting_rooms_below_t5_soft(fitting_rooms: list[dict] | None, t5_soft_rects: list[dict] | None) -> tuple[list[dict], list[str]]:
    """Remove Fit2..Fit10 whose room boundaries overlap T5 soft boundaries in plan."""
    rooms = list(fitting_rooms or [])
    softs = list(t5_soft_rects or [])
    if not rooms or not softs:
        return rooms, []
    kept = []
    removed_ids = []
    for room in rooms:
        idx = int(room.get("index", 0) or 0)
        if idx < 2:
            kept.append(room)
            continue
        room_rect = {
            "x": float(room.get("x", 0.0)),
            "y": float(room.get("y", 0.0)),
            "length": float(room.get("length", 0.0)),
            "width": float(room.get("width", 0.0)),
        }
        if any(_rects_overlap(room_rect, s) for s in softs):
            removed_ids.append(str(room.get("id", f"Fit{idx}")))
        else:
            kept.append(room)
    return kept, removed_ids

def _build_t5_placements(display_classes: dict | None, zoning: dict, circulation: dict | None, fitting_rooms: list[dict] | None, count: int, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 1.60, front_min_m: float = 1.20, allow_d7: bool = False, blocked_soft_rects: list[dict] | None = None) -> dict:
    """Place T5 3D Body Scanner along the top boundary of the fitting area buffer first.
    If needed, fitting rooms Fit2..Fit10 may be removed progressively to enlarge the available top-edge span.
    If additional capacity is still needed, T3 may also fit inside D7 boundaries.
    """
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0, "kept_rooms": list(fitting_rooms or []), "removed_room_ids": []}
    if count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    original_rooms = list(fitting_rooms or [])
    blocked_soft_rects = list(blocked_soft_rects or [])

    def _candidate_sets(rooms: list[dict]) -> list[tuple[list[dict], list[str]]]:
        removable = sorted([r for r in rooms if int(r.get("index", 0) or 0) >= 2], key=lambda r: int(r.get("index", 0) or 0), reverse=True)
        out = [(list(rooms), [])]
        for i in range(1, len(removable) + 1):
            removed = removable[:i]
            removed_ids = [str(r.get("id", f"Fit{r.get('index', '?')}")) for r in removed]
            removed_idx = {int(r.get("index", 0) or 0) for r in removed}
            kept = [r for r in rooms if int(r.get("index", 0) or 0) not in removed_idx]
            out.append((kept, removed_ids))
        return out

    def _pack_top_buffer(rects: list[dict], start_idx: int, remaining: int):
        pack = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
        idx = start_idx
        span = width_m + 2.0 * side_offset_m

        def _can_place(hard: dict, soft_buf: dict) -> bool:
            if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                return False
            if any(_rects_overlap(soft_buf, existing) for existing in pack["soft"]):
                return False
            return True

        for rect in rects:
            host_len = float(rect.get("length", 0.0))
            host_x = float(rect.get("x", 0.0))
            host_top = float(rect.get("y", 0.0) + rect.get("width", 0.0))
            cap = max(0, int(host_len // span))
            pack["capacity"] += cap
            if pack["placed"] >= remaining or cap <= 0:
                continue
            hard_y = host_top - depth_m

            # Prefer side-by-side attachment to the FIRST blocked soft boundary (e.g. first T3 soft envelope)
            # so the first T5 is explicitly attached to the first T3 before any fallback packing.
            anchors = []
            sorted_blocked = sorted(blocked_soft_rects, key=lambda r: float(r.get("x", 0.0)))
            if pack["placed"] == 0 and sorted_blocked:
                first_blk = sorted_blocked[0]
                bx = float(first_blk.get("x", 0.0))
                bl = float(first_blk.get("length", 0.0))
                # Prefer attaching on the right side first, then the left side.
                anchors.extend([bx + bl, bx - span])
            for blk in sorted_blocked:
                bx = float(blk.get("x", 0.0))
                bl = float(blk.get("length", 0.0))
                if bx + bl <= host_x - 1e-6 or bx >= host_x + host_len + 1e-6:
                    continue
                cand_right = bx + bl
                cand_left = bx - span
                for cand in (cand_right, cand_left):
                    if cand not in anchors:
                        anchors.append(cand)

            for x_cursor in anchors:
                if pack["placed"] >= remaining:
                    break
                if x_cursor < host_x - 1e-6 or x_cursor + span > host_x + host_len + 1e-6:
                    continue
                hard_x = x_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
                min_buf = {"x": x_cursor, "y": hard_y - front_min_m, "length": span, "width": depth_m + front_min_m}
                soft_buf = {"x": x_cursor, "y": hard_y - front_soft_m, "length": span, "width": depth_m + front_soft_m}
                if not _can_place(hard, soft_buf):
                    continue
                clear_rect = {"x": x_cursor, "y": hard_y - front_soft_m, "length": span, "width": depth_m + front_soft_m}
                pack["hard"].append(_rect_obj(hard, "interactive_t5", family="T5", module_index=idx, host_key="FITTING_AREA_BUFFER", orientation="S", lineweight="heavy"))
                pack["min"].append(_rect_obj(min_buf, "interactive_t5_buffer_min", family="T5", module_index=idx, host_key="FITTING_AREA_BUFFER"))
                pack["soft"].append(_rect_obj(soft_buf, "interactive_t5_buffer", family="T5", module_index=idx, host_key="FITTING_AREA_BUFFER"))
                cx, cy = _center(hard)
                pack["labels"].append(_text_obj(cx, cy, f"T5-{idx}", role="fixture_label", text_size="small"))
                pack["clear"].append(clear_rect)
                idx += 1
                pack["placed"] += 1

            if pack["placed"] >= remaining:
                continue

            # Fallback regular centered packing for any remaining capacity
            n = min(cap, remaining - pack["placed"])
            x_cursor = host_x + max(0.0, (host_len - n * span) / 2.0)
            for _ in range(n):
                hard_x = x_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
                min_buf = {"x": x_cursor, "y": hard_y - front_min_m, "length": span, "width": depth_m + front_min_m}
                soft_buf = {"x": x_cursor, "y": hard_y - front_soft_m, "length": span, "width": depth_m + front_soft_m}
                if not _can_place(hard, soft_buf):
                    x_cursor += span
                    continue
                clear_rect = {"x": x_cursor, "y": hard_y - front_soft_m, "length": span, "width": depth_m + front_soft_m}
                pack["hard"].append(_rect_obj(hard, "interactive_t5", family="T5", module_index=idx, host_key="FITTING_AREA_BUFFER", orientation="S", lineweight="heavy"))
                pack["min"].append(_rect_obj(min_buf, "interactive_t5_buffer_min", family="T5", module_index=idx, host_key="FITTING_AREA_BUFFER"))
                pack["soft"].append(_rect_obj(soft_buf, "interactive_t5_buffer", family="T5", module_index=idx, host_key="FITTING_AREA_BUFFER"))
                cx, cy = _center(hard)
                pack["labels"].append(_text_obj(cx, cy, f"T5-{idx}", role="fixture_label", text_size="small"))
                pack["clear"].append(clear_rect)
                idx += 1
                pack["placed"] += 1
                x_cursor += span
                if pack["placed"] >= remaining:
                    break
        return pack, idx

    def _pack_d7(start_idx: int, remaining: int):
        pack = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
        idx = start_idx
        sales = zoning.get("sales_zone", {})
        unit_h = width_m + 2.0 * side_offset_m
        for item in (display_classes or {}).get("D7", []) or []:
            host = item.get("rect") if isinstance(item, dict) else None
            if not host:
                continue
            host_len = float(host.get("length", 0.0))
            host_w = float(host.get("width", 0.0))
            if host_len + 1e-6 < depth_m or host_w + 1e-6 < unit_h:
                continue
            cap = max(0, int(host_w // unit_h))
            pack["capacity"] += cap
            if pack["placed"] >= remaining or cap <= 0:
                continue
            n = min(cap, remaining - pack["placed"])
            y_cursor = float(host["y"]) + max(0.0, (host_w - n * unit_h) / 2.0)
            side = _host_side(host, sales)
            for _ in range(n):
                hard_y = y_cursor + side_offset_m
                if side == "left":
                    hard_x = float(host["x"])
                    hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                    min_buf = {"x": hard_x, "y": hard_y - side_offset_m, "length": depth_m + front_min_m, "width": width_m + 2.0 * side_offset_m}
                    soft_buf = {"x": hard_x, "y": hard_y - side_offset_m, "length": depth_m + front_soft_m, "width": width_m + 2.0 * side_offset_m}
                else:
                    hard_x = float(host["x"] + host_len - depth_m)
                    hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                    min_buf = {"x": hard_x - front_min_m, "y": hard_y - side_offset_m, "length": depth_m + front_min_m, "width": width_m + 2.0 * side_offset_m}
                    soft_buf = {"x": hard_x - front_soft_m, "y": hard_y - side_offset_m, "length": depth_m + front_soft_m, "width": width_m + 2.0 * side_offset_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    y_cursor += unit_h
                    continue
                clear_rect = {"x": float(host["x"]), "y": hard_y - side_offset_m, "length": host_len, "width": width_m + 2.0 * side_offset_m}
                pack["hard"].append(_rect_obj(hard, "interactive_t5", family="T5", module_index=idx, host_key="D7", host_side=side, lineweight="heavy"))
                pack["min"].append(_rect_obj(min_buf, "interactive_t5_buffer_min", family="T5", module_index=idx, host_key="D7", host_side=side))
                pack["soft"].append(_rect_obj(soft_buf, "interactive_t5_buffer", family="T5", module_index=idx, host_key="D7", host_side=side))
                cx, cy = _center(hard)
                pack["labels"].append(_text_obj(cx, cy, f"T5-{idx}", role="fixture_label", text_size="small"))
                pack["clear"].append(clear_rect)
                idx += 1
                pack["placed"] += 1
                y_cursor += unit_h
                if pack["placed"] >= remaining:
                    break
        return pack

    best_payload = None
    for kept_rooms, removed_ids in _candidate_sets(original_rooms):
        rects = sorted(_compute_fitting_area_buffer_rects(zoning, circulation, kept_rooms), key=lambda r: (float(r.get("y",0))+float(r.get("width",0)), float(r.get("length",0))), reverse=True)
        pack = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0, "kept_rooms": kept_rooms, "removed_room_ids": removed_ids}
        top_pack, next_idx = _pack_top_buffer(rects, 1, count)
        for k in ["hard", "min", "soft", "labels", "clear"]:
            pack[k].extend(top_pack.get(k, []))
        pack["placed"] += top_pack.get("placed", 0)
        pack["capacity"] += top_pack.get("capacity", 0)
        if allow_d7 and pack["placed"] < count:
            d7_pack = _pack_d7(next_idx, count - pack["placed"])
            for k in ["hard", "min", "soft", "labels", "clear"]:
                pack[k].extend(d7_pack.get(k, []))
            pack["placed"] += d7_pack.get("placed", 0)
            pack["capacity"] += d7_pack.get("capacity", 0)
        best_payload = pack
        if pack["capacity"] >= count:
            break
    if best_payload is None:
        return result
    return best_payload


def _build_t3_t5_joint_placements(display_classes: dict | None, zoning: dict, circulation: dict | None, fitting_rooms: list[dict] | None, t3_count: int, t3_width_m: float, t3_depth_m: float, t5_count: int, t5_width_m: float, t5_depth_m: float, allow_d7: bool = False) -> dict:
    """Joint fitting-area search for T3 and T5.
    It progressively removes Fit2..Fit10 until the fitting area buffer can accommodate
    the requested T3 count first, then T5 adjacent/after T3 where possible.
    T3 always has priority over T5.
    """
    original_rooms = list(fitting_rooms or [])

    def _candidate_sets(rooms: list[dict]) -> list[tuple[list[dict], list[str]]]:
        removable = sorted([r for r in rooms if int(r.get("index", 0) or 0) >= 2], key=lambda r: int(r.get("index", 0) or 0), reverse=True)
        out = [(list(rooms), [])]
        for i in range(1, len(removable) + 1):
            removed = removable[:i]
            removed_ids = [str(r.get("id", f"Fit{r.get('index', '?')}")) for r in removed]
            removed_idx = {int(r.get("index", 0) or 0) for r in removed}
            kept = [r for r in rooms if int(r.get("index", 0) or 0) not in removed_idx]
            out.append((kept, removed_ids))
        return out

    best = {"score": (-1, -1, 999999), "t3": None, "t5": None, "kept_rooms": original_rooms, "removed_room_ids": []}
    for base_rooms, base_removed in _candidate_sets(original_rooms):
        t3_pack = _build_t3_placements(display_classes, zoning, circulation, base_rooms, int(t3_count), float(t3_width_m), float(t3_depth_m), allow_d7=allow_d7)
        rooms_after_t3 = list(t3_pack.get("kept_rooms", base_rooms))
        t5_pack = _build_t5_placements(display_classes, zoning, circulation, rooms_after_t3, int(t5_count), float(t5_width_m), float(t5_depth_m), allow_d7=allow_d7, blocked_soft_rects=list(t3_pack.get("soft", [])))
        kept_after_t5, removed_by_t5_soft = _filter_fitting_rooms_below_t5_soft(list(t5_pack.get("kept_rooms", rooms_after_t3)), list(t5_pack.get("soft", [])))
        t5_pack["kept_rooms"] = kept_after_t5
        t5_pack["removed_room_ids"] = list(dict.fromkeys(list(t5_pack.get("removed_room_ids", [])) + list(removed_by_t5_soft)))
        placed3 = int(t3_pack.get("placed", 0) or 0)
        placed5 = int(t5_pack.get("placed", 0) or 0)
        removed_ids = list(dict.fromkeys(list(base_removed) + list(t3_pack.get("removed_room_ids", [])) + list(t5_pack.get("removed_room_ids", []))))
        score = (placed3, placed5, -len(removed_ids))
        if score > best["score"]:
            best = {
                "score": score,
                "t3": t3_pack,
                "t5": t5_pack,
                "kept_rooms": list(t5_pack.get("kept_rooms", rooms_after_t3)),
                "removed_room_ids": removed_ids,
            }
        if placed3 >= int(t3_count) and placed5 >= int(t5_count):
            break

    return {
        "t3": best.get("t3") or {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0, "kept_rooms": original_rooms, "removed_room_ids": []},
        "t5": best.get("t5") or {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0, "kept_rooms": original_rooms, "removed_room_ids": []},
        "kept_rooms": list(best.get("kept_rooms", original_rooms)),
        "removed_room_ids": list(best.get("removed_room_ids", [])),
    }


def _rect_intersection(a: dict, b: dict) -> dict | None:
    ax1, ay1 = float(a.get("x", 0.0)), float(a.get("y", 0.0))
    ax2, ay2 = ax1 + float(a.get("length", 0.0)), ay1 + float(a.get("width", 0.0))
    bx1, by1 = float(b.get("x", 0.0)), float(b.get("y", 0.0))
    bx2, by2 = bx1 + float(b.get("length", 0.0)), by1 + float(b.get("width", 0.0))
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return None
    return {"x": ix1, "y": iy1, "length": ix2 - ix1, "width": iy2 - iy1}


def _rects_overlap(a: dict, b: dict) -> bool:
    return _rect_intersection(a, b) is not None





def _build_omni_d1d2_placements(display_classes: dict | None, count: int, width_m: float, depth_m: float, soft_offset_m: float = 0.80, min_offset_m: float = 0.40, blocked_soft_rects: list[dict] | None = None, role_prefix: str = "t6", family: str = "T6") -> dict:
    """Place omni-directional interactive devices inside D1 first then D2.

    Revised behavior for T6/T7:
    - mimic the side-biased hosting relation used for T2/T4 inside D1/D2
    - keep the front side clear for interaction
    - allow the other three soft sides to coexist with display attachment logic
    - maximize capacity using minimum-buffer packing rather than soft-buffer packing
    """
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
    if not display_classes or count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    blocked_soft_rects = list(blocked_soft_rects or [])
    candidates = []
    for key in ("D1", "D2"):
        for item in display_classes.get(key, []) or []:
            rect = item.get("rect") if isinstance(item, dict) else None
            if rect:
                candidates.append((key, rect))

    placed = 0
    total_capacity = 0
    idx = 1
    min_span_x = width_m + 2.0 * min_offset_m
    min_span_y = depth_m + 2.0 * min_offset_m

    for key, host in candidates:
        if placed >= count:
            break
        host_l = float(host.get("length", 0.0))
        host_w = float(host.get("width", 0.0))
        if host_l + 1e-6 < min_span_x or host_w + 1e-6 < min_span_y:
            continue

        # Density-oriented axis selection for omni T-families (T6/T7): compare
        # horizontal-row capacity against vertical-column capacity, then choose
        # the denser valid arrangement inside D1/D2.
        x_cap_test = max(0, int(host_l // max(min_span_x, 1e-6))) if (host_l + 1e-6 >= min_span_x and host_w + 1e-6 >= min_span_y) else 0
        y_cap_test = max(0, int(host_w // max(min_span_y, 1e-6))) if (host_w + 1e-6 >= min_span_y and host_l + 1e-6 >= min_span_x) else 0
        if x_cap_test <= 0 and y_cap_test <= 0:
            continue
        orient_x = x_cap_test >= y_cap_test
        if orient_x:
            cap = max(0, int(host_l // max(min_span_x, 1e-6)))
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            start_x = float(host["x"]) + max(0.0, (host_l - n * min_span_x) / 2.0)
            # Side-biased relation: keep the interaction/front side clear toward the open field (downward),
            # so the device sits against the opposite side of the island.
            hard_y = float(host["y"]) + host_w - depth_m - min_offset_m
            for i in range(n):
                min_x = start_x + i * min_span_x
                hard_x = min_x + min_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
                min_buf = {"x": min_x, "y": hard_y - min_offset_m, "length": min_span_x, "width": min_span_y}
                if any(_rects_overlap(min_buf, blk) for blk in blocked_soft_rects):
                    continue
                soft_buf = {"x": hard_x - soft_offset_m, "y": hard_y - soft_offset_m, "length": width_m + 2.0 * soft_offset_m, "width": depth_m + 2.0 * soft_offset_m}
                result["hard"].append(_rect_obj(hard, f"interactive_{role_prefix}", family=family, module_index=idx, host_key=key, orientation="S", lineweight="heavy"))
                result["min"].append(_rect_obj(min_buf, f"interactive_{role_prefix}_buffer_min", family=family, module_index=idx, host_key=key))
                result["soft"].append(_rect_obj(soft_buf, f"interactive_{role_prefix}_buffer", family=family, module_index=idx, host_key=key))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"{family}-{idx}", role="fixture_label", text_size="small"))
                # Only the front side stays clear; the other three soft sides can host / coexist with display fixtures.
                front_clear = {"x": soft_buf["x"], "y": soft_buf["y"], "length": soft_buf["length"], "width": soft_offset_m}
                result["clear"].append(_rect_intersection(front_clear, host) or front_clear)
                idx += 1
                placed += 1
                if placed >= count:
                    break
        else:
            cap = max(0, int(host_w // max(min_span_y, 1e-6)))
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            start_y = float(host["y"]) + max(0.0, (host_w - n * min_span_y) / 2.0)
            hard_x = float(host["x"]) + host_l - width_m - min_offset_m
            for i in range(n):
                min_y = start_y + i * min_span_y
                hard_y = min_y + min_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
                min_buf = {"x": hard_x - min_offset_m, "y": min_y, "length": min_span_x, "width": min_span_y}
                if any(_rects_overlap(min_buf, blk) for blk in blocked_soft_rects):
                    continue
                soft_buf = {"x": hard_x - soft_offset_m, "y": hard_y - soft_offset_m, "length": width_m + 2.0 * soft_offset_m, "width": depth_m + 2.0 * soft_offset_m}
                result["hard"].append(_rect_obj(hard, f"interactive_{role_prefix}", family=family, module_index=idx, host_key=key, orientation="S", lineweight="heavy"))
                result["min"].append(_rect_obj(min_buf, f"interactive_{role_prefix}_buffer_min", family=family, module_index=idx, host_key=key))
                result["soft"].append(_rect_obj(soft_buf, f"interactive_{role_prefix}_buffer", family=family, module_index=idx, host_key=key))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"{family}-{idx}", role="fixture_label", text_size="small"))
                front_clear = {"x": soft_buf["x"], "y": soft_buf["y"], "length": soft_buf["length"], "width": soft_offset_m}
                result["clear"].append(_rect_intersection(front_clear, host) or front_clear)
                idx += 1
                placed += 1
                if placed >= count:
                    break

    result["placed"] = placed
    result["capacity"] = total_capacity
    return result

def _build_t6_placements(display_classes: dict | None, count: int, width_m: float, depth_m: float, blocked_soft_rects: list[dict] | None = None) -> dict:
    return _build_omni_d1d2_placements(display_classes, count, width_m, depth_m, soft_offset_m=0.80, min_offset_m=0.40, blocked_soft_rects=blocked_soft_rects, role_prefix='t6', family='T6')


def _build_t7_placements(display_classes: dict | None, count: int, width_m: float, depth_m: float, blocked_soft_rects: list[dict] | None = None) -> dict:
    return _build_omni_d1d2_placements(display_classes, count, width_m, depth_m, soft_offset_m=0.80, min_offset_m=0.40, blocked_soft_rects=blocked_soft_rects, role_prefix='t7', family='T7')


T8_CHECKOUT_MIN_TRIMMED_WIDTH_M = 1.50
T8_D8_SPACING_MIN_M = 1.20
T8_D8_SPACING_MAX_M = 1.60


def _pack_count_and_gap(host_span: float, module_span: float, gap_min: float, gap_max: float) -> tuple[int, float]:
    """Return deterministic count and inter-module gap for D8 packing.

    Modules must keep a gap between gap_min and gap_max. Extra residual width is
    absorbed by outer margins once the gap reaches gap_max.
    """
    if host_span + 1e-6 < module_span or module_span <= 0:
        return 0, 0.0
    n = int((host_span + gap_min) // (module_span + gap_min))
    n = max(1, n)
    while n > 0:
        if n == 1:
            return 1, 0.0
        residual = host_span - n * module_span
        if residual + 1e-6 < (n - 1) * gap_min:
            n -= 1
            continue
        gap = residual / (n - 1)
        if gap > gap_max:
            gap = gap_max
        if gap + 1e-6 < gap_min:
            n -= 1
            continue
        return n, gap
    return 0, 0.0




def _d8_host_attachment_side(display_classes: dict | None, host: dict) -> str:
    """Infer which wall side a D8 host touches so T8 can attach to that wall.

    Returns one of: right, left, top, bottom. The T8 front/min/soft buffer
    is then projected toward the opposite side, i.e. toward the circulation.
    """
    host_x = float(host.get("x", 0.0)); host_y = float(host.get("y", 0.0))
    host_l = float(host.get("length", 0.0)); host_w = float(host.get("width", 0.0))
    xs=[]; ys=[]
    if display_classes:
        for items in display_classes.values():
            for item in items or []:
                r = item.get("rect") if isinstance(item, dict) else None
                if not r:
                    continue
                x=float(r.get("x",0.0)); y=float(r.get("y",0.0)); l=float(r.get("length",0.0)); w=float(r.get("width",0.0))
                xs.extend([x, x+l]); ys.extend([y, y+w])
    cx = (min(xs)+max(xs))/2.0 if xs else host_x + host_l/2.0
    cy = (min(ys)+max(ys))/2.0 if ys else host_y + host_w/2.0
    vertical_wall_host = host_w + 1e-6 >= host_l
    if vertical_wall_host:
        return "right" if (host_x + host_l/2.0) >= cx else "left"
    return "top" if (host_y + host_w/2.0) >= cy else "bottom"


def _t8_d8_wall_attached_rects(display_classes: dict | None, host: dict, width_m: float, depth_m: float, side_offset_m: float, front_soft_m: float, front_min_m: float, along_pos: float):
    """Build T8 hard/min/soft rects attached to D8 wall with buffer facing circulation."""
    host_x = float(host.get("x", 0.0)); host_y = float(host.get("y", 0.0))
    host_l = float(host.get("length", 0.0)); host_w = float(host.get("width", 0.0))
    side = _d8_host_attachment_side(display_classes, host)
    if side in ("right", "left"):
        # vertical side-wall D8: long T8 side runs parallel to wall (Y axis)
        y = along_pos
        x = host_x + host_l - depth_m if side == "right" else host_x
        hard = {"x": x, "y": y, "length": depth_m, "width": width_m}
        if side == "right":
            min_buf = {"x": x - front_min_m, "y": y - side_offset_m, "length": front_min_m + depth_m, "width": width_m + 2.0 * side_offset_m}
            soft_buf = {"x": x - front_soft_m, "y": y - side_offset_m, "length": front_soft_m + depth_m, "width": width_m + 2.0 * side_offset_m}
            orientation = "W"  # front faces west / inward circulation
        else:
            min_buf = {"x": x, "y": y - side_offset_m, "length": depth_m + front_min_m, "width": width_m + 2.0 * side_offset_m}
            soft_buf = {"x": x, "y": y - side_offset_m, "length": depth_m + front_soft_m, "width": width_m + 2.0 * side_offset_m}
            orientation = "E"  # front faces east / inward circulation
        return hard, min_buf, soft_buf, orientation
    else:
        # horizontal D8 host: long T8 side runs parallel to wall (X axis)
        x = along_pos
        y = host_y + host_w - depth_m if side == "top" else host_y
        hard = {"x": x, "y": y, "length": width_m, "width": depth_m}
        if side == "top":
            min_buf = {"x": x - side_offset_m, "y": y - front_min_m, "length": width_m + 2.0 * side_offset_m, "width": front_min_m + depth_m}
            soft_buf = {"x": x - side_offset_m, "y": y - front_soft_m, "length": width_m + 2.0 * side_offset_m, "width": front_soft_m + depth_m}
            orientation = "S"
        else:
            min_buf = {"x": x - side_offset_m, "y": y, "length": width_m + 2.0 * side_offset_m, "width": depth_m + front_min_m}
            soft_buf = {"x": x - side_offset_m, "y": y, "length": width_m + 2.0 * side_offset_m, "width": depth_m + front_soft_m}
            orientation = "N"
        return hard, min_buf, soft_buf, orientation

def _t8_d8_candidate_modules(display_classes: dict | None, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 2.40, front_min_m: float = 1.20, start_index: int = 1) -> list[dict]:
    """Return deterministic T8 candidate modules inside D8.

    D8 rule: T8 is attached directly to the wall side, its long side remains
    parallel to the wall, and its min/soft buffer always projects inward toward
    the circulation side. The hard footprint must stay inside D8; buffers may
    project outside D8 toward circulation.
    """
    modules = []
    if not display_classes or width_m <= 0 or depth_m <= 0:
        return modules

    candidates = []
    for item in display_classes.get("D8", []) or []:
        rect = item.get("rect") if isinstance(item, dict) else None
        if rect:
            area = float(rect.get("length", 0.0)) * float(rect.get("width", 0.0))
            candidates.append((-area, rect))
    candidates.sort(key=lambda t: t[0])

    idx = start_index
    for _, host in candidates:
        host_x = float(host.get("x", 0.0)); host_y = float(host.get("y", 0.0))
        host_l = float(host.get("length", 0.0)); host_w = float(host.get("width", 0.0))
        vertical_wall_host = host_w + 1e-6 >= host_l
        if vertical_wall_host:
            if host_l + 1e-6 < depth_m or host_w + 1e-6 < width_m:
                continue
            cap, gap = _pack_count_and_gap(host_w, width_m, T8_D8_SPACING_MIN_M, T8_D8_SPACING_MAX_M)
            if cap <= 0:
                continue
            used_span = cap * width_m + max(0, cap - 1) * gap
            y_cursor = host_y + max(0.0, (host_w - used_span) / 2.0)
            for module_i in range(cap):
                hard, min_buf, soft_buf, orientation = _t8_d8_wall_attached_rects(display_classes, host, width_m, depth_m, side_offset_m, front_soft_m, front_min_m, y_cursor)
                modules.append({
                    "hard": _rect_obj(hard, "interactive_t8", family="T8", module_index=idx, host_key="D8", orientation=orientation, lineweight="heavy"),
                    "min": _rect_obj(min_buf, "interactive_t8_buffer_min", family="T8", module_index=idx, host_key="D8"),
                    "soft": _rect_obj(soft_buf, "interactive_t8_buffer", family="T8", module_index=idx, host_key="D8"),
                    "label": _text_obj(*_center(hard), f"T8-{idx}", role="fixture_label", text_size="small"),
                    "clear": hard,
                })
                idx += 1
                y_cursor += width_m + (gap if module_i < cap - 1 else 0.0)
        else:
            if host_l + 1e-6 < width_m or host_w + 1e-6 < depth_m:
                continue
            cap, gap = _pack_count_and_gap(host_l, width_m, T8_D8_SPACING_MIN_M, T8_D8_SPACING_MAX_M)
            if cap <= 0:
                continue
            used_span = cap * width_m + max(0, cap - 1) * gap
            x_cursor = host_x + max(0.0, (host_l - used_span) / 2.0)
            for module_i in range(cap):
                hard, min_buf, soft_buf, orientation = _t8_d8_wall_attached_rects(display_classes, host, width_m, depth_m, side_offset_m, front_soft_m, front_min_m, x_cursor)
                modules.append({
                    "hard": _rect_obj(hard, "interactive_t8", family="T8", module_index=idx, host_key="D8", orientation=orientation, lineweight="heavy"),
                    "min": _rect_obj(min_buf, "interactive_t8_buffer_min", family="T8", module_index=idx, host_key="D8"),
                    "soft": _rect_obj(soft_buf, "interactive_t8_buffer", family="T8", module_index=idx, host_key="D8"),
                    "label": _text_obj(*_center(hard), f"T8-{idx}", role="fixture_label", text_size="small"),
                    "clear": hard,
                })
                idx += 1
                x_cursor += width_m + (gap if module_i < cap - 1 else 0.0)
    return modules


def _t8_checkout_candidate_modules(zoning: dict, circulation: dict | None, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 2.40, front_min_m: float = 1.20, start_index: int = 1) -> tuple[list[dict], int]:
    """Return deterministic candidate T8 modules inside checkout and checkout capacity."""
    modules = []
    checkout = zoning.get("checkout_zone") or {}
    fitting = zoning.get("fitting_zone") or {}
    _, _, checkout_buffer_rect = _build_checkout_buffer(zoning, circulation, None)
    counter_rect = _checkout_counter_rect(checkout_buffer_rect)
    if not checkout or not counter_rect or width_m <= 0 or depth_m <= 0:
        return modules, 0

    host = dict(checkout)
    counter_top_y = float(counter_rect["y"] + counter_rect["width"])
    hard_y = counter_top_y

    fit_right_x = float(fitting.get("x", 0.0)) + float(fitting.get("length", 0.0))
    checkout_left_x = float(checkout.get("x", 0.0))
    checkout_right_x = float(checkout.get("x", 0.0)) + float(checkout.get("length", 0.0))
    fitting_left_x = float(fitting.get("x", 0.0))

    start_from_right = False
    if abs(checkout_left_x - fit_right_x) <= 1e-6:
        start_from_right = False
    elif abs(checkout_right_x - fitting_left_x) <= 1e-6:
        start_from_right = True

    step_x = width_m + 2.0 * side_offset_m
    host_x0 = float(host.get("x", 0.0))
    host_x1 = float(host.get("x", 0.0)) + float(host.get("length", 0.0))

    idx = start_index
    capacity = 0
    if start_from_right:
        hard_x = host_x1 - width_m
        while hard_x >= host_x0 - 1e-6:
            hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
            min_buf_raw = {"x": hard_x - side_offset_m, "y": hard_y - (front_min_m + depth_m), "length": width_m + 2.0 * side_offset_m, "width": depth_m + front_min_m + depth_m}
            soft_buf_raw = {"x": hard_x - side_offset_m, "y": hard_y - (front_soft_m + depth_m), "length": width_m + 2.0 * side_offset_m, "width": depth_m + front_soft_m + depth_m}
            trimmed_width = float(soft_buf_raw["x"]) - host_x0
            if trimmed_width < T8_CHECKOUT_MIN_TRIMMED_WIDTH_M - 1e-6:
                break
            capacity += 1
            modules.append({
                "hard": _rect_obj(hard, "interactive_t8", family="T8", module_index=idx, host_key="CHECKOUT", orientation="S", lineweight="heavy"),
                "min": _rect_obj(min_buf_raw, "interactive_t8_buffer_min", family="T8", module_index=idx, host_key="CHECKOUT"),
                "soft": _rect_obj(soft_buf_raw, "interactive_t8_buffer", family="T8", module_index=idx, host_key="CHECKOUT"),
                "label": _text_obj(*_center(hard), f"T8-{idx}", role="fixture_label", text_size="small"),
                "clear": hard,
            })
            idx += 1
            hard_x -= step_x
    else:
        hard_x = host_x0
        while hard_x + width_m <= host_x1 + 1e-6:
            hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
            min_buf_raw = {"x": hard_x - side_offset_m, "y": hard_y - (front_min_m + depth_m), "length": width_m + 2.0 * side_offset_m, "width": depth_m + front_min_m + depth_m}
            soft_buf_raw = {"x": hard_x - side_offset_m, "y": hard_y - (front_soft_m + depth_m), "length": width_m + 2.0 * side_offset_m, "width": depth_m + front_soft_m + depth_m}
            trimmed_width = host_x1 - float(soft_buf_raw["x"] + soft_buf_raw["length"])
            if trimmed_width < T8_CHECKOUT_MIN_TRIMMED_WIDTH_M - 1e-6:
                break
            capacity += 1
            modules.append({
                "hard": _rect_obj(hard, "interactive_t8", family="T8", module_index=idx, host_key="CHECKOUT", orientation="S", lineweight="heavy"),
                "min": _rect_obj(min_buf_raw, "interactive_t8_buffer_min", family="T8", module_index=idx, host_key="CHECKOUT"),
                "soft": _rect_obj(soft_buf_raw, "interactive_t8_buffer", family="T8", module_index=idx, host_key="CHECKOUT"),
                "label": _text_obj(*_center(hard), f"T8-{idx}", role="fixture_label", text_size="small"),
                "clear": hard,
            })
            idx += 1
            hard_x += step_x
    return modules, capacity
def _build_t8_d8_fallback(display_classes: dict | None, count: int, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 2.40, front_min_m: float = 1.20, start_index: int = 1) -> dict:
    """Fallback T8 host inside D8.

    D8 wall rule: every T8 hard footprint is attached directly to the wall side,
    remains parallel to the wall, and projects its minimum/soft buffer inward
    toward circulation. Hard footprint must fit inside D8.
    """
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
    if not display_classes or count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    candidates = []
    for item in display_classes.get("D8", []) or []:
        rect = item.get("rect") if isinstance(item, dict) else None
        if rect:
            area = float(rect.get("length", 0.0)) * float(rect.get("width", 0.0))
            candidates.append((-area, rect))
    candidates.sort(key=lambda t: t[0])

    placed = 0
    total_capacity = 0
    idx = start_index
    for _, host in candidates:
        if placed >= count:
            break
        host_x = float(host.get("x", 0.0)); host_y = float(host.get("y", 0.0))
        host_l = float(host.get("length", 0.0)); host_w = float(host.get("width", 0.0))
        vertical_wall_host = host_w + 1e-6 >= host_l
        if vertical_wall_host:
            if host_l + 1e-6 < depth_m or host_w + 1e-6 < width_m:
                continue
            cap, gap = _pack_count_and_gap(host_w, width_m, T8_D8_SPACING_MIN_M, T8_D8_SPACING_MAX_M)
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            used_span = n * width_m + max(0, n - 1) * gap
            y_cursor = host_y + max(0.0, (host_w - used_span) / 2.0)
            for module_i in range(n):
                hard, min_buf, soft_buf, orientation = _t8_d8_wall_attached_rects(display_classes, host, width_m, depth_m, side_offset_m, front_soft_m, front_min_m, y_cursor)
                result["hard"].append(_rect_obj(hard, "interactive_t8", family="T8", module_index=idx, host_key="D8", orientation=orientation, lineweight="heavy"))
                result["min"].append(_rect_obj(min_buf, "interactive_t8_buffer_min", family="T8", module_index=idx, host_key="D8"))
                result["soft"].append(_rect_obj(soft_buf, "interactive_t8_buffer", family="T8", module_index=idx, host_key="D8"))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"T8-{idx}", role="fixture_label", text_size="small"))
                result["clear"].append(hard)
                idx += 1; placed += 1
                y_cursor += width_m + (gap if module_i < n - 1 else 0.0)
                if placed >= count:
                    break
        else:
            if host_l + 1e-6 < width_m or host_w + 1e-6 < depth_m:
                continue
            cap, gap = _pack_count_and_gap(host_l, width_m, T8_D8_SPACING_MIN_M, T8_D8_SPACING_MAX_M)
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            used_span = n * width_m + max(0, n - 1) * gap
            x_cursor = host_x + max(0.0, (host_l - used_span) / 2.0)
            for module_i in range(n):
                hard, min_buf, soft_buf, orientation = _t8_d8_wall_attached_rects(display_classes, host, width_m, depth_m, side_offset_m, front_soft_m, front_min_m, x_cursor)
                result["hard"].append(_rect_obj(hard, "interactive_t8", family="T8", module_index=idx, host_key="D8", orientation=orientation, lineweight="heavy"))
                result["min"].append(_rect_obj(min_buf, "interactive_t8_buffer_min", family="T8", module_index=idx, host_key="D8"))
                result["soft"].append(_rect_obj(soft_buf, "interactive_t8_buffer", family="T8", module_index=idx, host_key="D8"))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"T8-{idx}", role="fixture_label", text_size="small"))
                result["clear"].append(hard)
                idx += 1; placed += 1
                x_cursor += width_m + (gap if module_i < n - 1 else 0.0)
                if placed >= count:
                    break

    result["placed"] = placed
    result["capacity"] = total_capacity
    return result


def _build_t8_placements(display_classes: dict | None, zoning: dict, circulation: dict | None, count: int, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 2.40, front_min_m: float = 1.20) -> dict:
    """Place T8 in checkout first with staged D8 relief.

    Current rule sequence:
    - first T8 in checkout when checkout can host it
    - second T8 in D8 when D8 can host it
    - third T8 beside the first one back in checkout
    - remaining T8 continue in checkout, then continue in D8 if needed
    - if checkout cannot host any T8, fall back fully to D8
    """
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
    if count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    checkout_modules, checkout_capacity = _t8_checkout_candidate_modules(zoning, circulation, width_m, depth_m, side_offset_m=side_offset_m, front_soft_m=front_soft_m, front_min_m=front_min_m, start_index=1)
    d8_modules = _t8_d8_candidate_modules(display_classes, width_m, depth_m, side_offset_m=side_offset_m, front_soft_m=front_soft_m, front_min_m=front_min_m, start_index=1)
    d8_capacity = len(d8_modules)
    result["capacity"] = checkout_capacity + d8_capacity

    if checkout_capacity <= 0:
        return _build_t8_d8_fallback(display_classes, count, width_m, depth_m, side_offset_m=side_offset_m, front_soft_m=front_soft_m, front_min_m=front_min_m, start_index=1)

    selected = []
    # first one in checkout
    if count >= 1 and len(checkout_modules) >= 1:
        selected.append(checkout_modules[0])
    # second one in D8 when available
    if count >= 2 and len(d8_modules) >= 1:
        selected.append(d8_modules[0])
    # then continue beside the first one in checkout
    checkout_idx = 1
    while len(selected) < count and checkout_idx < len(checkout_modules):
        selected.append(checkout_modules[checkout_idx])
        checkout_idx += 1
    # if more are still requested, continue in D8 after the reserved second one
    d8_idx = 1 if count >= 2 and len(d8_modules) >= 1 else 0
    while len(selected) < count and d8_idx < len(d8_modules):
        selected.append(d8_modules[d8_idx])
        d8_idx += 1

    # renumber sequentially for clean labels and exported metadata
    for idx, module in enumerate(selected, start=1):
        for key in ("hard", "min", "soft"):
            module[key]["module_index"] = idx
        module["label"]["text"] = f"T8-{idx}"
        result["hard"].append(module["hard"])
        result["min"].append(module["min"])
        result["soft"].append(module["soft"])
        result["labels"].append(module["label"])
        result["clear"].append(module["clear"])

    result["placed"] = len(selected)
    return result

def _t9_candidate_hosts(display_classes: dict | None, zoning: dict) -> list[tuple[str, dict]]:
    """Return deterministic T9 host order: D1 nearest Checkout first, then D2."""
    hosts = []
    if not display_classes:
        return hosts

    checkout = zoning.get("checkout_zone") or {}
    qx = float(checkout.get("x", 0.0)) + float(checkout.get("length", 0.0)) / 2.0
    qy = float(checkout.get("y", 0.0)) + float(checkout.get("width", 0.0)) / 2.0

    d1_ranked = []
    for item in display_classes.get("D1", []) or []:
        rect = item.get("rect") if isinstance(item, dict) else None
        if rect:
            cx = float(rect.get("x", 0.0)) + float(rect.get("length", 0.0)) / 2.0
            cy = float(rect.get("y", 0.0)) + float(rect.get("width", 0.0)) / 2.0
            dist2 = (cx - qx) ** 2 + (cy - qy) ** 2
            d1_ranked.append((dist2, rect))
    d1_ranked.sort(key=lambda t: t[0])

    hosts.extend([("D1", rect) for _, rect in d1_ranked])
    for item in display_classes.get("D2", []) or []:
        rect = item.get("rect") if isinstance(item, dict) else None
        if rect:
            hosts.append(("D2", rect))
    return hosts


def _build_t9_placements(display_classes: dict | None, zoning: dict, count: int, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 2.40, front_min_m: float = 1.20, blocked_soft_rects: list[dict] | None = None) -> dict:
    """Place T9 in D1 nearest checkout first, then D2, using T8 envelope dimensions and display-island hosting behavior."""
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
    if not display_classes or count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    blocked_soft_rects = list(blocked_soft_rects or [])
    hosts = _t9_candidate_hosts(display_classes, zoning)

    placed = 0
    total_capacity = 0
    idx = 1
    span = width_m + 2.0 * side_offset_m

    for key, host in hosts:
        if placed >= count:
            break
        host_x = float(host.get("x", 0.0))
        host_y = float(host.get("y", 0.0))
        host_l = float(host.get("length", 0.0))
        host_w = float(host.get("width", 0.0))
        # Density-oriented orientation: evaluate both unrotated and rotated hosting modes
        # and choose the one that can host more T9 modules inside the checkout-side hosts.
        x_cap_test, _x_gap_test = _pack_count_and_gap(host_l, width_m, T8_D8_SPACING_MIN_M, T8_D8_SPACING_MAX_M) if (host_l + 1e-6 >= width_m and host_w + 1e-6 >= depth_m) else (0, 0.0)
        y_cap_test, _y_gap_test = _pack_count_and_gap(host_w, width_m, T8_D8_SPACING_MIN_M, T8_D8_SPACING_MAX_M) if (host_w + 1e-6 >= width_m and host_l + 1e-6 >= depth_m) else (0, 0.0)
        if x_cap_test <= 0 and y_cap_test <= 0:
            continue
        orient_x = x_cap_test >= y_cap_test

        if orient_x:
            if host_l + 1e-6 < width_m or host_w + 1e-6 < depth_m:
                continue
            cap = max(0, int(host_l // span))
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            x_cursor = host_x + max(0.0, (host_l - n * span) / 2.0)
            hard_y = host_y + max(0.0, (host_w - depth_m) / 2.0)
            for _ in range(n):
                hard_x = x_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    x_cursor += span
                    continue
                min_buf = {"x": hard_x - side_offset_m, "y": hard_y, "length": width_m + 2.0 * side_offset_m, "width": depth_m + front_min_m + depth_m}
                soft_buf = {"x": hard_x - side_offset_m, "y": hard_y, "length": width_m + 2.0 * side_offset_m, "width": depth_m + front_soft_m + depth_m}
                result["hard"].append(_rect_obj(hard, "interactive_t9", family="T9", module_index=idx, host_key=key, orientation="N", lineweight="heavy", fill="cyan"))
                result["min"].append(_rect_obj(min_buf, "interactive_t9_buffer_min", family="T9", module_index=idx, host_key=key, dash=True, lineweight="light"))
                result["soft"].append(_rect_obj(soft_buf, "interactive_t9_buffer", family="T9", module_index=idx, host_key=key, dash=True, lineweight="light"))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"T9-{idx}", role="fixture_label", text_size="small"))
                result["clear"].append(hard)
                idx += 1
                placed += 1
                x_cursor += span
                if placed >= count:
                    break
        else:
            if host_l + 1e-6 < depth_m or host_w + 1e-6 < width_m:
                continue
            cap = max(0, int(host_w // span))
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            y_cursor = host_y + max(0.0, (host_w - n * span) / 2.0)
            hard_x = host_x + max(0.0, (host_l - depth_m) / 2.0)
            for _ in range(n):
                hard_y = y_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    y_cursor += span
                    continue
                min_buf = {"x": hard_x, "y": hard_y - side_offset_m, "length": depth_m + front_min_m + depth_m, "width": width_m + 2.0 * side_offset_m}
                soft_buf = {"x": hard_x, "y": hard_y - side_offset_m, "length": depth_m + front_soft_m + depth_m, "width": width_m + 2.0 * side_offset_m}
                result["hard"].append(_rect_obj(hard, "interactive_t9", family="T9", module_index=idx, host_key=key, orientation="E", lineweight="heavy", fill="cyan"))
                result["min"].append(_rect_obj(min_buf, "interactive_t9_buffer_min", family="T9", module_index=idx, host_key=key, dash=True, lineweight="light"))
                result["soft"].append(_rect_obj(soft_buf, "interactive_t9_buffer", family="T9", module_index=idx, host_key=key, dash=True, lineweight="light"))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"T9-{idx}", role="fixture_label", text_size="small"))
                result["clear"].append(hard)
                idx += 1
                placed += 1
                y_cursor += span
                if placed >= count:
                    break

    result["placed"] = placed
    result["capacity"] = total_capacity
    return result


def _build_t2_placements(display_classes: dict | None, zoning: dict, count: int, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 1.60, front_min_m: float = 1.20, blocked_soft_rects: list[dict] | None = None) -> dict:
    """Place T2 Interactive Kiosk inside D1 first then D2.
    Uses hard-footprint containment so the kiosk can still be inserted in narrower D1/D2 islands,
    while soft/min-soft buffers are still drawn and used for local clearing (clipped to the host island).
    """
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
    if not display_classes or count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    blocked_soft_rects = list(blocked_soft_rects or [])

    candidates = []
    for key in ("D1", "D2"):
        for item in display_classes.get(key, []) or []:
            rect = item.get("rect") if isinstance(item, dict) else None
            if rect:
                candidates.append((key, rect))

    placed = 0
    total_capacity = 0
    idx = 1
    span = width_m + 2.0 * side_offset_m
    for key, host in candidates:
        if placed >= count:
            break
        host_l = float(host.get("length", 0.0))
        host_w = float(host.get("width", 0.0))

        # prefer stacking along the longer island direction, but require only hard containment
        orient_x = host_l >= host_w

        if orient_x:
            if host_l + 1e-6 < span or host_w + 1e-6 < depth_m:
                continue
            cap = max(0, int(host_l // span))
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            x_cursor = float(host["x"]) + max(0.0, (host_l - n * span) / 2.0)
            hard_y = float(host["y"]) + max(0.0, (host_w - depth_m) / 2.0)
            for _ in range(n):
                hard_x = x_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    x_cursor += span
                    continue
                # T2 buffers are U-shaped in plan logic: side offsets on left/right and front offset only; no rear expansion.
                # Represented here as the minimal bounding rectangle of that U-shape, with the rear edge aligned to the hard footprint rear.
                min_buf = {"x": x_cursor, "y": hard_y, "length": span, "width": depth_m + front_min_m}
                soft_buf = {"x": x_cursor, "y": hard_y, "length": span, "width": depth_m + front_soft_m}
                result["hard"].append(_rect_obj(hard, "interactive_t2", family="T2", module_index=idx, host_key=key, orientation="N", lineweight="heavy"))
                result["min"].append(_rect_obj(min_buf, "interactive_t2_buffer_min", family="T2", module_index=idx, host_key=key))
                result["soft"].append(_rect_obj(soft_buf, "interactive_t2_buffer", family="T2", module_index=idx, host_key=key))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"T2-{idx}", role="fixture_label", text_size="small"))
                # T4 may visually/projectively overlay existing fixture hard buffers with its dashed envelopes;
                # only the T4 hard footprint claims/removes area.
                clear_rect = hard
                result["clear"].append(clear_rect)
                idx += 1
                placed += 1
                x_cursor += span
                if placed >= count:
                    break
        else:
            if host_w + 1e-6 < span or host_l + 1e-6 < depth_m:
                continue
            cap = max(0, int(host_w // span))
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            y_cursor = float(host["y"]) + max(0.0, (host_w - n * span) / 2.0)
            hard_x = float(host["x"]) + max(0.0, (host_l - depth_m) / 2.0)
            for _ in range(n):
                hard_y = y_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    y_cursor += span
                    continue
                # Rotated case: U-shape buffers use side offsets on top/bottom and front offset only along +X; no rear expansion.
                min_buf = {"x": hard_x, "y": y_cursor, "length": depth_m + front_min_m, "width": span}
                soft_buf = {"x": hard_x, "y": y_cursor, "length": depth_m + front_soft_m, "width": span}
                result["hard"].append(_rect_obj(hard, "interactive_t2", family="T2", module_index=idx, host_key=key, orientation="E", lineweight="heavy"))
                result["min"].append(_rect_obj(min_buf, "interactive_t2_buffer_min", family="T2", module_index=idx, host_key=key))
                result["soft"].append(_rect_obj(soft_buf, "interactive_t2_buffer", family="T2", module_index=idx, host_key=key))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"T2-{idx}", role="fixture_label", text_size="small"))
                # T4 may visually/projectively overlay existing fixture hard buffers with its dashed envelopes;
                # only the T4 hard footprint claims/removes area.
                clear_rect = hard
                result["clear"].append(clear_rect)
                idx += 1
                placed += 1
                y_cursor += span
                if placed >= count:
                    break

    result["placed"] = placed
    result["capacity"] = total_capacity
    return result




def _build_t4_placements(display_classes: dict | None, zoning: dict, count: int, width_m: float, depth_m: float, side_offset_m: float = 0.60, front_soft_m: float = 1.60, front_min_m: float = 1.20, blocked_soft_rects: list[dict] | None = None) -> dict:
    """Place T4 Free-standing Smart / Magic Mirror inside D1 only, prioritizing D1 areas nearest the fitting suite."""
    result = {"hard": [], "min": [], "soft": [], "labels": [], "clear": [], "placed": 0, "capacity": 0}
    if not display_classes or count <= 0 or width_m <= 0 or depth_m <= 0:
        return result

    blocked_soft_rects = list(blocked_soft_rects or [])

    fitting = zoning.get("fitting_zone") or {}
    fx = float(fitting.get("x", 0.0)) + float(fitting.get("length", 0.0)) / 2.0
    fy = float(fitting.get("y", 0.0)) + float(fitting.get("width", 0.0)) / 2.0

    candidates = []
    for item in display_classes.get("D1", []) or []:
        rect = item.get("rect") if isinstance(item, dict) else None
        if rect:
            cx = float(rect.get("x", 0.0)) + float(rect.get("length", 0.0)) / 2.0
            cy = float(rect.get("y", 0.0)) + float(rect.get("width", 0.0)) / 2.0
            dist2 = (cx - fx) ** 2 + (cy - fy) ** 2
            candidates.append((dist2, rect))
    candidates.sort(key=lambda t: t[0])

    placed = 0
    total_capacity = 0
    idx = 1
    span = width_m + 2.0 * side_offset_m
    for _, host in candidates:
        if placed >= count:
            break
        host_l = float(host.get("length", 0.0))
        host_w = float(host.get("width", 0.0))
        orient_x = host_l >= host_w

        if orient_x:
            if host_l + 1e-6 < span or host_w + 1e-6 < depth_m:
                continue
            cap = max(0, int(host_l // span))
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            x_cursor = float(host["x"]) + max(0.0, (host_l - n * span) / 2.0)
            hard_y = float(host["y"]) + max(0.0, (host_w - depth_m) / 2.0)
            for _ in range(n):
                hard_x = x_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": width_m, "width": depth_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    x_cursor += span
                    continue
                min_buf = {"x": x_cursor, "y": hard_y, "length": span, "width": depth_m + front_min_m}
                soft_buf = {"x": x_cursor, "y": hard_y, "length": span, "width": depth_m + front_soft_m}
                result["hard"].append(_rect_obj(hard, "interactive_t4", family="T4", module_index=idx, host_key="D1", orientation="N", lineweight="heavy"))
                result["min"].append(_rect_obj(min_buf, "interactive_t4_buffer_min", family="T4", module_index=idx, host_key="D1"))
                result["soft"].append(_rect_obj(soft_buf, "interactive_t4_buffer", family="T4", module_index=idx, host_key="D1"))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"T4-{idx}", role="fixture_label", text_size="small"))
                clear_rect = _rect_intersection(soft_buf, host) or hard
                result["clear"].append(clear_rect)
                idx += 1
                placed += 1
                x_cursor += span
                if placed >= count:
                    break
        else:
            if host_w + 1e-6 < span or host_l + 1e-6 < depth_m:
                continue
            cap = max(0, int(host_w // span))
            total_capacity += cap
            if cap <= 0:
                continue
            n = min(cap, count - placed)
            y_cursor = float(host["y"]) + max(0.0, (host_w - n * span) / 2.0)
            hard_x = float(host["x"]) + max(0.0, (host_l - depth_m) / 2.0)
            for _ in range(n):
                hard_y = y_cursor + side_offset_m
                hard = {"x": hard_x, "y": hard_y, "length": depth_m, "width": width_m}
                if any(_rects_overlap(hard, blk) for blk in blocked_soft_rects):
                    y_cursor += span
                    continue
                min_buf = {"x": hard_x, "y": y_cursor, "length": depth_m + front_min_m, "width": span}
                soft_buf = {"x": hard_x, "y": y_cursor, "length": depth_m + front_soft_m, "width": span}
                result["hard"].append(_rect_obj(hard, "interactive_t4", family="T4", module_index=idx, host_key="D1", orientation="E", lineweight="heavy"))
                result["min"].append(_rect_obj(min_buf, "interactive_t4_buffer_min", family="T4", module_index=idx, host_key="D1"))
                result["soft"].append(_rect_obj(soft_buf, "interactive_t4_buffer", family="T4", module_index=idx, host_key="D1"))
                cx, cy = _center(hard)
                result["labels"].append(_text_obj(cx, cy, f"T4-{idx}", role="fixture_label", text_size="small"))
                clear_rect = _rect_intersection(soft_buf, host) or hard
                result["clear"].append(clear_rect)
                idx += 1
                placed += 1
                y_cursor += span
                if placed >= count:
                    break

    result["placed"] = placed
    result["capacity"] = total_capacity
    return result

def _generate_f5_fill_around_added_zone(hosted_rects: list[dict], host_islands: list[dict], zone_key: str | None = None) -> tuple[list[dict], list[dict]]:
    """Fill residual space between hosted added-zone pieces and host-island boundaries with F5 modules.
    Applies only where the hosted piece lies inside the host island. The F5 side touching the added-zone
    boundary is drawn with no buffer so the residual field reads as fully used without crossing into the added zone.
    For Digital Interaction, at least one side of the hosted zone is intentionally kept free of F5.
    """
    F5_L, F5_W, F5_BUF = 1.00, 0.60, 1.20
    fixtures: list[dict] = []
    buffers: list[dict] = []
    module_idx = 900000

    def add_f5(rect: dict, touch_side: str) -> None:
        nonlocal module_idx
        fixtures.append(_rect_obj(rect, 'display_gondola', family='F5', module_index=module_idx, graphic_class='rack', lineweight='heavy'))
        x, y, l, w = rect['x'], rect['y'], rect['length'], rect['width']
        if touch_side != 'left':
            buffers.append(_rect_obj({'x': x - F5_BUF, 'y': y, 'length': F5_BUF, 'width': w}, 'display_gondola_buffer', family='F5', module_index=module_idx, graphic_class='gondola_buffer', dash=True, lineweight='light'))
        if touch_side != 'right':
            buffers.append(_rect_obj({'x': x + l, 'y': y, 'length': F5_BUF, 'width': w}, 'display_gondola_buffer', family='F5', module_index=module_idx, graphic_class='gondola_buffer', dash=True, lineweight='light'))
        if touch_side != 'bottom':
            buffers.append(_rect_obj({'x': x, 'y': y - F5_BUF, 'length': l, 'width': F5_BUF}, 'display_gondola_buffer', family='F5', module_index=module_idx, graphic_class='gondola_buffer', dash=True, lineweight='light'))
        if touch_side != 'top':
            buffers.append(_rect_obj({'x': x, 'y': y + w, 'length': l, 'width': F5_BUF}, 'display_gondola_buffer', family='F5', module_index=module_idx, graphic_class='gondola_buffer', dash=True, lineweight='light'))
        module_idx += 1

    def fill_vertical_strip(strip: dict, touch_side: str) -> None:
        # modules use 0.60 across strip and 1.00 along Y
        if strip['length'] + 1e-6 < F5_W:
            return
        count = max(1, int(strip['width'] // F5_L))
        used = count * F5_L
        y0 = strip['y'] + (strip['width'] - used) / 2.0
        if touch_side == 'right':
            x = strip['x'] + strip['length'] - F5_W
        else:
            x = strip['x']
        for i in range(count):
            add_f5({'x': x, 'y': y0 + i * F5_L, 'length': F5_W, 'width': F5_L}, touch_side)

    def fill_horizontal_strip(strip: dict, touch_side: str) -> None:
        # modules use 1.00 along X and 0.60 across strip
        if strip['width'] + 1e-6 < F5_W:
            return
        count = max(1, int(strip['length'] // F5_L))
        used = count * F5_L
        x0 = strip['x'] + (strip['length'] - used) / 2.0
        if touch_side == 'top':
            y = strip['y'] + strip['width'] - F5_W
        else:
            y = strip['y']
        for i in range(count):
            add_f5({'x': x0 + i * F5_L, 'y': y, 'length': F5_L, 'width': F5_W}, touch_side)

    for hosted, island in zip(hosted_rects or [], host_islands or []):
        ix, iy, il, iw = island['x'], island['y'], island['length'], island['width']
        hx, hy, hl, hw = hosted['x'], hosted['y'], hosted['length'], hosted['width']

        residuals = {
            'left': max(0.0, hx - ix) * iw,
            'right': max(0.0, (ix + il) - (hx + hl)) * iw,
            'bottom': max(0.0, hy - iy) * hl,
            'top': max(0.0, (iy + iw) - (hy + hw)) * hl,
        }
        free_side = None
        if zone_key == 'digital_interaction':
            candidates = [(side, area) for side, area in residuals.items() if area > 1e-6]
            if candidates:
                free_side = max(candidates, key=lambda kv: kv[1])[0]

        # left residual
        if hx - ix > 1e-6 and free_side != 'left':
            fill_vertical_strip({'x': ix, 'y': iy, 'length': hx - ix, 'width': iw}, 'right')
        # right residual
        if (ix + il) - (hx + hl) > 1e-6 and free_side != 'right':
            fill_vertical_strip({'x': hx + hl, 'y': iy, 'length': (ix + il) - (hx + hl), 'width': iw}, 'left')
        # bottom residual
        if hy - iy > 1e-6 and free_side != 'bottom':
            fill_horizontal_strip({'x': hx, 'y': iy, 'length': hl, 'width': hy - iy}, 'top')
        # top residual
        if (iy + iw) - (hy + hw) > 1e-6 and free_side != 'top':
            fill_horizontal_strip({'x': hx, 'y': hy + hw, 'length': hl, 'width': (iy + iw) - (hy + hw)}, 'bottom')

    return fixtures, buffers

def _wall_depth_and_buffer(family: str, host_depth: float) -> tuple[float, float] | None:
    host = float(host_depth)
    if family == "F1":
        if host >= 0.45 - 1e-6:
            return 0.45, 0.90
        if host >= 0.30 - 1e-6:
            return 0.30, 0.60
        return None
    if family == "F2":
        if host >= 0.60 - 1e-6:
            return 0.60, 1.20
        if host >= 0.50 - 1e-6:
            return 0.50, 0.90
        return None
    if family == "F3":
        if host >= 0.60 - 1e-6:
            return 0.60, 1.20
        if host >= 0.55 - 1e-6:
            return 0.55, 0.90
        return None
    return None


def _family_fallbacks(family: str) -> list[str]:
    return [family]


def _sequence_for_host(display_key: str, slot_count: int) -> list[str]:
    if slot_count <= 0:
        return []
    if display_key in {"D6", "D7", "D8"}:
        return ["F1" for _ in range(slot_count)]
    # D5 hosts F2 and F3 only.
    # Repetition rule: keep the first F2 as the anchor, then let F3
    # repeat contiguously on the F3 side instead of alternating F2/F3/F2/F3.
    if slot_count == 1:
        return ["F2"]
    return ["F2"] + ["F3" for _ in range(slot_count - 1)]


def _fit_widths(seq: list[str], usable_run: float, module_widths: list[float] | None = None, min_module: float = 0.60) -> list[float]:
    widths = []
    opts = sorted(module_widths or [1.20, 0.90, 0.60], reverse=True)
    remaining = float(usable_run)
    count = len(seq)
    for idx in range(count):
        slots_left = count - idx - 1
        chosen = None
        for opt in opts:
            if opt - remaining > 1e-6:
                continue
            after = remaining - opt
            if slots_left > 0 and after + 1e-6 < slots_left * min_module:
                continue
            chosen = opt
            break
        if chosen is None:
            chosen = min_module if remaining >= min_module - 1e-6 else max(0.0, remaining)
        widths.append(round(chosen, 6))
        remaining -= chosen
    return widths


def _host_side(host: dict, sales: dict) -> str:
    hx = float(host.get("x", 0.0))
    hlen = float(host.get("length", 0.0))
    sales_x = float(sales.get("x", 0.0))
    sales_r = sales_x + float(sales.get("length", 0.0))
    if abs(hx - sales_x) <= 0.25:
        return "left"
    if abs((hx + hlen) - sales_r) <= 0.25:
        return "right"
    host_cx = hx + hlen / 2.0
    sales_cx = sales_x + float(sales.get("length", 0.0)) / 2.0
    return "left" if host_cx <= sales_cx else "right"




def _ranges_overlap(a1: float, a2: float, b1: float, b2: float) -> bool:
    return min(a2, b2) - max(a1, b1) > 1e-6


def _nearest_spine_side(rect: dict, spine: dict | None) -> str | None:
    if not spine:
        return None
    rx1 = float(rect['x']); rx2 = rx1 + float(rect['length'])
    ry1 = float(rect['y']); ry2 = ry1 + float(rect['width'])
    sx1 = float(spine['x']); sx2 = sx1 + float(spine['length'])
    sy1 = float(spine['y']); sy2 = sy1 + float(spine['width'])
    candidates = []
    if _ranges_overlap(ry1, ry2, sy1, sy2):
        candidates.append((abs(rx1 - sx2), 'left'))
        candidates.append((abs(rx2 - sx1), 'right'))
    if _ranges_overlap(rx1, rx2, sx1, sx2):
        candidates.append((abs(ry1 - sy2), 'bottom'))
        candidates.append((abs(ry2 - sy1), 'top'))
    if not candidates:
        cx = rx1 + (rx2-rx1)/2.0; cy = ry1 + (ry2-ry1)/2.0
        scx = sx1 + (sx2-sx1)/2.0; scy = sy1 + (sy2-sy1)/2.0
        if abs(cx - scx) >= abs(cy - scy):
            return 'left' if cx < scx else 'right'
        return 'bottom' if cy < scy else 'top'
    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]




def _d1_vertical_spine_side(rect: dict, spine: dict | None) -> str:
    """Return the D1 side facing the vertical main spine using left/right only."""
    if not spine:
        return 'left'
    rx = float(rect['x']); rl = float(rect['length'])
    sx = float(spine['x']); sl = float(spine['length'])
    rcx = rx + rl / 2.0
    scx = sx + sl / 2.0
    return 'right' if rcx <= scx else 'left'


def _d1_touches_vertical_spine(rect: dict, spine: dict | None, tol: float = 1e-6) -> bool:
    """True only when a D1 boundary actually touches the vertical main spine.
    If there is a gap between D1 and the spine, F4 must not be generated.
    """
    if not spine:
        return False
    rx = float(rect['x']); rl = float(rect['length'])
    ry = float(rect['y']); rw = float(rect['width'])
    sx = float(spine['x']); sl = float(spine['length'])
    sy = float(spine['y']); sw = float(spine['width'])

    # Require vertical overlap as well as side contact.
    overlap_y = min(ry + rw, sy + sw) - max(ry, sy)
    if overlap_y <= tol:
        return False

    left_touch = abs((rx + rl) - sx) <= tol
    right_touch = abs(rx - (sx + sl)) <= tol
    return left_touch or right_touch

def _rect_from_side_band(rect: dict, side: str, band_depth: float) -> dict | None:
    x = float(rect['x']); y = float(rect['y']); l = float(rect['length']); w = float(rect['width'])
    if side == 'left' and l >= band_depth:
        return {'x': x, 'y': y, 'length': band_depth, 'width': w}
    if side == 'right' and l >= band_depth:
        return {'x': x + l - band_depth, 'y': y, 'length': band_depth, 'width': w}
    if side == 'bottom' and w >= band_depth:
        return {'x': x, 'y': y, 'length': l, 'width': band_depth}
    if side == 'top' and w >= band_depth:
        return {'x': x, 'y': y + w - band_depth, 'length': l, 'width': band_depth}
    return None


def _subtract_band(rect: dict, side: str, band_depth: float) -> dict | None:
    x = float(rect['x']); y = float(rect['y']); l = float(rect['length']); w = float(rect['width'])
    if side in {'left', 'right'}:
        if l - band_depth <= 0.60:
            return None
        if side == 'left':
            return {'x': x + band_depth, 'y': y, 'length': l - band_depth, 'width': w}
        return {'x': x, 'y': y, 'length': l - band_depth, 'width': w}
    if side in {'bottom', 'top'}:
        if w - band_depth <= 0.60:
            return None
        if side == 'bottom':
            return {'x': x, 'y': y + band_depth, 'length': l, 'width': w - band_depth}
        return {'x': x, 'y': y, 'length': l, 'width': w - band_depth}
    return None


def _rects_overlap(a: dict, b: dict, tol: float = 1e-6) -> bool:
    ax1 = float(a["x"])
    ay1 = float(a["y"])
    ax2 = ax1 + float(a["length"])
    ay2 = ay1 + float(a["width"])
    bx1 = float(b["x"])
    by1 = float(b["y"])
    bx2 = bx1 + float(b["length"])
    by2 = by1 + float(b["width"])
    return not (
        ax2 <= bx1 + tol or
        bx2 <= ax1 + tol or
        ay2 <= by1 + tol or
        by2 <= ay1 + tol
    )


def _collect_hard_fixture_rects(fixtures: list[dict] | None) -> list[dict]:
    rects: list[dict] = []
    for item in fixtures or []:
        if item.get("shape") == "rect" and all(k in item for k in ("x", "y", "length", "width")):
            rects.append({
                "x": float(item["x"]),
                "y": float(item["y"]),
                "length": float(item["length"]),
                "width": float(item["width"]),
            })
    return rects


def _generate_f7_1_modules(
    display_classes: dict | None,
    display_wall: list[dict] | None,
    display_gondola: list[dict] | None,
    circulation: dict | None = None,
    enable_d11_display: bool = False,
) -> tuple[list[dict], list[dict]]:
    if not display_classes:
        return [], []

    hard_size = 0.60
    soft_depth = 1.20  # fixed offset for F7.1 soft buffer
    min_soft_depth = 0.60  # inner minimum soft buffer
    clear_spacing = 0.60
    allowed_keys = ["D3", "D9", "D10", "D12"]
    if enable_d11_display:
        allowed_keys.append("D11")
    frontage_glass_offset_keys = {"D3", "D9", "D10", "D11", "D12"}
    glass_offset = 0.20

    mannequin_fixtures: list[dict] = []
    mannequin_buffers: list[dict] = []

    existing_hard = _collect_hard_fixture_rects(display_wall) + _collect_hard_fixture_rects(display_gondola)

    path_rects: list[dict] = []
    if circulation:
        for key in ["primary_spine", "service_connector"]:
            r = circulation.get(key)
            if r and all(k in r for k in ("x", "y", "length", "width")):
                path_rects.append(r)
        for key in ["secondary_aisles", "side_secondary_aisles", "territorial_aisles", "territorial_secondary_aisles"]:
            for r in circulation.get(key, []):
                if all(k in r for k in ("x", "y", "length", "width")):
                    path_rects.append(r)

    def _candidate_row_positions(host: dict) -> list[float]:
        hx = float(host["x"])
        host_l = float(host.get("length", 0.0))
        if host_l + 1e-6 < hard_size:
            return []

        max_count = max(1, int((host_l + clear_spacing) // (hard_size + clear_spacing)))
        for count in range(max_count, 1, -1):
            used = count * hard_size + (count - 1) * clear_spacing
            if used > host_l + 1e-6:
                continue
            start_x = hx + (host_l - used) / 2.0
            return [round(start_x + i * (hard_size + clear_spacing), 6) for i in range(count)]

        return [round(hx + (host_l - hard_size) / 2.0, 6)]

    def _vertical_aisle_candidates(keys: list[str], host: dict) -> list[dict]:
        out: list[dict] = []
        if not circulation:
            return out
        hy0 = float(host.get("y", 0.0))
        hy1 = hy0 + float(host.get("width", 0.0))
        for key in keys:
            for r in circulation.get(key, []) or []:
                if not all(k in r for k in ("x", "y", "length", "width")):
                    continue
                rx = float(r["x"]); ry = float(r["y"])
                rl = float(r["length"]); rw = float(r["width"])
                if rw + 1e-6 < rl:
                    continue  # keep vertical aisles only
                ry1 = ry + rw
                if min(hy1, ry1) - max(hy0, ry) <= 1e-6:
                    continue
                out.append(r)
        return out

    def _orientation_from_aisle_priority(hard_rect: dict, host: dict, prefer_side_secondary: bool = False) -> str:
        cx = float(hard_rect["x"]) + float(hard_rect["length"]) / 2.0
        if prefer_side_secondary:
            side_secondary = _vertical_aisle_candidates(["side_secondary_aisles"], host)
            secondary = _vertical_aisle_candidates(["secondary_aisles"], host)
            territorial = _vertical_aisle_candidates(["territorial_aisles", "territorial_secondary_aisles"], host)
            pool = side_secondary if side_secondary else (secondary if secondary else territorial)
        else:
            secondary = _vertical_aisle_candidates(["secondary_aisles", "side_secondary_aisles"], host)
            territorial = _vertical_aisle_candidates(["territorial_aisles", "territorial_secondary_aisles"], host)
            pool = secondary if secondary else territorial
        if not pool:
            return "front_up"
        nearest = min(pool, key=lambda r: abs((float(r["x"]) + float(r["length"]) / 2.0) - cx))
        aisle_cx = float(nearest["x"]) + float(nearest["length"]) / 2.0
        return "front_right" if aisle_cx > cx else "front_left"

    module_index = 1

    for dkey in allowed_keys:
        for item in display_classes.get(dkey, []):
            host = item.get("rect", {})
            if not host:
                continue

            host_l = float(host.get("length", 0.0))
            host_w = float(host.get("width", 0.0))
            if host_l + 1e-6 < hard_size or host_w + 1e-6 < hard_size:
                continue
            placement_host = dict(host)
            frontage_bottom_attached = dkey in frontage_glass_offset_keys

            placement_w = float(placement_host.get("width", 0.0))
            if host_l + 1e-6 < hard_size or placement_w + 1e-6 < hard_size:
                continue

            if frontage_bottom_attached:
                # Frontage islands attached to the south glass wall must keep
                # the hard footprint bottom edge 0.20 m above the glass line.
                hy = round(float(host["y"]) + glass_offset, 6)
                if hy + hard_size > float(host["y"]) + host_w + 1e-6:
                    continue
            else:
                hy = round(float(placement_host["y"]) + (placement_w - hard_size) / 2.0, 6)
            row_positions = _candidate_row_positions(placement_host)
            if dkey == "D11":
                row_positions = [round(float(placement_host["x"]) + (host_l - hard_size) / 2.0, 6)]

            # For repeated F7.1 inside D1: the mannequin column nearest the spine faces the spine.
            # Remaining columns follow aisle hierarchy: secondary aisles first, then territorial aisles.
            spine_side_index = None
            if dkey == "D1" and len(row_positions) > 1 and circulation and circulation.get("primary_spine"):
                spine = circulation.get("primary_spine")
                if spine and all(k in spine for k in ("x", "length")):
                    spine_cx_local = float(spine["x"]) + float(spine["length"]) / 2.0
                    host_cx = float(host["x"]) + float(host.get("length", 0.0)) / 2.0
                    spine_side_index = len(row_positions) - 1 if host_cx < spine_cx_local else 0

            for pos_idx, hx in enumerate(row_positions):
                hard_rect = {
                    "x": float(hx),
                    "y": float(hy),
                    "length": hard_size,
                    "width": hard_size,
                }

                # Hard square must remain non-blocking and must not collide with any hard fixture.
                if any(_rects_overlap(hard_rect, r) for r in existing_hard):
                    continue
                if any(_rects_overlap(hard_rect, p) for p in path_rects):
                    continue

                x = float(hard_rect["x"])
                y = float(hard_rect["y"])
                l = float(hard_rect["length"])
                w = float(hard_rect["width"])

                spine = circulation.get("primary_spine") if circulation else None
                spine_cx = None
                if spine and all(k in spine for k in ("x", "length")):
                    spine_cx = float(spine["x"]) + float(spine["length"]) / 2.0

                # Default F7.1 orientation keeps the front on the top horizontal side.
                # For frontage strips D3/D4/D9/D10/D11/D12, rotate the mannequin 180°
                # so the frontage-facing condition is inverted and the FRONT faces down.
                # D1/D2 override near the primary spine: the FRONT (open side)
                # must face the spine, so left-of-spine hosts open to the right
                # and right-of-spine hosts open to the left.
                orientation = "front_down" if dkey in {"D3", "D4", "D9", "D10", "D11", "D12"} else "front_up"
                if dkey in {"D1", "D2"} and spine is not None and spine_cx is not None:
                    spine_left = float(spine["x"])
                    spine_right = float(spine["x"]) + float(spine["length"])
                    host_left = float(host["x"])
                    host_right = float(host["x"]) + float(host.get("length", 0.0))
                    gap_to_spine = min(abs(host_right - spine_left), abs(host_left - spine_right))
                    if dkey == "D2" or gap_to_spine <= 1.20 + 1e-6:
                        cx = x + l / 2.0
                        if dkey == "D1" and spine_side_index is not None and pos_idx != spine_side_index:
                            orientation = _orientation_from_aisle_priority(hard_rect, host, prefer_side_secondary=True)
                        else:
                            orientation = "front_right" if cx < spine_cx else "front_left"
                elif dkey == "D1":
                    orientation = _orientation_from_aisle_priority(hard_rect, host, prefer_side_secondary=True)

                # Back edge of both soft envelopes is attached to the hard footprint,
                # so there is no rear extension behind F7.1.

                mannequin_fixtures.append(
                    _rect_obj(
                        hard_rect,
                        "display_mannequin",
                        family="F7.1",
                        module_index=module_index,
                        graphic_class="mannequin",
                        lineweight="heavy",
                    )
                )

                if orientation == "front_up":
                    # Back side attached to the hard footprint top edge; envelope extends laterally and forward only.
                    mannequin_buffers.append(_line_obj(x - min_soft_depth, y, x - min_soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x + l + min_soft_depth, y, x + l + min_soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x, y, x + l, y,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - min_soft_depth, y + w + soft_depth, x + l + min_soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y, x - soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x + l + soft_depth, y, x + l + soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x, y, x + l, y,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y + w + soft_depth, x + l + soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
                elif orientation == "front_down":
                    # 180° rotation of frontage F7.1: back side attached to the hard footprint bottom edge;
                    # envelope extends laterally and upward only, with the FRONT on the bottom side.
                    mannequin_buffers.append(_line_obj(x - min_soft_depth, y - soft_depth, x - min_soft_depth, y + w,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x + l + min_soft_depth, y - soft_depth, x + l + min_soft_depth, y + w,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - min_soft_depth, y - soft_depth, x + l + min_soft_depth, y - soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
                    mannequin_buffers.append(_line_obj(x, y + w, x + l, y + w,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y - soft_depth, x - soft_depth, y + w,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x + l + soft_depth, y - soft_depth, x + l + soft_depth, y + w,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y - soft_depth, x + l + soft_depth, y - soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
                    mannequin_buffers.append(_line_obj(x, y + w, x + l, y + w,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                elif orientation == "front_right":
                    # Back side attached to hard left edge; envelope extends up/down and toward the front only.
                    mannequin_buffers.append(_line_obj(x, y - min_soft_depth, x, y + w + min_soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x, y - min_soft_depth, x + l + soft_depth, y - min_soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x, y + w + min_soft_depth, x + l + soft_depth, y + w + min_soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x + l + soft_depth, y - min_soft_depth, x + l + soft_depth, y + w + min_soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
                    mannequin_buffers.append(_line_obj(x, y - soft_depth, x, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x, y - soft_depth, x + l + soft_depth, y - soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x, y + w + soft_depth, x + l + soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x + l + soft_depth, y - soft_depth, x + l + soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
                else:  # front_left
                    # Back side attached to hard right edge; envelope extends up/down and toward the front only.
                    mannequin_buffers.append(_line_obj(x + l, y - min_soft_depth, x + l, y + w + min_soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y - min_soft_depth, x + l, y - min_soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y + w + min_soft_depth, x + l, y + w + min_soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y - min_soft_depth, x - soft_depth, y + w + min_soft_depth,
                        "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
                    mannequin_buffers.append(_line_obj(x + l, y - soft_depth, x + l, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y - soft_depth, x + l, y - soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y + w + soft_depth, x + l, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
                    mannequin_buffers.append(_line_obj(x - soft_depth, y - soft_depth, x - soft_depth, y + w + soft_depth,
                        "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))

                existing_hard.append(hard_rect)
                module_index += 1

    return mannequin_fixtures, mannequin_buffers




def _generate_d2_mix_modules(
    display_classes: dict | None,
    display_wall: list[dict] | None,
    display_gondola: list[dict] | None,
    circulation: dict | None = None,
) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict]]:
    """Generate D2 mixed composition using D1 gondola-style column packing.

    No F7/F8 are generated in D1. Inside each D2 host, columns are packed like the
    D1 field: the spine-side column becomes F7; remaining columns become F8 where
    size permits, with F7 fallback when F8 cannot fit.
    """
    if not display_classes:
        return [], [], [], [], [], []

    f7_size = 0.60
    f7_min = 0.60
    f7_soft = 1.20
    f7_clear = 0.60
    f8_l = 1.20
    f8_w = 1.00
    f8_min = 0.60
    f8_outer = 1.20

    mannequin_fixtures: list[dict] = []
    mannequin_buffers: list[dict] = []
    display_table: list[dict] = []
    display_table_buffer_min: list[dict] = []
    display_table_buffer: list[dict] = []
    labels: list[dict] = []

    existing_hard = _collect_hard_fixture_rects(display_wall) + _collect_hard_fixture_rects(display_gondola)

    path_rects: list[dict] = []
    if circulation:
        for key in ["primary_spine", "service_connector"]:
            r = circulation.get(key)
            if r and all(k in r for k in ("x", "y", "length", "width")):
                path_rects.append(r)
        for key in ["secondary_aisles", "side_secondary_aisles", "territorial_aisles", "territorial_secondary_aisles"]:
            for r in circulation.get(key, []) or []:
                if all(k in r for k in ("x", "y", "length", "width")):
                    path_rects.append(r)

    spine = circulation.get("primary_spine") if circulation else None
    spine_cx = None
    if spine and all(k in spine for k in ("x", "length")):
        spine_cx = float(spine["x"]) + float(spine["length"]) / 2.0

    def add_f7(hard_rect: dict, orientation: str, module_index: int):
        x = float(hard_rect["x"]); y = float(hard_rect["y"]); l = f7_size; w = f7_size
        mannequin_fixtures.append(_rect_obj(hard_rect, "display_mannequin", family="F7.1", module_index=module_index, graphic_class="mannequin", lineweight="heavy"))
        labels.append(_text_obj(x + l/2.0, y + w/2.0, "F7", role="fixture_label", text_size="small"))
        if orientation == "front_right":
            mannequin_buffers.append(_line_obj(x, y - f7_min, x, y + w + f7_min, "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x, y - f7_min, x + l + f7_soft, y - f7_min, "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x, y + w + f7_min, x + l + f7_soft, y + w + f7_min, "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x + l + f7_soft, y - f7_min, x + l + f7_soft, y + w + f7_min, "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
            mannequin_buffers.append(_line_obj(x, y - f7_soft, x, y + w + f7_soft, "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x, y - f7_soft, x + l + f7_soft, y - f7_soft, "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x, y + w + f7_soft, x + l + f7_soft, y + w + f7_soft, "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x + l + f7_soft, y - f7_soft, x + l + f7_soft, y + w + f7_soft, "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
        else:
            mannequin_buffers.append(_line_obj(x + l, y - f7_min, x + l, y + w + f7_min, "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x - f7_soft, y - f7_min, x + l, y - f7_min, "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x - f7_soft, y + w + f7_min, x + l, y + w + f7_min, "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x - f7_soft, y - f7_min, x - f7_soft, y + w + f7_min, "display_mannequin_buffer_min", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))
            mannequin_buffers.append(_line_obj(x + l, y - f7_soft, x + l, y + w + f7_soft, "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x - f7_soft, y - f7_soft, x + l, y - f7_soft, "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x - f7_soft, y + w + f7_soft, x + l, y + w + f7_soft, "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="medium"))
            mannequin_buffers.append(_line_obj(x - f7_soft, y - f7_soft, x - f7_soft, y + w + f7_soft, "display_mannequin_buffer", family="F7.1", module_index=module_index, dash=True, lineweight="heavy"))

    module_index = 1
    for item in display_classes.get("D2", []):
        host = item.get("rect", {})
        if not host:
            continue
        hx = float(host.get("x", 0.0)); hy = float(host.get("y", 0.0))
        hl = float(host.get("length", 0.0)); hw = float(host.get("width", 0.0))
        if hl < f7_size or hw < f7_size:
            continue

        max_count = max(1, int((hl + f7_clear) // (f7_size + f7_clear)))
        count = 1
        for c in range(max_count, 0, -1):
            used = c * f7_size + max(0, c - 1) * f7_clear
            if used <= hl + 1e-6:
                count = c
                break
        used = count * f7_size + max(0, count - 1) * f7_clear
        start_x = hx + (hl - used) / 2.0
        row_positions = [round(start_x + i * (f7_size + f7_clear), 6) for i in range(count)]

        host_cx = hx + hl / 2.0
        spine_on_right = True if spine_cx is None else (host_cx < spine_cx)
        spine_side_index = len(row_positions) - 1 if spine_on_right else 0

        for pos_idx, px in enumerate(row_positions):
            if pos_idx == spine_side_index:
                f7_rect = {"x": px, "y": hy + (hw - f7_size) / 2.0, "length": f7_size, "width": f7_size}
                orientation = "front_right" if spine_on_right else "front_left"
                if any(_rects_overlap(f7_rect, r) for r in existing_hard):
                    continue
                if any(_rects_overlap(f7_rect, p) for p in path_rects):
                    continue
                add_f7(f7_rect, orientation, module_index)
                existing_hard.append(dict(f7_rect))
                module_index += 1
            else:
                # F8 uses the same column centerline as the D1 gondola-style field; fallback to F7 if width is tight.
                f8_rect = {"x": px - (f8_l - f7_size) / 2.0, "y": hy + (hw - f8_w) / 2.0, "length": f8_l, "width": f8_w}
                fits_host = (f8_rect["x"] >= hx - 1e-6 and f8_rect["x"] + f8_rect["length"] <= hx + hl + 1e-6 and
                             f8_rect["y"] >= hy - 1e-6 and f8_rect["y"] + f8_rect["width"] <= hy + hw + 1e-6)
                if fits_host and not any(_rects_overlap(f8_rect, r) for r in existing_hard) and not any(_rects_overlap(f8_rect, p) for p in path_rects):
                    min_rect = {"x": f8_rect["x"] - f8_min, "y": f8_rect["y"] - f8_min, "length": f8_rect["length"] + 2.0 * f8_min, "width": f8_rect["width"] + 2.0 * f8_min}
                    outer_rect = {"x": f8_rect["x"] - f8_outer, "y": f8_rect["y"] - f8_outer, "length": f8_rect["length"] + 2.0 * f8_outer, "width": f8_rect["width"] + 2.0 * f8_outer}
                    display_table.append(_rect_obj(f8_rect, "display_table", family="F8", module_index=module_index, graphic_class="table", lineweight="heavy"))
                    display_table_buffer_min.append(_rect_obj(min_rect, "display_table_buffer_min", family="F8", module_index=module_index, dash=True, lineweight="light"))
                    display_table_buffer.append(_rect_obj(outer_rect, "display_table_buffer", family="F8", module_index=module_index, dash=True, lineweight="medium"))
                    labels.append(_text_obj(float(f8_rect["x"]) + float(f8_rect["length"])/2.0, float(f8_rect["y"]) + float(f8_rect["width"])/2.0, "F8", role="fixture_label", text_size="small"))
                    existing_hard.append(dict(f8_rect))
                    module_index += 1
                else:
                    f7_rect = {"x": px, "y": hy + (hw - f7_size) / 2.0, "length": f7_size, "width": f7_size}
                    # fallback F7 faces away from the spine-side column, mirroring the side field
                    orientation = "front_left" if spine_on_right else "front_right"
                    if any(_rects_overlap(f7_rect, r) for r in existing_hard):
                        continue
                    if any(_rects_overlap(f7_rect, p) for p in path_rects):
                        continue
                    add_f7(f7_rect, orientation, module_index)
                    existing_hard.append(dict(f7_rect))
                    module_index += 1

    return mannequin_fixtures, mannequin_buffers, display_table, display_table_buffer_min, display_table_buffer, labels



def _generate_f8_modules(
    display_classes: dict | None,
    display_wall: list[dict] | None,
    display_gondola: list[dict] | None,
    display_mannequin: list[dict] | None,
    circulation: dict | None = None,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    if not display_classes:
        return [], [], [], []

    hard_l = 1.20
    hard_w = 1.00
    d4_hard_w = 0.60
    min_buf = 0.60
    outer_buf = 1.20
    clear_spacing = 0.90
    allowed_keys = ["D4", "D9", "D10"]
    frontage_glass_offset_keys = {"D4", "D9", "D10"}
    glass_offset = 0.20

    display_table: list[dict] = []
    display_table_buffer_min: list[dict] = []
    display_table_buffer: list[dict] = []
    labels: list[dict] = []

    existing_hard = []
    existing_hard += _collect_hard_fixture_rects(display_wall)
    existing_hard += _collect_hard_fixture_rects(display_gondola)
    existing_hard += _collect_hard_fixture_rects(display_mannequin)

    path_rects: list[dict] = []
    if circulation:
        for key in ["primary_spine", "service_connector"]:
            r = circulation.get(key)
            if r and all(k in r for k in ("x", "y", "length", "width")):
                path_rects.append(r)
        for key in ["secondary_aisles", "side_secondary_aisles", "territorial_aisles", "territorial_secondary_aisles"]:
            for r in circulation.get(key, []) or []:
                if all(k in r for k in ("x", "y", "length", "width")):
                    path_rects.append(r)

    module_index = 1

    for dkey in allowed_keys:
        for item in display_classes.get(dkey, []):
            host = item.get("rect", {})
            if not host:
                continue

            hx = float(host.get("x", 0.0))
            hy = float(host.get("y", 0.0))
            hl = float(host.get("length", 0.0))
            hw = float(host.get("width", 0.0))
            if hl <= 0.0 or hw <= 0.0:
                continue

            if dkey == "D4":
                tab_l, tab_w = hard_l, d4_hard_w
                repeat_axis = "x"
                module_span = tab_l
                host_span = hl
            elif hl >= hw:
                tab_l, tab_w = hard_l, hard_w
                repeat_axis = "x"
                module_span = tab_l
                host_span = hl
            else:
                tab_l, tab_w = hard_w, hard_l
                repeat_axis = "y"
                module_span = tab_w
                host_span = hw

            if hl + 1e-6 < tab_l or hw + 1e-6 < tab_w:
                continue

            local_clear_spacing = 0.60 if dkey == "D1" else clear_spacing
            step = module_span + local_clear_spacing
            count = max(1, int((host_span + local_clear_spacing) // step))
            used_span = count * module_span + max(0, count - 1) * local_clear_spacing

            candidates = []
            if repeat_axis == "x":
                start_x = hx + (hl - used_span) / 2.0
                if dkey in frontage_glass_offset_keys:
                    fixed_y = hy + glass_offset
                else:
                    fixed_y = hy + (hw - tab_w) / 2.0
                if fixed_y + tab_w > hy + hw + 1e-6:
                    continue
                for i in range(count):
                    candidates.append({
                        "x": round(start_x + i * step, 6),
                        "y": round(fixed_y, 6),
                        "length": tab_l,
                        "width": tab_w,
                    })
            else:
                fixed_x = hx + (hl - tab_l) / 2.0
                if dkey in frontage_glass_offset_keys:
                    start_y = hy + glass_offset
                else:
                    start_y = hy + (hw - used_span) / 2.0
                if start_y + used_span > hy + hw + 1e-6:
                    continue
                for i in range(count):
                    candidates.append({
                        "x": round(fixed_x, 6),
                        "y": round(start_y + i * step, 6),
                        "length": tab_l,
                        "width": tab_w,
                    })

            for hard_rect in candidates:
                # D4 behaves as a dedicated frontage strip: host one horizontal row using
                # D1-style row logic. To keep that row visible and stable, D4 bypasses the
                # generic overlap rejection used for island/table fields. Other hosts retain
                # the standard hard/buffer conflict checks.
                if dkey != "D4":
                    if any(_rects_overlap(hard_rect, r) for r in existing_hard):
                        continue
                    if any(_rects_overlap(hard_rect, p) for p in path_rects):
                        continue

                min_rect = {
                    "x": hard_rect["x"] - min_buf,
                    "y": hard_rect["y"] - min_buf,
                    "length": hard_rect["length"] + 2.0 * min_buf,
                    "width": hard_rect["width"] + 2.0 * min_buf,
                }
                outer_rect = {
                    "x": hard_rect["x"] - outer_buf,
                    "y": hard_rect["y"] - outer_buf,
                    "length": hard_rect["length"] + 2.0 * outer_buf,
                    "width": hard_rect["width"] + 2.0 * outer_buf,
                }

                if dkey != "D4":
                    if any(_rects_overlap(min_rect, r) for r in existing_hard):
                        continue
                    if any(_rects_overlap(outer_rect, r) for r in existing_hard):
                        continue

                display_table.append(
                    _rect_obj(
                        hard_rect,
                        "display_table",
                        family="F8",
                        module_index=module_index,
                        graphic_class="table",
                        lineweight="heavy",
                    )
                )
                display_table_buffer_min.append(
                    _rect_obj(
                        min_rect,
                        "display_table_buffer_min",
                        family="F8",
                        module_index=module_index,
                        dash=True,
                        lineweight="light",
                    )
                )
                display_table_buffer.append(
                    _rect_obj(
                        outer_rect,
                        "display_table_buffer",
                        family="F8",
                        module_index=module_index,
                        dash=True,
                        lineweight="medium",
                    )
                )
                lx, ly = _center(hard_rect)
                labels.append(_text_obj(lx, ly, "F8", role="fixture_label", text_size="small"))
                existing_hard.append(dict(hard_rect))
                module_index += 1

    return display_table, display_table_buffer_min, display_table_buffer, labels


def _generate_d1_modules(display_classes: dict | None, circulation: dict | None) -> tuple[list[dict], list[dict]]:
    if not display_classes:
        return [], []
    spine = circulation.get('primary_spine') if circulation else None
    fixtures: list[dict] = []
    buffers: list[dict] = []
    module_idx = 1

    F4_L, F4_W, F4_BUF = 1.20, 1.04, 1.20
    F5_L, F5_W, F5_BUF = 1.00, 0.60, 1.20
    F6_L, F6_W, F6_BUF = 1.20, 1.20, 1.20
    # D1 internal aisle must protect soft-buffer to hard-footprint conflicts between F4/F5/F6.
    AISLE = 1.20

    # Circulation-facing refinement for D1:
    # F5 is a single-sided browsing rack, so its soft/browsing buffer should face
    # the nearest circulation edge rather than an arbitrary packing side. F4/F6
    # remain two-sided systems, but F5 gets re-oriented after the baseline rack
    # field is generated. This preserves the baseline model and only improves
    # fixture-facing logic inside D1.
    path_rects: list[dict] = []
    if circulation:
        for key in ["primary_spine", "service_connector"]:
            r = circulation.get(key)
            if r and all(k in r for k in ("x", "y", "length", "width")):
                path_rects.append(r)
        for key in ["secondary_aisles", "side_secondary_aisles", "territorial_aisles", "territorial_secondary_aisles"]:
            for r in circulation.get(key, []) or []:
                if r and all(k in r for k in ("x", "y", "length", "width")):
                    path_rects.append(r)

    def _axis_overlap(a0: float, a1: float, b0: float, b1: float) -> float:
        return max(0.0, min(a1, b1) - max(a0, b0))

    def _nearest_circulation_side(rect: dict, allowed_sides: list[str] | None = None) -> str | None:
        """Return the side of a hard fixture that should face circulation.

        The selected side is the nearest aisle/path edge with a meaningful overlap
        along the perpendicular axis. This lets F5 buffers point toward the actual
        customer approach side inside D1. If no path is detected, the previous
        baseline side is kept by the caller.
        """
        if not path_rects:
            return None
        allowed = set(allowed_sides or ["left", "right", "bottom", "top"])
        x0 = float(rect["x"]); y0 = float(rect["y"])
        x1 = x0 + float(rect["length"]); y1 = y0 + float(rect["width"])
        candidates: list[tuple[float, int, str]] = []
        for pr in path_rects:
            px0 = float(pr["x"]); py0 = float(pr["y"])
            px1 = px0 + float(pr["length"]); py1 = py0 + float(pr["width"])
            v_olap = _axis_overlap(y0, y1, py0, py1)
            h_olap = _axis_overlap(x0, x1, px0, px1)
            # Prefer paths that overlap the fixture span; still allow a weak
            # candidate when the path is very close because D1 modules may be
            # slightly offset from aisles by buffers.
            if "left" in allowed and px1 <= x0 + 1e-6:
                dist = x0 - px1
                if v_olap > 1e-6 or dist <= AISLE + 1e-6:
                    candidates.append((dist, 0 if v_olap > 1e-6 else 1, "left"))
            if "right" in allowed and px0 >= x1 - 1e-6:
                dist = px0 - x1
                if v_olap > 1e-6 or dist <= AISLE + 1e-6:
                    candidates.append((dist, 0 if v_olap > 1e-6 else 1, "right"))
            if "bottom" in allowed and py1 <= y0 + 1e-6:
                dist = y0 - py1
                if h_olap > 1e-6 or dist <= AISLE + 1e-6:
                    candidates.append((dist, 0 if h_olap > 1e-6 else 1, "bottom"))
            if "top" in allowed and py0 >= y1 - 1e-6:
                dist = py0 - y1
                if h_olap > 1e-6 or dist <= AISLE + 1e-6:
                    candidates.append((dist, 0 if h_olap > 1e-6 else 1, "top"))
        if not candidates:
            return None
        candidates.sort(key=lambda t: (t[0], t[1]))
        return candidates[0][2]

    def _f5_side_facing_circulation(rect: dict, fallback: str, orientation: str) -> list[str]:
        # F5 is single-sided: vertical F5 rows browse from left/right; horizontal
        # F5 rows browse from bottom/top. Keeping this axis prevents accidental
        # 90-degree reinterpretation while still facing the nearest circulation.
        allowed = ["left", "right"] if orientation == "vertical" else ["bottom", "top"]
        side = _nearest_circulation_side(rect, allowed) or fallback
        return [side]

    def add_rect(fam: str, rect: dict, buffer_sides: list[str]):
        nonlocal module_idx
        fixtures.append(_rect_obj(rect, 'display_gondola', family=fam, module_index=module_idx, graphic_class=('gondola' if fam=='F4' else 'rack'), lineweight='heavy'))
        if buffer_sides:
            x = float(rect['x']); y = float(rect['y']); l = float(rect['length']); w = float(rect['width'])
            for s in buffer_sides:
                if s == 'left':
                    br = {'x': x - F4_BUF if fam=='F4' else x - (F5_BUF if fam=='F5' else F6_BUF), 'y': y, 'length': F4_BUF if fam=='F4' else (F5_BUF if fam=='F5' else F6_BUF), 'width': w}
                elif s == 'right':
                    buf = F4_BUF if fam=='F4' else (F5_BUF if fam=='F5' else F6_BUF)
                    br = {'x': x + l, 'y': y, 'length': buf, 'width': w}
                elif s == 'bottom':
                    buf = F4_BUF if fam=='F4' else (F5_BUF if fam=='F5' else F6_BUF)
                    br = {'x': x, 'y': y - buf, 'length': l, 'width': buf}
                else:
                    buf = F4_BUF if fam=='F4' else (F5_BUF if fam=='F5' else F6_BUF)
                    br = {'x': x, 'y': y + w, 'length': l, 'width': buf}
                buffers.append(_rect_obj(br, 'display_gondola_buffer', family=fam, module_index=module_idx, graphic_class='gondola_buffer', dash=True, lineweight='light'))
        module_idx += 1

    for item in display_classes.get('D1', []):
        d1 = item.get('rect', {})
        if not d1:
            continue

        # Build each D1 arrangement locally, then center the whole display area
        # (hard fixtures + soft buffers) in both X and Y inside the D1 container.
        local_fixtures: list[dict] = []
        local_buffers: list[dict] = []

        def add_local_rect(fam: str, rect: dict, buffer_sides: list[str]):
            nonlocal module_idx
            fixture = _rect_obj(rect, 'display_gondola', family=fam, module_index=module_idx, graphic_class=('gondola' if fam=='F4' else 'rack'), lineweight='heavy')
            local_fixtures.append(fixture)
            if buffer_sides:
                x = float(rect['x']); y = float(rect['y']); l = float(rect['length']); w = float(rect['width'])
                for s in buffer_sides:
                    if s == 'left':
                        br = {'x': x - F4_BUF if fam=='F4' else x - (F5_BUF if fam=='F5' else F6_BUF), 'y': y, 'length': F4_BUF if fam=='F4' else (F5_BUF if fam=='F5' else F6_BUF), 'width': w}
                    elif s == 'right':
                        buf = F4_BUF if fam=='F4' else (F5_BUF if fam=='F5' else F6_BUF)
                        br = {'x': x + l, 'y': y, 'length': buf, 'width': w}
                    elif s == 'bottom':
                        buf = F4_BUF if fam=='F4' else (F5_BUF if fam=='F5' else F6_BUF)
                        br = {'x': x, 'y': y - buf, 'length': l, 'width': buf}
                    else:
                        buf = F4_BUF if fam=='F4' else (F5_BUF if fam=='F5' else F6_BUF)
                        br = {'x': x, 'y': y + w, 'length': l, 'width': buf}
                    local_buffers.append(_rect_obj(br, 'display_gondola_buffer', family=fam, module_index=module_idx, graphic_class='gondola_buffer', dash=True, lineweight='light'))
            module_idx += 1

        # Locked D1 rule: evaluate against the vertical main spine using left/right only,
        # so the same spine-side/opposite-side behavior survives store width changes and
        # left/center/right entrance cases.
        side = _d1_vertical_spine_side(d1, spine)
        touches_spine = _d1_touches_vertical_spine(d1, spine)
        band = _rect_from_side_band(d1, side, F4_W) if touches_spine else None
        residual = _subtract_band(d1, side, F4_W + F4_BUF) if touches_spine else dict(d1)

        if band:
            vertical = side in {'left', 'right'}
            run = float(band['width'] if vertical else band['length'])
            mod_len = F4_L
            count = int(run // mod_len)
            if count >= 1:
                leftover = run - count * mod_len
                offset = leftover / 2.0
                for i in range(count):
                    if vertical:
                        rr = {'x': float(band['x']), 'y': float(band['y']) + offset + i * mod_len, 'length': F4_W, 'width': F4_L}
                        add_local_rect('F4', rr, ['left', 'right'])
                    else:
                        rr = {'x': float(band['x']) + offset + i * mod_len, 'y': float(band['y']), 'length': F4_L, 'width': F4_W}
                        add_local_rect('F4', rr, ['bottom', 'top'])

        if residual:
            orient_vertical = float(residual['width']) >= float(residual['length'])
            if orient_vertical:
                row_run = float(residual['width'])
                cross = float(residual['length'])

                row_specs: list[tuple[str, float]] = []
                remaining_cross = cross
                while remaining_cross + 1e-6 >= F5_W:
                    fam = 'F6' if remaining_cross + 1e-6 >= F6_W else 'F5'
                    row_w = F6_W if fam == 'F6' else F5_W
                    row_specs.append((fam, row_w))
                    remaining_cross -= row_w
                    if remaining_cross + 1e-6 >= AISLE + F5_W:
                        remaining_cross -= AISLE
                    else:
                        break

                if touches_spine:
                    # Keep the rack field tied to the side opposite the spine.
                    if side == 'left':
                        cursor_x = float(residual['x']) + float(residual['length'])
                        step_sign = -1.0
                    else:
                        cursor_x = float(residual['x'])
                        step_sign = 1.0

                    for fam, row_width in row_specs:
                        if step_sign < 0:
                            rx = cursor_x - row_width
                            cursor_x = rx
                        else:
                            rx = cursor_x
                        mod_len = F6_L if fam == 'F6' else F5_L
                        count = int(row_run // mod_len)
                        if count > 0:
                            leftover = row_run - count * mod_len
                            y0 = float(residual['y']) + leftover / 2.0
                            for i in range(count):
                                rr = {'x': rx, 'y': y0 + i * mod_len, 'length': row_width, 'width': mod_len}
                                if fam == 'F6':
                                    add_local_rect('F6', rr, ['left', 'right'])
                                else:
                                    add_local_rect('F5', rr, _f5_side_facing_circulation(rr, 'left' if side == 'left' else 'right', 'vertical'))
                        if step_sign < 0:
                            cursor_x -= AISLE
                        else:
                            cursor_x += row_width + AISLE
                else:
                    # Non-spine D1 must behave as a coherent centered host field,
                    # not as a thin residual strip tied to one side.
                    total_used = sum(w for _, w in row_specs) + max(0, len(row_specs)-1) * AISLE
                    start_x = float(residual['x']) + max(0.0, (cross - total_used) / 2.0)
                    cursor_x = start_x
                    field_cx = float(residual['x']) + float(residual['length']) / 2.0
                    for fam, row_width in row_specs:
                        mod_len = F6_L if fam == 'F6' else F5_L
                        count = int(row_run // mod_len)
                        if count > 0:
                            leftover = row_run - count * mod_len
                            y0 = float(residual['y']) + leftover / 2.0
                            for i in range(count):
                                rr = {'x': cursor_x, 'y': y0 + i * mod_len, 'length': row_width, 'width': mod_len}
                                if fam == 'F6':
                                    add_local_rect('F6', rr, ['left', 'right'])
                                else:
                                    # Keep F5 repetition on the same F5 side instead of mirroring
                                    # across the field center. Anchor the repeated F5 rows to the
                                    # side of the first F5 row and let subsequent F5 rows repeat on
                                    # that same side.
                                    add_local_rect('F5', rr, _f5_side_facing_circulation(rr, 'right', 'vertical'))
                        cursor_x += row_width + AISLE
            else:
                row_run = float(residual['length'])
                cross = float(residual['width'])
                row_specs: list[tuple[str, float]] = []
                remaining_cross = cross
                while remaining_cross + 1e-6 >= F5_W:
                    fam = 'F6' if remaining_cross + 1e-6 >= F6_W else 'F5'
                    row_w = F6_W if fam == 'F6' else F5_W
                    row_specs.append((fam, row_w))
                    remaining_cross -= row_w
                    if remaining_cross + 1e-6 >= AISLE + F5_W:
                        remaining_cross -= AISLE
                    else:
                        break
                if touches_spine:
                    total_used = sum(w for _, w in row_specs) + max(0, len(row_specs)-1) * AISLE
                    y0 = float(residual['y']) + max(0.0, (cross - total_used) / 2.0)
                    for fam, row_width in row_specs:
                        mod_len = F6_L if fam == 'F6' else F5_L
                        count = int(row_run // mod_len)
                        if count == 0:
                            y0 += row_width + AISLE
                            continue
                        used = count * mod_len
                        if side == 'left':
                            x0 = float(residual['x']) + float(residual['length']) - used
                        else:
                            x0 = float(residual['x'])
                        for i in range(count):
                            rr = {'x': x0 + i * mod_len, 'y': y0, 'length': mod_len, 'width': row_width}
                            if fam == 'F6':
                                add_local_rect('F6', rr, ['bottom', 'top'])
                            else:
                                add_local_rect('F5', rr, _f5_side_facing_circulation(rr, 'top' if side == 'right' else 'bottom', 'horizontal'))
                        y0 += row_width + AISLE
                else:
                    total_used = sum(w for _, w in row_specs) + max(0, len(row_specs)-1) * AISLE
                    y0 = float(residual['y']) + max(0.0, (cross - total_used) / 2.0)
                    field_cy = float(residual['y']) + float(residual['width']) / 2.0
                    for fam, row_width in row_specs:
                        mod_len = F6_L if fam == 'F6' else F5_L
                        count = int(row_run // mod_len)
                        if count == 0:
                            y0 += row_width + AISLE
                            continue
                        used = count * mod_len
                        x0 = float(residual['x']) + max(0.0, (float(residual['length']) - used) / 2.0)
                        for i in range(count):
                            rr = {'x': x0 + i * mod_len, 'y': y0, 'length': mod_len, 'width': row_width}
                            if fam == 'F6':
                                add_local_rect('F6', rr, ['bottom', 'top'])
                            else:
                                # Keep F5 repetition on the same F5 side instead of mirroring
                                # across the field center. Anchor the repeated F5 rows to the
                                # side of the first F5 row and let subsequent F5 rows repeat on
                                # that same side.
                                add_local_rect('F5', rr, _f5_side_facing_circulation(rr, 'top', 'horizontal'))
                        y0 += row_width + AISLE

        # If the D1 arrangement resolves to a single column/strip of fixtures
        # (for example one vertical stack of F4, F5, or F6), center the hard
        # fixture composition in both X and Y inside D1. Buffers follow the hard
        # geometry and must not drive the centering.
        if local_fixtures:
            xs = sorted({round(float(f["x"]), 6) for f in local_fixtures})
            ys = sorted({round(float(f["y"]), 6) for f in local_fixtures})
            single_column = len(xs) == 1 or len(ys) == 1
            if single_column:
                minx = min(float(f['x']) for f in local_fixtures)
                miny = min(float(f['y']) for f in local_fixtures)
                maxx = max(float(f['x']) + float(f['length']) for f in local_fixtures)
                maxy = max(float(f['y']) + float(f['width']) for f in local_fixtures)
                hard_cx = (minx + maxx) / 2.0
                hard_cy = (miny + maxy) / 2.0
                d1_cx = float(d1['x']) + float(d1['length']) / 2.0
                d1_cy = float(d1['y']) + float(d1['width']) / 2.0
                dx = d1_cx - hard_cx
                dy = d1_cy - hard_cy
                for coll in (local_fixtures, local_buffers):
                    for obj in coll:
                        obj['x'] = round(float(obj['x']) + dx, 6)
                        obj['y'] = round(float(obj['y']) + dy, 6)

        fixtures.extend(local_fixtures)
        buffers.extend(local_buffers)

    return fixtures, buffers


def _d1_post_t_max_availability_recovery(
    display_classes: dict | None,
    circulation: dict | None,
    display_gondola: list[dict],
    display_gondola_buffer: list[dict],
    display_wall: list[dict] | None = None,
    display_wall_buffer: list[dict] | None = None,
    display_mannequin: list[dict] | None = None,
    display_mannequin_buffer: list[dict] | None = None,
    display_table: list[dict] | None = None,
    display_table_buffer_min: list[dict] | None = None,
    display_table_buffer: list[dict] | None = None,
    interactive_hard: list[dict] | None = None,
    interactive_min: list[dict] | None = None,
    interactive_soft: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Post-interactive D1 density recovery without changing the baseline model.

    Baseline F-family generation stays untouched. After T-family insertion has removed
    conflicting F-modules, this pass only fills remaining D1 gaps with compact F6/F5
    modules. It respects the thesis buffer hierarchy:
    - every new F hard footprint must stay inside D1;
    - no hard footprint may overlap any existing hard footprint;
    - no hard footprint may enter any existing F/T buffer;
    - new F buffers may share circulation/soft buffer space, but may not cross an
      existing hard footprint or T minimum buffer;
    - F5 single-sided buffer faces the nearest circulation side.
    """
    if not display_classes:
        return display_gondola, display_gondola_buffer

    F5_L, F5_W, F5_BUF = 1.00, 0.60, 1.20
    F6_L, F6_W, F6_BUF = 1.20, 1.20, 1.20
    GRID = 0.10
    EPS = 1e-6

    def _is_rect(o: dict | None) -> bool:
        return isinstance(o, dict) and o.get("shape") == "rect" and all(k in o for k in ("x", "y", "length", "width"))

    def _host_contains(host: dict, r: dict, tol: float = 1e-6) -> bool:
        return (
            float(r["x"]) + tol >= float(host["x"]) and
            float(r["y"]) + tol >= float(host["y"]) and
            float(r["x"]) + float(r["length"]) <= float(host["x"]) + float(host["length"]) + tol and
            float(r["y"]) + float(r["width"]) <= float(host["y"]) + float(host["width"]) + tol
        )

    def _rect_key(o: dict) -> tuple[str, int]:
        return (str(o.get("family", "")), int(o.get("module_index", -1)) if o.get("module_index") is not None else -1)

    def _axis_overlap(a0: float, a1: float, b0: float, b1: float) -> float:
        return max(0.0, min(a1, b1) - max(a0, b0))

    path_rects: list[dict] = []
    if circulation:
        for key in ["primary_spine", "service_connector"]:
            r = circulation.get(key)
            if r and all(k in r for k in ("x", "y", "length", "width")):
                path_rects.append(r)
        for key in ["secondary_aisles", "side_secondary_aisles", "territorial_aisles", "territorial_secondary_aisles"]:
            for r in circulation.get(key, []) or []:
                if r and all(k in r for k in ("x", "y", "length", "width")):
                    path_rects.append(r)

    def _nearest_circulation_side(rect: dict, allowed_sides: list[str] | None = None) -> str:
        allowed = set(allowed_sides or ["left", "right", "bottom", "top"])
        x0 = float(rect["x"]); y0 = float(rect["y"])
        x1 = x0 + float(rect["length"]); y1 = y0 + float(rect["width"])
        candidates: list[tuple[float, int, str]] = []
        for pr in path_rects:
            px0 = float(pr["x"]); py0 = float(pr["y"])
            px1 = px0 + float(pr["length"]); py1 = py0 + float(pr["width"])
            v_olap = _axis_overlap(y0, y1, py0, py1)
            h_olap = _axis_overlap(x0, x1, px0, px1)
            if "left" in allowed and px1 <= x0 + EPS:
                candidates.append((x0 - px1, 0 if v_olap > EPS else 1, "left"))
            if "right" in allowed and px0 >= x1 - EPS:
                candidates.append((px0 - x1, 0 if v_olap > EPS else 1, "right"))
            if "bottom" in allowed and py1 <= y0 + EPS:
                candidates.append((y0 - py1, 0 if h_olap > EPS else 1, "bottom"))
            if "top" in allowed and py0 >= y1 - EPS:
                candidates.append((py0 - y1, 0 if h_olap > EPS else 1, "top"))
        if candidates:
            candidates.sort(key=lambda t: (t[0], t[1]))
            return candidates[0][2]
        return list(allowed)[0]

    def _buffer_rects_for(fam: str, rect: dict, sides: list[str]) -> list[dict]:
        x = float(rect["x"]); y = float(rect["y"]); l = float(rect["length"]); w = float(rect["width"])
        buf = F6_BUF if fam == "F6" else F5_BUF
        out = []
        for s in sides:
            if s == "left":
                out.append({"x": x - buf, "y": y, "length": buf, "width": w})
            elif s == "right":
                out.append({"x": x + l, "y": y, "length": buf, "width": w})
            elif s == "bottom":
                out.append({"x": x, "y": y - buf, "length": l, "width": buf})
            elif s == "top":
                out.append({"x": x, "y": y + w, "length": l, "width": buf})
        return out

    def _hard_rects(seq: list[dict] | None) -> list[dict]:
        return [o for o in (seq or []) if _is_rect(o)]

    existing_hard = []
    for seq in [display_gondola, display_wall, display_mannequin, display_table, interactive_hard]:
        existing_hard.extend(_hard_rects(seq))

    existing_buffers = []
    for seq in [display_gondola_buffer, display_wall_buffer, display_mannequin_buffer, display_table_buffer_min, display_table_buffer, interactive_min, interactive_soft]:
        existing_buffers.extend(_hard_rects(seq))

    # Keep T minimum and T soft buffers as protected zones for new F hard footprints.
    protected_t = _hard_rects(interactive_min) + _hard_rects(interactive_soft)

    next_idx = 1
    for obj in display_gondola + display_gondola_buffer:
        if str(obj.get("family", "")) in {"F4", "F5", "F6"}:
            try:
                next_idx = max(next_idx, int(obj.get("module_index", 0)) + 1)
            except Exception:
                pass

    def _valid_candidate(host: dict, hard: dict, buffers: list[dict]) -> bool:
        if not _host_contains(host, hard):
            return False
        # No new hard over existing hard, existing soft/min buffers, or protected T zones.
        if any(_rects_overlap(hard, r) for r in existing_hard):
            return False
        if any(_rects_overlap(hard, r) for r in existing_buffers):
            return False
        if any(_rects_overlap(hard, r) for r in protected_t):
            return False
        # New soft/browsing buffers may project into circulation, but not through hard modules or T min buffers.
        for br in buffers:
            if any(_rects_overlap(br, r) for r in existing_hard):
                return False
            if any(_rects_overlap(br, r) for r in _hard_rects(interactive_min)):
                return False
        return True

    def _add_module(fam: str, hard: dict, buffer_sides: list[str]) -> None:
        nonlocal next_idx
        fixture = _rect_obj(hard, "display_gondola", family=fam, module_index=next_idx, graphic_class=("rack" if fam in {"F5", "F6"} else "gondola"), lineweight="heavy")
        display_gondola.append(fixture)
        existing_hard.append(fixture)
        for br in _buffer_rects_for(fam, hard, buffer_sides):
            buf_obj = _rect_obj(br, "display_gondola_buffer", family=fam, module_index=next_idx, graphic_class="gondola_buffer", dash=True, lineweight="light")
            display_gondola_buffer.append(buf_obj)
            existing_buffers.append(buf_obj)
        next_idx += 1

    def _candidate_positions(host: dict, l: float, w: float) -> list[tuple[float, float]]:
        hx = float(host["x"]); hy = float(host["y"]); hl = float(host["length"]); hw = float(host["width"])
        if hl + EPS < l or hw + EPS < w:
            return []
        nx = int((hl - l) / GRID) + 1
        ny = int((hw - w) / GRID) + 1
        pts = []
        for iy in range(max(1, ny)):
            for ix in range(max(1, nx)):
                pts.append((round(hx + ix * GRID, 6), round(hy + iy * GRID, 6)))
        # Also test edge-aligned final positions to avoid losing a thin residual gap due to grid rounding.
        pts.append((round(hx + hl - l, 6), round(hy + hw - w, 6)))
        return list(dict.fromkeys(pts))

    for item in display_classes.get("D1", []) or []:
        host = item.get("rect", {}) if isinstance(item, dict) else {}
        if not host:
            continue

        # Pass 1: recover larger two-sided F6 modules where rules allow.
        placed = True
        while placed:
            placed = False
            best = None
            for x, y in _candidate_positions(host, F6_L, F6_W):
                hard = {"x": x, "y": y, "length": F6_L, "width": F6_W}
                near = _nearest_circulation_side(hard)
                sides = ["left", "right"] if near in {"left", "right"} else ["bottom", "top"]
                buffers = _buffer_rects_for("F6", hard, sides)
                if _valid_candidate(host, hard, buffers):
                    best = (hard, sides)
                    break
            if best:
                _add_module("F6", best[0], best[1])
                placed = True

        # Pass 2: fill residual gaps with single-sided F5 facing circulation.
        placed = True
        while placed:
            placed = False
            best = None
            orientations = [(F5_W, F5_L, ["left", "right"]), (F5_L, F5_W, ["bottom", "top"])]
            for l, w, allowed in orientations:
                for x, y in _candidate_positions(host, l, w):
                    hard = {"x": x, "y": y, "length": l, "width": w}
                    side = _nearest_circulation_side(hard, allowed)
                    buffers = _buffer_rects_for("F5", hard, [side])
                    if _valid_candidate(host, hard, buffers):
                        best = (hard, [side])
                        break
                if best:
                    break
            if best:
                _add_module("F5", best[0], best[1])
                placed = True

    return display_gondola, display_gondola_buffer

def _generate_wall_modules(display_classes: dict | None, zoning: dict, enable_d7_display: bool = False, enable_d8_display: bool = False) -> tuple[list[dict], list[dict]]:
    if not display_classes:
        return [], []

    sales = zoning["sales_zone"]
    fixtures: list[dict] = []
    buffers: list[dict] = []
    module_idx = 1

    host_keys = ["D5", "D6"]
    if enable_d7_display:
        host_keys.append("D7")
    if enable_d8_display:
        host_keys.append("D8")

    for display_key in host_keys:
        for host_item in display_classes.get(display_key, []):
            host = host_item.get("rect", {})
            host_length = float(host.get("length", 0.0))
            host_width = float(host.get("width", 0.0))
            if host_length <= 0 or host_width <= 0:
                continue

            vertical_run = host_width >= host_length
            usable_run = host_width if vertical_run else host_length
            host_depth = host_length if vertical_run else host_width
            slot_count = int(usable_run // 0.60)
            seq = _sequence_for_host(display_key, slot_count)
            if not seq:
                continue
            widths = _fit_widths(seq, usable_run)
            side = _host_side(host, sales)
            cursor = float(host["y"] if vertical_run else host["x"])

            for family, module_run in zip(seq, widths):
                chosen = None
                chosen_family = family
                for candidate in _family_fallbacks(family):
                    chosen = _wall_depth_and_buffer(candidate, host_depth)
                    if chosen is not None:
                        chosen_family = candidate
                        break
                if chosen is None or module_run < 0.60 - 1e-6:
                    continue
                depth, buffer_depth = chosen

                if vertical_run:
                    if side == "left":
                        fx = float(host["x"])
                        bx = fx
                        bl = depth + buffer_depth
                    else:
                        fx = float(host["x"]) + host_length - depth
                        bx = fx - buffer_depth
                        bl = depth + buffer_depth
                    fixture = {"x": round(fx, 6), "y": round(cursor, 6), "length": round(depth, 6), "width": round(module_run, 6)}
                    buffer_rect = {"x": round(bx, 6), "y": round(cursor, 6), "length": round(bl, 6), "width": round(module_run, 6)}
                else:
                    # kept explicit for completeness if horizontal wall strips are later reused
                    fy = float(host["y"])
                    by = fy
                    bw = depth + buffer_depth
                    fixture = {"x": round(cursor, 6), "y": round(fy, 6), "length": round(module_run, 6), "width": round(depth, 6)}
                    buffer_rect = {"x": round(cursor, 6), "y": round(by, 6), "length": round(module_run, 6), "width": round(bw, 6)}

                fixtures.append(_rect_obj(
                    fixture,
                    "display_wall_module",
                    family=chosen_family,
                    host_display=display_key,
                    module_index=module_idx,
                    lineweight="heavy",
                    graphic_class="wall_module",
                ))
                buffers.append(_rect_obj(
                    buffer_rect,
                    "display_wall_buffer",
                    family=chosen_family,
                    host_display=display_key,
                    module_index=module_idx,
                    lineweight="heavy",
                    dash=True,
                    graphic_class="wall_buffer",
                ))
                module_idx += 1
                cursor += module_run

    return fixtures, buffers

def _area_based_fitting_count(area_m2: float) -> int:
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


def _generate_fitting_rooms(zoning: dict, fitting_side: str, area_m2: float, circulation: dict | None = None, layout_mode: str = "attached") -> list[dict]:
    fitting = zoning["fitting_zone"]
    fit_w = 1.20
    fit_d = 1.50
    opening = 0.80
    fitting_top_y = float(fitting["y"] + fitting["width"])

    # Default rule: top of rooms aligns to top of fitting suite.
    top_edge_y = fitting_top_y
    bottom_y = top_edge_y - fit_d

    # Override rule: if depth between fitting-suite top and service-connector top
    # is <= 1.50 m, align room bottoms to connector top instead.
    if circulation and circulation.get("service_connector"):
        connector = circulation["service_connector"]
        connector_top_y = float(connector["y"] + connector["width"])
        spacing = fitting_top_y - connector_top_y
        if spacing <= fit_d:
            bottom_y = connector_top_y
            top_edge_y = bottom_y + fit_d

    requested_count = _area_based_fitting_count(area_m2)
    max_count = max(1, int(fitting["length"] // fit_w))
    count = min(requested_count, max_count)

    side = str(fitting_side).lower()
    layout_mode = str(layout_mode).lower()
    left_anchor_x = float(fitting["x"])
    right_anchor_x = float(fitting["x"] + fitting["length"] - fit_w)

    def _x_for_attached(slot_index: int) -> float:
        if side == "left":
            return float(left_anchor_x + slot_index * fit_w)
        return float(right_anchor_x - slot_index * fit_w)

    def _x_for_separated(room_number: int) -> float:
        if side == "left":
            primary_anchor, opposite_anchor = left_anchor_x, right_anchor_x
            primary_sign, opposite_sign = 1.0, -1.0
        else:
            primary_anchor, opposite_anchor = right_anchor_x, left_anchor_x
            primary_sign, opposite_sign = -1.0, 1.0

        if room_number % 2 == 1:
            slot_index = (room_number - 1) // 2
            return float(primary_anchor + primary_sign * slot_index * fit_w)
        slot_index = (room_number // 2) - 1
        return float(opposite_anchor + opposite_sign * slot_index * fit_w)

    rooms = []
    used_x = []
    for room_number in range(1, count + 1):
        if layout_mode == "separated":
            x = _x_for_separated(room_number)
        else:
            x = _x_for_attached(room_number - 1)

        if any(abs(x - ux) < 1e-6 for ux in used_x):
            continue
        if x < float(fitting["x"]) - 1e-6 or (x + fit_w) > float(fitting["x"] + fitting["length"]) + 1e-6:
            continue
        used_x.append(x)

        op_start = x + (fit_w - opening) / 2.0
        op_end = op_start + opening
        room_id = f"Fit{room_number}"
        rooms.append({
            "id": room_id,
            "index": room_number,
            "x": x,
            "y": bottom_y,
            "length": fit_w,
            "width": fit_d,
            "layout_mode": layout_mode,
            "opening": {"side": "bottom", "width": opening, "x1": op_start, "x2": op_end, "y": bottom_y},
            "segments": [
                {"x1": x, "y1": bottom_y, "x2": op_start, "y2": bottom_y},
                {"x1": op_end, "y1": bottom_y, "x2": x + fit_w, "y2": bottom_y},
                {"x1": x, "y1": bottom_y, "x2": x, "y2": top_edge_y},
                {"x1": x + fit_w, "y1": bottom_y, "x2": x + fit_w, "y2": top_edge_y},
                {"x1": x, "y1": top_edge_y, "x2": x + fit_w, "y2": top_edge_y},
            ],
        })
    return rooms



def _build_fitting_area_buffer(zoning: dict, circulation: dict | None, fitting_rooms: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    fitting = zoning["fitting_zone"]
    fitting_top_y = float(fitting["y"] + fitting["width"])
    connector_top_y = float(fitting["y"])
    if circulation and circulation.get("service_connector"):
        connector = circulation["service_connector"]
        connector_top_y = float(connector["y"] + connector["width"])
    if fitting_top_y <= connector_top_y + 1e-6:
        return [], []

    x0 = float(fitting["x"])
    x1 = float(fitting["x"] + fitting["length"])
    intervals = [(x0, x1)]
    for room in fitting_rooms or []:
        rx0 = max(x0, float(room.get("x", x0)))
        rx1 = min(x1, float(room.get("x", x0)) + float(room.get("length", 0.0)))
        if rx1 <= rx0 + 1e-6:
            continue
        updated = []
        for a, b in intervals:
            if rx1 <= a + 1e-6 or rx0 >= b - 1e-6:
                updated.append((a, b))
            else:
                if a < rx0 - 1e-6:
                    updated.append((a, rx0))
                if rx1 < b - 1e-6:
                    updated.append((rx1, b))
        intervals = updated

    lines = []
    labels = []
    rects = []
    for a, b in intervals:
        if b <= a + 1e-6:
            continue
        rect = {"x": a, "y": connector_top_y, "length": b - a, "width": fitting_top_y - connector_top_y}
        rects.append(rect)
        lines.extend([
            _line_obj(a, connector_top_y, b, connector_top_y, "fitting_area_buffer_boundary"),
            _line_obj(a, fitting_top_y, b, fitting_top_y, "fitting_area_buffer_boundary"),
            _line_obj(a, connector_top_y, a, fitting_top_y, "fitting_area_buffer_boundary"),
            _line_obj(b, connector_top_y, b, fitting_top_y, "fitting_area_buffer_boundary"),
        ])
    if rects:
        largest = max(rects, key=lambda r: r["length"] * r["width"])
        lx, ly = _center(largest)
        labels.append(_text_obj(lx, ly, "FITTING AREA BUFFER", role="zone_label", text_size="small"))
    return lines, labels



def _trim_checkout_span_for_t8(x0: float, x1: float, t8_soft_rects: list[dict] | None) -> tuple[float, float]:
    """Trim checkout horizontal span so it stops at the nearest vertical soft-buffer edge of T8.

    This avoids drawing CHECKOUT BUFFER / CHECKOUT COUNTER horizontal boundaries under or over
    the T8 soft buffer zone once T8 is hosted above the counter.
    """
    rects = [r for r in (t8_soft_rects or []) if isinstance(r, dict)]
    if not rects:
        return x0, x1

    host_center_x = (x0 + x1) / 2.0
    # Use the T8 module closest to the checkout centerline; if multiple exist, this keeps the
    # trimming stable and deterministic. Then trim the side on which the T8 sits.
    target = min(rects, key=lambda r: abs((float(r.get("x", 0.0)) + float(r.get("length", 0.0)) / 2.0) - host_center_x))
    sx0 = float(target.get("x", 0.0))
    sx1 = sx0 + float(target.get("length", 0.0))
    scx = (sx0 + sx1) / 2.0

    if scx >= host_center_x:
        candidate_x1 = min(x1, sx0)
        if candidate_x1 - x0 >= T8_CHECKOUT_MIN_TRIMMED_WIDTH_M - 1e-6:
            x1 = candidate_x1
    else:
        candidate_x0 = max(x0, sx1)
        if x1 - candidate_x0 >= T8_CHECKOUT_MIN_TRIMMED_WIDTH_M - 1e-6:
            x0 = candidate_x0
    return x0, x1


def _trim_checkout_span_for_t9(x0: float, x1: float, checkout: dict, shell: dict | None, t9_count: int = 0) -> tuple[float, float]:
    """Reduce checkout width by 20% per placed T9 from the *other* vertical side.

    This is the mirrored behavior of the previous T9 checkout reduction rule.
    If the checkout touches an exterior wall on one side, the reduction is applied from
    that wall side instead of the opposite side.

    Guardrail: regardless of T9 count, CHECKOUT BUFFER / CHECKOUT COUNTER may not be
    reduced below 1.50 m in the X-axis.
    """
    count = max(0, int(t9_count or 0))
    if count <= 0:
        return x0, x1
    current_w = x1 - x0
    if current_w <= 1e-6:
        return x0, x1
    factor = max(0.0, 1.0 - 0.20 * count)
    new_w = current_w * factor
    min_w = 1.50
    new_w = max(min_w, new_w)
    if new_w >= current_w - 1e-6:
        return x0, x1

    shell = shell or {}
    shell_x0 = float(shell.get("x", x0))
    shell_x1 = float(shell.get("x", x0)) + float(shell.get("length", max(current_w, new_w)))
    left_touch = abs(x0 - shell_x0) <= 1e-6
    right_touch = abs(x1 - shell_x1) <= 1e-6

    if right_touch and not left_touch:
        # Mirror the previous behavior: trim from the right wall side.
        x1 = x0 + new_w
    elif left_touch and not right_touch:
        # Mirror the previous behavior: trim from the left wall side.
        x0 = x1 - new_w
    else:
        # Fallback: preserve the side that is farther from the nearest shell wall.
        if abs(x0 - shell_x0) <= abs(shell_x1 - x1):
            x0 = x1 - new_w
        else:
            x1 = x0 + new_w
    return x0, x1


def _build_checkout_buffer(zoning: dict, circulation: dict | None, t8_soft_rects: list[dict] | None = None, shell: dict | None = None, t9_count: int = 0) -> tuple[list[dict], list[dict], dict | None]:
    checkout = zoning["checkout_zone"]
    depth = 1.0
    connector_top_y = float(checkout["y"])
    if circulation and circulation.get("service_connector"):
        connector = circulation["service_connector"]
        connector_top_y = float(connector["y"] + connector["width"])
    max_top_y = float(checkout["y"] + checkout["width"])
    top_y = min(connector_top_y + depth, max_top_y)
    if top_y <= connector_top_y + 1e-6:
        return [], [], None
    x0 = float(checkout["x"])
    x1 = float(checkout["x"] + checkout["length"])
    x0, x1 = _trim_checkout_span_for_t8(x0, x1, t8_soft_rects)
    x0, x1 = _trim_checkout_span_for_t9(x0, x1, checkout, shell, t9_count=t9_count)
    if x1 <= x0 + 1e-6:
        return [], [], None
    lines = [
        _line_obj(x0, connector_top_y, x1, connector_top_y, "checkout_buffer_boundary"),
        _line_obj(x0, top_y, x1, top_y, "checkout_buffer_boundary"),
        _line_obj(x0, connector_top_y, x0, top_y, "checkout_buffer_boundary"),
        _line_obj(x1, connector_top_y, x1, top_y, "checkout_buffer_boundary"),
    ]
    labels = [_text_obj((x0 + x1) / 2.0, (connector_top_y + top_y) / 2.0, "CHECKOUT BUFFER", role="zone_label", text_size="small")]
    rect = {"x": x0, "y": connector_top_y, "length": x1 - x0, "width": top_y - connector_top_y}
    return lines, labels, rect


def _checkout_counter_rect(checkout_buffer_rect: dict | None) -> dict | None:
    if not checkout_buffer_rect:
        return None
    depth = 0.60
    x0 = float(checkout_buffer_rect["x"])
    x1 = float(checkout_buffer_rect["x"] + checkout_buffer_rect["length"])
    buffer_top_y = float(checkout_buffer_rect["y"] + checkout_buffer_rect["width"])
    return {"x": x0, "y": buffer_top_y, "length": x1 - x0, "width": depth}


def _build_checkout_counter(checkout_buffer_rect: dict | None) -> tuple[list[dict], list[dict]]:
    counter_rect = _checkout_counter_rect(checkout_buffer_rect)
    if not counter_rect:
        return [], []
    x0 = float(counter_rect["x"])
    x1 = float(counter_rect["x"] + counter_rect["length"])
    y0 = float(counter_rect["y"])
    y1 = float(counter_rect["y"] + counter_rect["width"])
    lines = [
        _line_obj(x0, y0, x1, y0, "checkout_counter_boundary"),
        _line_obj(x0, y1, x1, y1, "checkout_counter_boundary"),
        _line_obj(x0, y0, x0, y1, "checkout_counter_boundary"),
        _line_obj(x1, y0, x1, y1, "checkout_counter_boundary"),
    ]
    labels = [_text_obj((x0 + x1) / 2.0, (y0 + y1) / 2.0, "CHECKOUT COUNTER", role="zone_label", text_size="small")]
    return lines, labels


def _build_checkout_staff_buffer(checkout_buffer_rect: dict | None) -> tuple[list[dict], list[dict]]:
    counter_rect = _checkout_counter_rect(checkout_buffer_rect)
    if not counter_rect:
        return [], []
    depth = 0.80
    x0 = float(counter_rect["x"])
    x1 = float(counter_rect["x"] + counter_rect["length"])
    y0 = float(counter_rect["y"] + counter_rect["width"])
    y1 = float(y0 + depth)
    lines = [
        _line_obj(x0, y0, x1, y0, "checkout_staff_buffer_boundary", dash=True, lineweight="heavy"),
        _line_obj(x0, y1, x1, y1, "checkout_staff_buffer_boundary", dash=True, lineweight="heavy"),
        _line_obj(x0, y0, x0, y1, "checkout_staff_buffer_boundary", dash=True, lineweight="heavy"),
        _line_obj(x1, y0, x1, y1, "checkout_staff_buffer_boundary", dash=True, lineweight="heavy"),
    ]
    labels = [_text_obj((x0 + x1) / 2.0, (y0 + y1) / 2.0, "CHECKOUT STAFF BUFFER", role="zone_label", text_size="small")]
    return lines, labels

def _shell_layers(shell: dict) -> dict:
    outer = shell.get("outer_boundary")
    inner = shell.get("inner_clear_boundary")
    entrance = shell.get("entrance_opening", {})
    length_m = float(shell.get("length_m", 0.0))

    wall_ext, wall_glass, openings, labels = [], [], [], []
    if outer and inner:
        west_t = inner["x"] - outer["x"]
        east_t = (outer["x"] + outer["length"]) - (inner["x"] + inner["length"])
        south_t = inner["y"] - outer["y"]
        north_t = (outer["y"] + outer["width"]) - (inner["y"] + inner["width"])

        if west_t > 0:
            wall_ext.append(_rect_obj({"x": outer["x"], "y": outer["y"], "length": west_t, "width": outer["width"]}, "wall_external"))
        if east_t > 0:
            wall_ext.append(_rect_obj({"x": inner["x"] + inner["length"], "y": outer["y"], "length": east_t, "width": outer["width"]}, "wall_external"))
        if north_t > 0:
            wall_ext.append(_rect_obj({"x": outer["x"], "y": inner["y"] + inner["width"], "length": outer["length"], "width": north_t}, "wall_external"))

        x1 = float(entrance.get("x1", 0.0))
        x2 = float(entrance.get("x2", 0.0))
        if south_t > 0:
            if x1 > outer["x"]:
                wall_glass.append(_rect_obj({"x": outer["x"], "y": outer["y"], "length": x1 - outer["x"], "width": south_t}, "wall_glass"))
            if x2 < outer["x"] + outer["length"]:
                wall_glass.append(_rect_obj({"x": x2, "y": outer["y"], "length": outer["x"] + outer["length"] - x2, "width": south_t}, "wall_glass"))

        openings.append(_line_obj(x1, outer["y"], x2, outer["y"], "entrance_opening", width_m=float(entrance.get("width_m", 0.0))))
        labels.append(_text_obj(length_m / 2.0, outer["y"] - 0.95, "SOUTH FRONTAGE / GLASS WALL", role="title"))

    return {"WALL_EXT": wall_ext, "WALL_GLASS": wall_glass, "OPENINGS": openings, "LABELS": labels, "DIMENSIONS": []}


def _build_drawing(shell: dict, zoning: dict, added: dict | None, circulation: dict | None, frontage: dict | None, display_classes: dict | None, fitting_rooms: list[dict] | None = None, enable_d7_display: bool = False, enable_d8_display: bool = False, enable_d11_display: bool = False, t1_enabled: bool = False, t1_count: int = 0, t1_width_m: float = 0.60, t1_depth_m: float = 0.30, t2_enabled: bool = False, t2_count: int = 0, t2_width_m: float = 0.60, t2_depth_m: float = 0.60, t3_enabled: bool = False, t3_count: int = 0, t3_width_m: float = 0.60, t3_depth_m: float = 0.30, t4_enabled: bool = False, t4_count: int = 0, t4_width_m: float = 0.80, t4_depth_m: float = 0.60, t5_enabled: bool = False, t5_count: int = 0, t5_width_m: float = 1.50, t5_depth_m: float = 1.50, t6_enabled: bool = False, t6_count: int = 0, t6_width_m: float = 0.80, t6_depth_m: float = 0.80, t7_enabled: bool = False, t7_count: int = 0, t7_width_m: float = 1.20, t7_depth_m: float = 1.20, t8_enabled: bool = False, t8_count: int = 0, t8_width_m: float = 0.60, t8_depth_m: float = 0.30, t9_enabled: bool = False, t9_count: int = 0, t9_width_m: float = 1.20, t9_depth_m: float = 0.60) -> dict:
    layers = _shell_layers(shell)
    labels = list(layers.get("LABELS", []))
    zone_guides = []
    added_zone_lines = []
    wall_int = []
    paths = []
    fitting_room_lines = []
    fitting_buffer_lines = []
    checkout_buffer_lines = []
    checkout_counter_lines = []
    checkout_staff_buffer_lines = []
    display_wall = []
    display_wall_buffer = []
    display_gondola = []
    display_gondola_buffer = []
    display_mannequin = []
    display_mannequin_buffer = []
    display_layers = {"DISPLAY_D1": [], "DISPLAY_D2": [], "DISPLAY_D3": [], "DISPLAY_D4": [], "DISPLAY_D5": [], "DISPLAY_D6": [], "DISPLAY_D7": [], "DISPLAY_D8": [], "DISPLAY_D9": [], "DISPLAY_D10": []}
    interactive_t1 = []
    interactive_t1_buffer_min = []
    interactive_t1_buffer = []
    interactive_t2 = []
    interactive_t2_buffer_min = []
    interactive_t2_buffer = []
    interactive_t3 = []
    interactive_t3_buffer_min = []
    interactive_t3_buffer = []
    interactive_t4 = []
    interactive_t4_buffer_min = []
    interactive_t4_buffer = []
    interactive_t5 = []
    interactive_t5_buffer_min = []
    interactive_t5_buffer = []
    interactive_t6 = []
    interactive_t6_buffer_min = []
    interactive_t6_buffer = []
    interactive_t7 = []
    interactive_t7_buffer_min = []
    interactive_t7_buffer = []
    interactive_t8 = []
    interactive_t8_buffer_min = []
    interactive_t8_buffer = []
    interactive_t9 = []
    interactive_t9_buffer_min = []
    interactive_t9_buffer = []

    inner = shell["inner_clear_boundary"]
    sales = zoning["sales_zone"]
    fitting = zoning["fitting_zone"]
    checkout = zoning["checkout_zone"]
    boh = zoning["boh_zone"]
    entrance_node = zoning["entrance_node"]

    zone_guides.append(_line_obj(inner["x"], zoning["service_lines"]["sales_to_back_y"], inner["x"] + inner["length"], zoning["service_lines"]["sales_to_back_y"], "zone_boundary", dash=True))
    zone_guides.append(_line_obj(inner["x"], zoning["service_lines"]["service_to_boh_y"], inner["x"] + inner["length"], zoning["service_lines"]["service_to_boh_y"], "zone_boundary", dash=True))
    zone_guides.append(_line_obj(zoning["service_lines"]["fit_checkout_x"], zoning["service_lines"]["sales_to_back_y"], zoning["service_lines"]["fit_checkout_x"], zoning["service_lines"]["service_to_boh_y"], "zone_boundary", dash=True))

    wall_int.append(_rect_obj(entrance_node, "entrance_node", lineweight="light"))

    ex, ey = _center(entrance_node)
    labels.append(_text_obj(ex, ey, entrance_node.get("label", "ENTRANCE /\nDECOMPRESSION"), role="zone_label", text_size="small"))
    sx, sy = _center(sales)
    labels.append(_text_obj(sx, sy, sales.get("label", "SALES / DISPLAY"), role="zone_label", text_size="zone"))
    fx, fy = _center(fitting)
    labels.append(_text_obj(fx, fy, fitting.get("label", "FITTING\nSUITE"), role="zone_label", text_size="small"))
    cx, cy = _center(checkout)
    labels.append(_text_obj(cx, cy, checkout.get("label", "CHECKOUT"), role="zone_label", text_size="small"))
    bx, by = _center(boh)
    labels.append(_text_obj(bx, by, boh.get("label", "BACK OF HOUSE\n(STAFF ONLY)"), role="zone_label", text_size="small"))

    cleared_island_rects: list[dict] = []
    hosted_added_zone_rects: list[dict] = []
    added_fill_f5: list[dict] = []
    added_fill_f5_buffer: list[dict] = []
    removed_fixture_ids: set[tuple[str, int]] = set()
    if added and added.get("zones"):
        for item in added["zones"]:
            if item.get("key") in {"lounge_seating", "queue_pocket", "promotional_featured", "digital_interaction"}:
                if item.get("key") == "lounge_seating":
                    priority_rect = zoning.get("fitting_zone")
                    hosted_rects, host_islands = _host_added_zone_by_islands(display_classes, item, priority_rect=priority_rect)
                elif item.get("key") == "queue_pocket":
                    priority_rect = zoning.get("checkout_zone")
                    hosted_rects, host_islands = _host_added_zone_by_islands(display_classes, item, priority_rect=priority_rect)
                elif item.get("key") == "promotional_featured":
                    # Promotional / Featured should prioritize frontage islands attached to the entrance glass wall first.
                    priority_rect = zoning.get("entrance_node")
                    hosted_rects, host_islands = _host_added_zone_by_islands(
                        display_classes,
                        item,
                        priority_rect=priority_rect,
                        allowed_keys=["D3", "D4", "D9", "D10", "D11", "D12"],
                        prefer_front_glass=True,
                    )
                else:
                    # Digital Interaction should use the same hosted-by-islands logic,
                    # but prioritize the central display field of the store first.
                    priority_rect = sales
                    hosted_rects, host_islands = _host_added_zone_by_islands(
                        display_classes,
                        item,
                        priority_rect=priority_rect,
                        allowed_keys=["D1", "D2"],
                        prefer_front_glass=False,
                    )
                for host_rect in host_islands:
                    if not any(_rects_overlap(host_rect, existing) and _rect_area(host_rect) == _rect_area(existing) for existing in cleared_island_rects):
                        cleared_island_rects.append(host_rect)
                hosted_added_zone_rects.extend(hosted_rects)
                fill_f5, fill_f5_buffer = _generate_f5_fill_around_added_zone(hosted_rects, host_islands, zone_key=item.get("key"))
                added_fill_f5.extend(fill_f5)
                added_fill_f5_buffer.extend(fill_f5_buffer)
                for hosted in hosted_rects:
                    added_zone_lines.append(_rect_obj(hosted, "added_zone", dash=False, lineweight="heavy"))
                    ax, ay = _center(hosted)
                    labels.append(_text_obj(ax, ay, item["label"], role="zone_label", text_size="small"))
            else:
                r = item["rect"]
                added_zone_lines.append(_rect_obj(r, "added_zone", dash=False, lineweight="heavy"))
                ax, ay = _center(r)
                labels.append(_text_obj(ax, ay, item["label"], role="zone_label", text_size="small"))

    if frontage and frontage.get("zones"):
        for item in frontage["zones"]:
            r = item["rect"]
            zone_guides.append(_rect_obj(r, "frontage_zone", dash=True))

    frontage_display_keys = set()
    if display_classes:
        display_wall, display_wall_buffer = _generate_wall_modules(display_classes, zoning, enable_d7_display=enable_d7_display, enable_d8_display=enable_d8_display)
        display_gondola, display_gondola_buffer = _generate_d1_modules(display_classes, circulation)
        d2_mannequin, d2_mannequin_buffer, d2_table, d2_table_buffer_min, d2_table_buffer, d2_f8_labels = _generate_d2_mix_modules(
            display_classes,
            display_wall,
            display_gondola,
            circulation,
        )
        display_mannequin, display_mannequin_buffer = _generate_f7_1_modules(
            display_classes,
            display_wall,
            display_gondola,
            circulation,
            enable_d11_display=enable_d11_display,
        )
        display_mannequin = d2_mannequin + display_mannequin
        display_mannequin_buffer = d2_mannequin_buffer + display_mannequin_buffer
        display_table, display_table_buffer_min, display_table_buffer, f8_labels = _generate_f8_modules(
            display_classes,
            display_wall,
            display_gondola,
            display_mannequin,
            circulation,
        )
        display_table = d2_table + display_table
        display_table_buffer_min = d2_table_buffer_min + display_table_buffer_min
        display_table_buffer = d2_table_buffer + display_table_buffer
        labels.extend(d2_f8_labels)
        labels.extend(f8_labels)
        for key in ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"]:
            layer = f"DISPLAY_{key}"
            if layer not in display_layers:
                display_layers[layer] = []
            for item in display_classes.get(key, []):
                rect = item["rect"]
                display_layers[layer].append(_rect_obj(rect, f"display_{key.lower()}"))
                if key not in frontage_display_keys:
                    lx, ly = _center(rect)
                    labels.append(_text_obj(lx, ly, key, role="zone_label", text_size="small"))

        if t1_enabled and t1_count > 0:
            t1_pack = _build_t1_placements(display_classes, zoning, int(t1_count), float(t1_width_m), float(t1_depth_m))
            interactive_t1 = list(t1_pack.get("hard", []))
            interactive_t1_buffer_min = list(t1_pack.get("min", []))
            interactive_t1_buffer = list(t1_pack.get("soft", []))
            labels.extend(t1_pack.get("labels", []))
            t1_clear_rects = list(t1_pack.get("clear", []))
            if t1_clear_rects:
                display_wall, display_wall_buffer, removed_wall_t1 = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, t1_clear_rects)
                display_gondola, display_gondola_buffer, removed_gondola_t1 = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, t1_clear_rects)
                display_mannequin, display_mannequin_buffer, removed_mannequin_t1 = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, t1_clear_rects)
                display_table, display_table_buffer_min, removed_table_min_t1 = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, t1_clear_rects)
                removed_table_t1 = set(removed_table_min_t1)
                removed_t1 = set(removed_wall_t1) | set(removed_gondola_t1) | set(removed_mannequin_t1) | set(removed_table_t1)
                removed_fixture_ids |= removed_t1
                display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_t1]
                labels = [
                    obj for obj in labels
                    if not (
                        obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                        any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), clr) for clr in t1_clear_rects)
                    )
                ]

        _t5_block_pack = None
        if t8_enabled and t8_count > 0:
            t8_pack = _build_t8_placements(display_classes, zoning, circulation, int(t8_count), float(t8_width_m), float(t8_depth_m), side_offset_m=0.60, front_soft_m=2.40, front_min_m=1.20)
            interactive_t8 = list(t8_pack.get("hard", []))
            interactive_t8_buffer_min = list(t8_pack.get("min", []))
            interactive_t8_buffer = list(t8_pack.get("soft", []))
            labels.extend(t8_pack.get("labels", []))

            if any(str(obj.get("host_key", "")) == "D8" for obj in interactive_t8):
                d8_clear_rects = [item.get("rect") for item in (display_classes.get("D8", []) or []) if isinstance(item, dict) and item.get("rect")]
                if d8_clear_rects:
                    display_wall, display_wall_buffer, removed_wall_t8d8 = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, d8_clear_rects, remove_surviving_buffers_on_overlap=False)
                    display_gondola, display_gondola_buffer, removed_gondola_t8d8 = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, d8_clear_rects, remove_surviving_buffers_on_overlap=False)
                    display_mannequin, display_mannequin_buffer, removed_mannequin_t8d8 = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, d8_clear_rects)
                    display_table, display_table_buffer_min, removed_table_min_t8d8 = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, d8_clear_rects)
                    removed_table_t8d8 = set(removed_table_min_t8d8)
                    removed_t8d8 = set(removed_wall_t8d8) | set(removed_gondola_t8d8) | set(removed_mannequin_t8d8) | set(removed_table_t8d8)
                    removed_fixture_ids |= removed_t8d8
                    display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_t8d8]
                    labels = [
                        obj for obj in labels
                        if not (
                            obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                            any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), clr) for clr in d8_clear_rects)
                        )
                    ]

        if t5_enabled and t5_count > 0:
            _t5_block_pack = _build_t5_placements(display_classes, zoning, circulation, fitting_rooms, int(t5_count), float(t5_width_m), float(t5_depth_m), allow_d7=enable_d7_display)

        _t4_block_pack = None
        if t4_enabled and t4_count > 0:
            _t4_block_pack = _build_t4_placements(display_classes, zoning, int(t4_count), float(t4_width_m), float(t4_depth_m), side_offset_m=0.60, front_soft_m=1.60, front_min_m=1.20, blocked_soft_rects=list((_t5_block_pack or {}).get("soft", [])))

        if t2_enabled and t2_count > 0:
            t2_pack = _build_t2_placements(display_classes, zoning, int(t2_count), float(t2_width_m), float(t2_depth_m), side_offset_m=0.60, front_soft_m=1.60, front_min_m=1.20, blocked_soft_rects=list((_t4_block_pack or {}).get("soft", [])))
            interactive_t2 = list(t2_pack.get("hard", []))
            interactive_t2_buffer_min = list(t2_pack.get("min", []))
            interactive_t2_buffer = list(t2_pack.get("soft", []))
            labels.extend(t2_pack.get("labels", []))
            t2_clear_rects = list(t2_pack.get("clear", []))
            if t2_clear_rects:
                display_wall, display_wall_buffer, removed_wall_t2 = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, t2_clear_rects, remove_surviving_buffers_on_overlap=False)
                display_gondola, display_gondola_buffer, removed_gondola_t2 = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, t2_clear_rects, remove_surviving_buffers_on_overlap=False)
                if interactive_t2_buffer:
                    display_gondola, display_gondola_buffer, _removed_gondola_soft_t2 = _filter_selected_fixture_families_by_islands(display_gondola, display_gondola_buffer, interactive_t2_buffer, {"F4", "F5", "F6"}, remove_surviving_buffers_on_overlap=False)
                # D2 pressure-resolution patch: protect the minimum buffer area of T2
                # before hard-footprint cleanup, so D2 does not keep F7/F8/F4-F6 residues
                # visually colliding with the interactive kiosk.
                display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _clear_d1_fixture_area_for_interactive_min(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t2_buffer_min, clear_surviving_buffers_on_overlap=True)
                display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _remove_d1_fixture_overlaps_for_interactive_hard(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t2, clear_surviving_buffers_on_overlap=True)
                display_mannequin, display_mannequin_buffer, removed_mannequin_t2 = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, t2_clear_rects)
                display_table, display_table_buffer_min, removed_table_min_t2 = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, t2_clear_rects)
                removed_table_t2 = set(removed_table_min_t2)
                removed_t2 = set(removed_wall_t2) | set(removed_gondola_t2) | set(removed_mannequin_t2) | set(removed_table_t2)
                removed_fixture_ids |= removed_t2
                display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_t2]
                labels = [
                    obj for obj in labels
                    if not (
                        obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                        any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), clr) for clr in t2_clear_rects)
                    )
                ]

        joint_t3_t5 = None
        if t3_enabled and t5_enabled and t3_count > 0 and t5_count > 0:
            joint_t3_t5 = _build_t3_t5_joint_placements(display_classes, zoning, circulation, fitting_rooms, int(t3_count), float(t3_width_m), float(t3_depth_m), int(t5_count), float(t5_width_m), float(t5_depth_m), allow_d7=enable_d7_display)

        if t3_enabled and t3_count > 0:
            t3_pack = (joint_t3_t5 or {}).get("t3") if joint_t3_t5 else _build_t3_placements(display_classes, zoning, circulation, fitting_rooms, int(t3_count), float(t3_width_m), float(t3_depth_m), side_offset_m=0.60, front_soft_m=1.60, front_min_m=1.20, allow_d7=enable_d7_display)
            interactive_t3 = list((t3_pack or {}).get("hard", []))
            interactive_t3_buffer_min = list((t3_pack or {}).get("min", []))
            interactive_t3_buffer = list((t3_pack or {}).get("soft", []))
            labels.extend((t3_pack or {}).get("labels", []))
            fitting_rooms = list((joint_t3_t5 or {}).get("kept_rooms", (t3_pack or {}).get("kept_rooms", fitting_rooms or [])))
            t3_clear_rects = list((t3_pack or {}).get("clear", []))
            if t3_clear_rects:
                display_wall, display_wall_buffer, removed_wall_t3 = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, t3_clear_rects, remove_surviving_buffers_on_overlap=False)
                display_gondola, display_gondola_buffer, removed_gondola_t3 = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, t3_clear_rects, remove_surviving_buffers_on_overlap=False)
                display_mannequin, display_mannequin_buffer, removed_mannequin_t3 = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, t3_clear_rects)
                display_table, display_table_buffer_min, removed_table_min_t3 = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, t3_clear_rects)
                removed_table_t3 = set(removed_table_min_t3)
                removed_t3 = set(removed_wall_t3) | set(removed_gondola_t3) | set(removed_mannequin_t3) | set(removed_table_t3)
                removed_fixture_ids |= removed_t3
                display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_t3]
                labels = [
                    obj for obj in labels
                    if not (
                        obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                        any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), clr) for clr in t3_clear_rects)
                    )
                ]

        if t4_enabled and t4_count > 0:
            t4_pack = _build_t4_placements(display_classes, zoning, int(t4_count), float(t4_width_m), float(t4_depth_m), side_offset_m=0.60, front_soft_m=1.60, front_min_m=1.20, blocked_soft_rects=list((t2_pack if t2_enabled and t2_count > 0 else {}).get("soft", [])))
            interactive_t4 = list(t4_pack.get("hard", []))
            interactive_t4_buffer_min = list(t4_pack.get("min", []))
            interactive_t4_buffer = list(t4_pack.get("soft", []))
            labels.extend(t4_pack.get("labels", []))
            if interactive_t4_buffer:
                display_gondola, display_gondola_buffer, _removed_gondola_soft_t4 = _filter_selected_fixture_families_by_islands(display_gondola, display_gondola_buffer, interactive_t4_buffer, {"F4", "F5", "F6"}, remove_surviving_buffers_on_overlap=False)
            display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _remove_d1_fixture_overlaps_for_interactive_hard(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t4)

        t6_pack = None
        if t6_enabled and t6_count > 0:
            _t6_blocked = []
            _t6_blocked.extend(list((t4_pack if t4_enabled and t4_count > 0 else {}).get("min", [])))
            _t6_blocked.extend(list((t2_pack if t2_enabled and t2_count > 0 else {}).get("min", [])))
            t6_pack = _build_t6_placements(display_classes, int(t6_count), float(t6_width_m), float(t6_depth_m), blocked_soft_rects=_t6_blocked)
            interactive_t6 = list(t6_pack.get("hard", []))
            interactive_t6_buffer_min = list(t6_pack.get("min", []))
            interactive_t6_buffer = list(t6_pack.get("soft", []))
            labels.extend(t6_pack.get("labels", []))
            if interactive_t6_buffer:
                display_gondola, display_gondola_buffer, _removed_gondola_soft_t6 = _filter_selected_fixture_families_by_islands(display_gondola, display_gondola_buffer, interactive_t6_buffer, {"F4", "F5", "F6"}, remove_surviving_buffers_on_overlap=False)
            # T6 has priority inside D1: if a T6 host overlaps any F8 table footprint or its
            # minimum buffer inside D1, remove that F8 before the generic D1 cleanup runs.
            _t6_priority_rects = [obj for obj in (interactive_t6 + interactive_t6_buffer_min) if isinstance(obj, dict) and str(obj.get("host_key", "")) == "D1"]
            if _t6_priority_rects:
                # Narrow D1 rule requested by the user: when T6 is hosted in D1,
                # any F8 table that lies inside D1 boundaries is removed so T6 keeps priority there.
                _d1_host_rects = []
                for _item in (display_classes.get("D1", []) or []):
                    _rect = _item.get("rect") if isinstance(_item, dict) else None
                    if _rect:
                        _d1_host_rects.append(_rect)
                _removed_f8_t6 = set()
                if _d1_host_rects:
                    display_table, display_table_buffer_min, _removed_f8_host = _filter_selected_fixture_families_by_islands(
                        display_table, display_table_buffer_min, _d1_host_rects, {"F8"}, remove_surviving_buffers_on_overlap=True
                    )
                    _removed_f8_t6 |= set(_removed_f8_host)
                # Safety fallback: if any F8 still geometrically overlaps the hosted T6
                # hard or minimum buffer in D1, remove it as well.
                _kept_tables = []
                for obj in display_table or []:
                    fam = str(obj.get("family", ""))
                    rect = obj if obj.get("shape") == "rect" else _line_bbox(obj)
                    if fam == "F8" and any(_rects_overlap(rect, zr) for zr in _t6_priority_rects):
                        idx = int(obj.get("module_index", -1)) if obj.get("module_index") is not None else -1
                        if idx >= 0:
                            _removed_f8_t6.add((fam, idx))
                    else:
                        _kept_tables.append(obj)
                if _removed_f8_t6:
                    display_table = _kept_tables
                    display_table_buffer_min = [obj for obj in display_table_buffer_min if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in _removed_f8_t6]
                    display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in _removed_f8_t6]
                    removed_fixture_ids |= _removed_f8_t6
                    labels = [
                        obj for obj in labels
                        if not (
                            obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                            any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), zr) for zr in (_d1_host_rects or _t6_priority_rects))
                        )
                    ]
            display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _clear_d1_fixture_area_for_interactive_min(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t6_buffer_min, clear_surviving_buffers_on_overlap=True)
            display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _remove_d1_fixture_overlaps_for_interactive_hard(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t6, clear_surviving_buffers_on_overlap=True)

        t7_pack = None
        if t7_enabled and t7_count > 0:
            _t7_blocked = []
            _t7_blocked.extend(list((t4_pack if t4_enabled and t4_count > 0 else {}).get("min", [])))
            _t7_blocked.extend(list((t2_pack if t2_enabled and t2_count > 0 else {}).get("min", [])))
            _t7_blocked.extend(list((t6_pack if t6_enabled and t6_count > 0 else {}).get("min", [])))
            t7_pack = _build_t7_placements(display_classes, int(t7_count), float(t7_width_m), float(t7_depth_m), blocked_soft_rects=_t7_blocked)
            interactive_t7 = list(t7_pack.get("hard", []))
            interactive_t7_buffer_min = list(t7_pack.get("min", []))
            interactive_t7_buffer = list(t7_pack.get("soft", []))
            labels.extend(t7_pack.get("labels", []))
            if interactive_t7_buffer:
                display_gondola, display_gondola_buffer, _removed_gondola_soft_t7 = _filter_selected_fixture_families_by_islands(display_gondola, display_gondola_buffer, interactive_t7_buffer, {"F4", "F5", "F6"}, remove_surviving_buffers_on_overlap=False)
            display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _clear_d1_fixture_area_for_interactive_min(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t7_buffer_min)
            display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _remove_d1_fixture_overlaps_for_interactive_hard(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t7)

        t9_pack = None
        if t9_enabled and t9_count > 0:
            _t9_blocked = []
            _t9_blocked.extend(list((t4_pack if t4_enabled and t4_count > 0 else {}).get("min", [])))
            _t9_blocked.extend(list((t2_pack if t2_enabled and t2_count > 0 else {}).get("min", [])))
            _t9_blocked.extend(list((t6_pack if t6_enabled and t6_count > 0 else {}).get("min", [])))
            _t9_blocked.extend(list((t7_pack if t7_enabled and t7_count > 0 else {}).get("min", [])))
            t9_pack = _build_t9_placements(display_classes, zoning, int(t9_count), float(t9_width_m), float(t9_depth_m), side_offset_m=0.60, front_soft_m=2.40, front_min_m=1.20, blocked_soft_rects=_t9_blocked)
            interactive_t9 = list(t9_pack.get("hard", []))
            interactive_t9_buffer_min = list(t9_pack.get("min", []))
            interactive_t9_buffer = list(t9_pack.get("soft", []))
            labels.extend(t9_pack.get("labels", []))
            t9_clear_rects = list(t9_pack.get("clear", []))
            if t9_clear_rects:
                display_wall, display_wall_buffer, removed_wall_t9 = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, t9_clear_rects, remove_surviving_buffers_on_overlap=False)
                display_gondola, display_gondola_buffer, removed_gondola_t9 = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, t9_clear_rects, remove_surviving_buffers_on_overlap=False)
                if interactive_t9_buffer:
                    display_gondola, display_gondola_buffer, _removed_gondola_soft_t9 = _filter_selected_fixture_families_by_islands(display_gondola, display_gondola_buffer, interactive_t9_buffer, {"F4", "F5", "F6"}, remove_surviving_buffers_on_overlap=False)
                # D2 pressure-resolution patch: T9 also receives protected minimum-buffer
                # clearance when hosted in D2, preventing F-family/device collision.
                display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _clear_d1_fixture_area_for_interactive_min(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t9_buffer_min, clear_surviving_buffers_on_overlap=True)
                display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids = _remove_d1_fixture_overlaps_for_interactive_hard(display_wall, display_wall_buffer, display_gondola, display_gondola_buffer, display_mannequin, display_mannequin_buffer, display_table, display_table_buffer_min, display_table_buffer, labels, removed_fixture_ids, interactive_t9, clear_surviving_buffers_on_overlap=True)
                display_mannequin, display_mannequin_buffer, removed_mannequin_t9 = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, t9_clear_rects)
                display_table, display_table_buffer_min, removed_table_min_t9 = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, t9_clear_rects)
                removed_table_t9 = set(removed_table_min_t9)
                removed_t9 = set(removed_wall_t9) | set(removed_gondola_t9) | set(removed_mannequin_t9) | set(removed_table_t9)
                removed_fixture_ids |= removed_t9
                display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_t9]
                labels = [
                    obj for obj in labels
                    if not (
                        obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                        any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), clr) for clr in t9_clear_rects)
                    )
                ]
        if t5_enabled and t5_count > 0:
            if joint_t3_t5:
                t5_pack = (joint_t3_t5 or {}).get("t5", {})
            else:
                t5_blocked = []
                if t4_enabled and t4_count > 0:
                    t5_blocked.extend(list((t4_pack or {}).get("soft", [])))
                if t3_enabled and t3_count > 0:
                    t5_blocked.extend(list((t3_pack or {}).get("soft", [])))
                t5_pack = _build_t5_placements(display_classes, zoning, circulation, fitting_rooms, int(t5_count), float(t5_width_m), float(t5_depth_m), allow_d7=enable_d7_display, blocked_soft_rects=t5_blocked)
            interactive_t5 = list((t5_pack or {}).get("hard", []))
            interactive_t5_buffer_min = list((t5_pack or {}).get("min", []))
            interactive_t5_buffer = list((t5_pack or {}).get("soft", []))
            labels.extend((t5_pack or {}).get("labels", []))
            fitting_rooms = list((joint_t3_t5 or {}).get("kept_rooms", fitting_rooms or [])) if joint_t3_t5 else fitting_rooms
            t5_clear_rects = list((t5_pack or {}).get("clear", []))
            if t5_clear_rects:
                display_wall, display_wall_buffer, removed_wall_t5 = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, t5_clear_rects, remove_surviving_buffers_on_overlap=False)
                display_gondola, display_gondola_buffer, removed_gondola_t5 = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, t5_clear_rects, remove_surviving_buffers_on_overlap=False)
                display_mannequin, display_mannequin_buffer, removed_mannequin_t5 = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, t5_clear_rects)
                display_table, display_table_buffer_min, removed_table_min_t5 = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, t5_clear_rects)
                removed_table_t5 = set(removed_table_min_t5)
                removed_t5 = set(removed_wall_t5) | set(removed_gondola_t5) | set(removed_mannequin_t5) | set(removed_table_t5)
                removed_fixture_ids |= removed_t5
                display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_t5]
                labels = [
                    obj for obj in labels
                    if not (
                        obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                        any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), clr) for clr in t5_clear_rects)
                    )
                ]

    if t4_enabled and int(t4_count) > 0 and fitting_rooms:
        fitting_rooms = _reduce_fitting_by_t4(fitting_rooms, int(t4_count))

    if display_classes:
        _interactive_hard_for_d1_recovery = interactive_t2 + interactive_t4 + interactive_t6 + interactive_t7 + interactive_t9
        _interactive_min_for_d1_recovery = interactive_t2_buffer_min + interactive_t4_buffer_min + interactive_t6_buffer_min + interactive_t7_buffer_min + interactive_t9_buffer_min
        _interactive_soft_for_d1_recovery = interactive_t2_buffer + interactive_t4_buffer + interactive_t6_buffer + interactive_t7_buffer + interactive_t9_buffer
        display_gondola, display_gondola_buffer = _d1_post_t_max_availability_recovery(
            display_classes,
            circulation,
            display_gondola,
            display_gondola_buffer,
            display_wall=display_wall,
            display_wall_buffer=display_wall_buffer,
            display_mannequin=display_mannequin,
            display_mannequin_buffer=display_mannequin_buffer,
            display_table=display_table,
            display_table_buffer_min=display_table_buffer_min,
            display_table_buffer=display_table_buffer,
            interactive_hard=_interactive_hard_for_d1_recovery,
            interactive_min=_interactive_min_for_d1_recovery,
            interactive_soft=_interactive_soft_for_d1_recovery,
        )

    if cleared_island_rects:
        display_wall, display_wall_buffer, removed_wall = _filter_fixture_family_by_islands(display_wall, display_wall_buffer, cleared_island_rects)
        display_gondola, display_gondola_buffer, removed_gondola = _filter_fixture_family_by_islands(display_gondola, display_gondola_buffer, cleared_island_rects)
        display_mannequin, display_mannequin_buffer, removed_mannequin = _filter_fixture_family_by_islands(display_mannequin, display_mannequin_buffer, cleared_island_rects)
        display_table, display_table_buffer_min, removed_table_min = _filter_fixture_family_by_islands(display_table, display_table_buffer_min, cleared_island_rects)
        removed_table = set(removed_table_min)
        removed_fixture_ids |= set(removed_wall) | set(removed_gondola) | set(removed_mannequin) | set(removed_table)
        display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_table]
        labels = [
            obj for obj in labels
            if not (
                obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), isl) for isl in cleared_island_rects)
            )
        ]
        # Extra safety: no F1–F8 hard footprint or hard label may remain inside or crossing
        # the actual hosted added-zone boundaries, even when the host island is only partially used.
        if hosted_added_zone_rects:
            def _filter_hard_against_added(rect_objs, zone_rects):
                kept = []
                removed = set()
                for obj in rect_objs or []:
                    rect = obj if obj.get("shape") == "rect" else _line_bbox(obj)
                    if any(_rects_overlap(rect, zr) for zr in zone_rects):
                        fam = str(obj.get("family", ""))
                        idx = int(obj.get("module_index", -1)) if obj.get("module_index") is not None else -1
                        if fam and idx >= 0:
                            removed.add((fam, idx))
                    else:
                        kept.append(obj)
                return kept, removed

            display_wall, rem_wall2 = _filter_hard_against_added(display_wall, hosted_added_zone_rects)
            display_gondola, rem_gond2 = _filter_hard_against_added(display_gondola, hosted_added_zone_rects)
            display_mannequin, rem_man2 = _filter_hard_against_added(display_mannequin, hosted_added_zone_rects)
            display_table, rem_tab2 = _filter_hard_against_added(display_table, hosted_added_zone_rects)
            removed_by_zone = rem_wall2 | rem_gond2 | rem_man2 | rem_tab2
            removed_fixture_ids |= set(removed_by_zone)
            display_wall_buffer = [obj for obj in display_wall_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_by_zone]
            display_gondola_buffer = [obj for obj in display_gondola_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_by_zone]
            display_mannequin_buffer = [obj for obj in display_mannequin_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_by_zone]
            display_table_buffer_min = [obj for obj in display_table_buffer_min if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_by_zone]
            display_table_buffer = [obj for obj in display_table_buffer if (str(obj.get("family", "")), int(obj.get("module_index", -1))) not in removed_by_zone]
            labels = [
                obj for obj in labels
                if not (
                    obj.get("shape") == "text" and obj.get("role") == "fixture_label" and
                    any(_point_in_rect(float(obj.get("x", 0.0)), float(obj.get("y", 0.0)), zr) for zr in hosted_added_zone_rects)
                )
            ]
            added_fill_f5 = [obj for obj in added_fill_f5 if not any(_rects_overlap(obj, zr) for zr in hosted_added_zone_rects)]
            added_fill_f5_buffer = [obj for obj in added_fill_f5_buffer if not any(_rects_overlap(obj if obj.get("shape") == "rect" else _line_bbox(obj), zr) for zr in hosted_added_zone_rects)]
        display_gondola.extend(added_fill_f5)
        display_gondola_buffer.extend(added_fill_f5_buffer)

    for room in fitting_rooms or []:
        for seg in room.get("segments", []):
            fitting_room_lines.append(_line_obj(seg["x1"], seg["y1"], seg["x2"], seg["y2"], "fitting_room_boundary"))
        rx, ry = _center(room)
        labels.append(_text_obj(rx, ry, room.get("id", "Fit1"), role="zone_label", text_size="small"))

    fitting_buffer_lines, fitting_buffer_labels = _build_fitting_area_buffer(zoning, circulation, fitting_rooms)
    labels.extend(fitting_buffer_labels)
    checkout_buffer_lines, checkout_buffer_labels, checkout_buffer_rect = _build_checkout_buffer(
        zoning,
        circulation,
        [r for r in interactive_t8_buffer if (r.get("host_key") == "CHECKOUT")],
        shell=shell,
        t9_count=len(interactive_t9),
    )
    labels.extend(checkout_buffer_labels)
    checkout_counter_lines, checkout_counter_labels = _build_checkout_counter(checkout_buffer_rect)
    labels.extend(checkout_counter_labels)
    checkout_staff_buffer_lines, checkout_staff_buffer_labels = _build_checkout_staff_buffer(checkout_buffer_rect)
    labels.extend(checkout_staff_buffer_labels)

    if circulation:
        if circulation.get("primary_spine"):
            sp = circulation["primary_spine"]
            paths.append(_rect_obj(sp, "primary_spine"))
            px, py = _center(sp)
            labels.append(_text_obj(px, py, "MAIN SPINE", role="zone_label", text_size="small"))
        if circulation.get("service_connector"):
            paths.append(_rect_obj(circulation["service_connector"], "service_connector"))
        for sec in circulation.get("secondary_aisles", []):
            paths.append(_rect_obj(sec, "secondary_aisle"))
        for side_sec in circulation.get("side_secondary_aisles", []):
            paths.append(_rect_obj(side_sec, "secondary_aisle"))
        for terr in circulation.get("territorial_aisles", []):
            paths.append(_rect_obj(terr, "territorial_aisle"))
        for terr_sec in circulation.get("territorial_secondary_aisles", []):
            paths.append(_rect_obj(terr_sec, "secondary_aisle"))

    layers["WALL_INT"] = wall_int
    layers["ZONE_GUIDES"] = zone_guides
    layers["ADDED_ZONES"] = added_zone_lines
    for layer_name, objs in display_layers.items():
        layers[layer_name] = objs
    layers["PATHS"] = paths
    layers["DISPLAY_WALL"] = display_wall
    layers["DISPLAY_WALL_BUFFER"] = display_wall_buffer
    layers["DISPLAY_GONDOLA"] = display_gondola
    layers["DISPLAY_GONDOLA_BUFFER"] = display_gondola_buffer
    layers["DISPLAY_MANNEQUIN"] = display_mannequin
    layers["DISPLAY_MANNEQUIN_BUFFER"] = display_mannequin_buffer
    layers["DISPLAY_TABLE"] = display_table
    layers["DISPLAY_TABLE_BUFFER_MIN"] = display_table_buffer_min
    layers["DISPLAY_TABLE_BUFFER"] = display_table_buffer
    layers["INTERACTIVE_T1_BUFFER"] = interactive_t1_buffer
    layers["INTERACTIVE_T1_BUFFER_MIN"] = interactive_t1_buffer_min
    layers["INTERACTIVE_T1"] = interactive_t1
    layers["INTERACTIVE_T2_BUFFER"] = interactive_t2_buffer
    layers["INTERACTIVE_T2_BUFFER_MIN"] = interactive_t2_buffer_min
    layers["INTERACTIVE_T2"] = interactive_t2
    layers["INTERACTIVE_T3_BUFFER"] = interactive_t3_buffer
    layers["INTERACTIVE_T3_BUFFER_MIN"] = interactive_t3_buffer_min
    layers["INTERACTIVE_T3"] = interactive_t3
    layers["INTERACTIVE_T4_BUFFER"] = interactive_t4_buffer
    layers["INTERACTIVE_T4_BUFFER_MIN"] = interactive_t4_buffer_min
    layers["INTERACTIVE_T4"] = interactive_t4
    layers["INTERACTIVE_T5_BUFFER"] = interactive_t5_buffer
    layers["INTERACTIVE_T5_BUFFER_MIN"] = interactive_t5_buffer_min
    layers["INTERACTIVE_T5"] = interactive_t5
    layers["INTERACTIVE_T6_BUFFER"] = interactive_t6_buffer
    layers["INTERACTIVE_T6_BUFFER_MIN"] = interactive_t6_buffer_min
    layers["INTERACTIVE_T6"] = interactive_t6
    layers["INTERACTIVE_T7_BUFFER"] = interactive_t7_buffer
    layers["INTERACTIVE_T7_BUFFER_MIN"] = interactive_t7_buffer_min
    layers["INTERACTIVE_T7"] = interactive_t7
    layers["INTERACTIVE_T8_BUFFER"] = interactive_t8_buffer
    layers["INTERACTIVE_T8_BUFFER_MIN"] = interactive_t8_buffer_min
    layers["INTERACTIVE_T8"] = interactive_t8
    layers["INTERACTIVE_T9_BUFFER"] = interactive_t9_buffer
    layers["INTERACTIVE_T9_BUFFER_MIN"] = interactive_t9_buffer_min
    layers["INTERACTIVE_T9"] = interactive_t9
    layers["FITTING_AREA_BUFFER"] = fitting_buffer_lines
    layers["CHECKOUT_BUFFER"] = checkout_buffer_lines
    layers["CHECKOUT_COUNTER"] = checkout_counter_lines
    layers["CHECKOUT_STAFF_BUFFER"] = checkout_staff_buffer_lines
    layers["FITTING_ROOMS"] = fitting_room_lines
    layers["LABELS"] = labels
    if isinstance(added, dict):
        display_area_m2 = float(added.get("display_area_m2", 0.0) or 0.0)
        added_rows = []
        for item in added.get("zones", []):
            area = float(item.get("actual_area_m2", 0.0) or 0.0)
            share = (area / display_area_m2 * 100.0) if display_area_m2 > 0 else 0.0
            added_rows.append({
                "key": str(item.get("key", "")),
                "label": str(item.get("label", "")),
                "area_m2": round(area, 3),
                "share_pct": round(share, 2),
            })
        added["report_meta"] = {
            "added_zone_rows": added_rows,
            "removed_fixture_ids": [f"{fam}-{idx}" for fam, idx in sorted(removed_fixture_ids, key=lambda t: (str(t[0]), int(t[1])) )],
            "removed_fixture_count": len(removed_fixture_ids),
            "total_added_area_m2": round(sum(r["area_m2"] for r in added_rows), 3),
            "total_added_share_pct": round(sum(r["share_pct"] for r in added_rows), 2),
            "display_area_m2": round(display_area_m2, 3),
        }
    return layers


params = load_parameters()



# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Page 3 — Manual T-family relocation between display islands
# -----------------------------------------------------------------------------
def _p3_deepcopy_drawing(drawing: dict) -> dict:
    try:
        return json.loads(json.dumps(drawing if isinstance(drawing, dict) else {}))
    except Exception:
        return dict(drawing or {})


def _p3_display_islands_from_drawing(drawing: dict) -> list[dict]:
    islands = []
    if not isinstance(drawing, dict):
        return islands
    for key in [f"D{i}" for i in range(1, 13)]:
        layer = drawing.get(f"DISPLAY_{key}", []) or []
        for idx, obj in enumerate(layer, start=1):
            if isinstance(obj, dict) and obj.get("shape") == "rect":
                islands.append({
                    "id": f"{key}-{idx}",
                    "key": key,
                    "index": idx,
                    "x": float(obj.get("x", 0.0)),
                    "y": float(obj.get("y", 0.0)),
                    "length": float(obj.get("length", 0.0)),
                    "width": float(obj.get("width", 0.0)),
                })
    return islands


def _p3_collect_t_instances(drawing: dict) -> list[dict]:
    out = []
    if not isinstance(drawing, dict):
        return out
    for i in range(1, 10):
        fam = f"T{i}"
        for obj in drawing.get(f"INTERACTIVE_{fam}", []) or []:
            if not (isinstance(obj, dict) and obj.get("shape") == "rect"):
                continue
            idx = int(obj.get("module_index", len(out) + 1) or 1)
            cx, cy = _center(obj)
            out.append({
                "id": f"{fam}-{idx}",
                "family": fam,
                "module_index": idx,
                "host_key": str(obj.get("host_key", "") or ""),
                "x": float(obj.get("x", 0.0)),
                "y": float(obj.get("y", 0.0)),
                "length": float(obj.get("length", 0.0)),
                "width": float(obj.get("width", 0.0)),
                "center_x": cx,
                "center_y": cy,
            })
    return out


def _p3_group_t_objects(drawing: dict, family: str, module_index: int) -> dict[str, list[dict]]:
    fam = str(family or "").upper().replace(" ", "")
    idx = int(module_index or 1)
    found = {"hard": [], "min": [], "soft": [], "labels": []}
    layer_map = {
        "hard": f"INTERACTIVE_{fam}",
        "min": f"INTERACTIVE_{fam}_BUFFER_MIN",
        "soft": f"INTERACTIVE_{fam}_BUFFER",
    }
    for bucket, lname in layer_map.items():
        for obj in drawing.get(lname, []) or []:
            if not isinstance(obj, dict):
                continue
            try:
                midx = int(obj.get("module_index", -1))
            except Exception:
                midx = -1
            ofam = str(obj.get("family", "") or fam).upper().replace(" ", "")
            if ofam == fam and midx == idx:
                found[bucket].append(obj)
    for obj in drawing.get("LABELS", []) or []:
        if not isinstance(obj, dict) or obj.get("shape") != "text":
            continue
        txt = str(obj.get("text", "") or "").upper().replace(" ", "")
        if txt in {f"{fam}-{idx}", f"{fam}{idx}"}:
            found["labels"].append(obj)
    return found


def _p3_move_obj(obj: dict, dx: float, dy: float) -> None:
    if obj.get("shape") == "rect":
        obj["x"] = float(obj.get("x", 0.0)) + dx
        obj["y"] = float(obj.get("y", 0.0)) + dy
    elif obj.get("shape") == "line":
        obj["x1"] = float(obj.get("x1", 0.0)) + dx
        obj["x2"] = float(obj.get("x2", 0.0)) + dx
        obj["y1"] = float(obj.get("y1", 0.0)) + dy
        obj["y2"] = float(obj.get("y2", 0.0)) + dy
    elif obj.get("shape") == "text":
        obj["x"] = float(obj.get("x", 0.0)) + dx
        obj["y"] = float(obj.get("y", 0.0)) + dy


def _p3_rect_inside(inner: dict, outer: dict, tol: float = 1e-6) -> bool:
    ix = float(inner.get("x", 0.0)); iy = float(inner.get("y", 0.0))
    il = float(inner.get("length", 0.0)); iw = float(inner.get("width", 0.0))
    ox = float(outer.get("x", 0.0)); oy = float(outer.get("y", 0.0))
    ol = float(outer.get("length", 0.0)); ow = float(outer.get("width", 0.0))
    return ix >= ox - tol and iy >= oy - tol and ix + il <= ox + ol + tol and iy + iw <= oy + ow + tol


def _p3_anchor_center(host: dict, hard: dict, anchor: str, margin: float = 0.05) -> tuple[float, float]:
    hx = float(host.get("x", 0.0)); hy = float(host.get("y", 0.0))
    hl = float(host.get("length", 0.0)); hw = float(host.get("width", 0.0))
    l = float(hard.get("length", 0.0)); w = float(hard.get("width", 0.0))
    cx = hx + hl / 2.0; cy = hy + hw / 2.0
    mx = l / 2.0 + margin; my = w / 2.0 + margin
    a = str(anchor or "Center")
    if "Left" in a:
        cx = hx + mx
    if "Right" in a:
        cx = hx + hl - mx
    if "Bottom" in a:
        cy = hy + my
    if "Top" in a:
        cy = hy + hw - my
    return min(max(cx, hx + mx), hx + hl - mx), min(max(cy, hy + my), hy + hw - my)


def _p3_hard_blockers(drawing: dict, family: str, module_index: int) -> list[dict]:
    fam = str(family or "").upper().replace(" ", "")
    idx = int(module_index or 1)
    blockers = []
    # Baseline display hard footprints remain protected.
    for lname in ["DISPLAY_WALL", "DISPLAY_GONDOLA", "DISPLAY_MANNEQUIN", "DISPLAY_TABLE"]:
        for obj in drawing.get(lname, []) or []:
            if isinstance(obj, dict) and obj.get("shape") == "rect":
                blockers.append(obj)
    # Other T-family hard footprints remain protected.
    for i in range(1, 10):
        lname = f"INTERACTIVE_T{i}"
        for obj in drawing.get(lname, []) or []:
            if not (isinstance(obj, dict) and obj.get("shape") == "rect"):
                continue
            ofam = str(obj.get("family", "") or f"T{i}").upper().replace(" ", "")
            try:
                midx = int(obj.get("module_index", -1))
            except Exception:
                midx = -1
            if ofam == fam and midx == idx:
                continue
            blockers.append(obj)
    return blockers


def _p3_point_inside_rect(px: float, py: float, rect: dict, tol: float = 1e-6) -> bool:
    return (
        px >= float(rect.get("x", 0.0)) - tol and
        py >= float(rect.get("y", 0.0)) - tol and
        px <= float(rect.get("x", 0.0)) + float(rect.get("length", 0.0)) + tol and
        py <= float(rect.get("y", 0.0)) + float(rect.get("width", 0.0)) + tol
    )


def _p3_find_target_island_by_center(drawing: dict, cx: float, cy: float, proposed_hard: dict | None = None) -> dict | None:
    """Find the display island under a proposed T-family center.

    This supports the Page 3 drag-style workflow: the user moves the device by X/Y
    position and the application automatically detects the host island instead of
    requiring a target-island list.
    """
    candidates = []
    for item in _p3_display_islands_from_drawing(drawing):
        if not _p3_point_inside_rect(cx, cy, item):
            continue
        if proposed_hard is not None and not _p3_rect_inside(proposed_hard, item):
            continue
        # Prefer D1/D2, then the smallest containing island.
        pri = 0 if item.get("key") in {"D1", "D2"} else 1
        area = float(item.get("length", 0.0)) * float(item.get("width", 0.0))
        candidates.append((pri, area, item))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]))
    return candidates[0][2]


def _p3_path_rects_from_drawing(drawing: dict) -> list[dict]:
    """Collect circulation-like rectangles from the drawing for F5 facing logic."""
    out = []
    for lname, objs in (drawing or {}).items():
        ln = str(lname).upper()
        if not any(tag in ln for tag in ["PATH", "AISLE", "SPINE", "CIRCULATION", "CONNECTOR"]):
            continue
        for obj in objs or []:
            if isinstance(obj, dict) and obj.get("shape") == "rect":
                out.append(obj)
    return out


def _p3_refill_d1_empty_spaces_with_f_families(drawing: dict) -> dict:
    """Fill empty D1 gaps after a T-family manual move using F6 then F5.

    This is intentionally a post-move recovery pass only. It does not rebuild the
    baseline model. It adds new F modules only where the current D1 geometry still
    has valid empty space, while respecting the buffer hierarchy:
    - no F hard footprint overlaps any existing hard footprint;
    - no F hard footprint enters T hard/min/soft buffers or existing F buffers;
    - new F browsing buffers may overlap circulation, but not hard footprints or T min buffers;
    - F5 buffer faces the nearest circulation side where circulation rectangles are available.
    """
    if not isinstance(drawing, dict):
        return drawing

    F6_L = F6_W = 1.20
    F6_BUF = 1.20
    F5_L, F5_W, F5_BUF = 1.00, 0.60, 1.20
    GRID = 0.10
    EPS = 1e-6

    def is_rect(o):
        return isinstance(o, dict) and o.get("shape") == "rect" and all(k in o for k in ("x", "y", "length", "width"))

    def host_contains(host, r):
        return (
            float(r["x"]) >= float(host["x"]) - EPS and
            float(r["y"]) >= float(host["y"]) - EPS and
            float(r["x"]) + float(r["length"]) <= float(host["x"]) + float(host["length"]) + EPS and
            float(r["y"]) + float(r["width"]) <= float(host["y"]) + float(host["width"]) + EPS
        )

    def axis_overlap(a0, a1, b0, b1):
        return max(0.0, min(a1, b1) - max(a0, b0))

    def buffer_rects(fam, r, sides):
        x = float(r["x"]); y = float(r["y"]); l = float(r["length"]); w = float(r["width"])
        buf = F6_BUF if fam == "F6" else F5_BUF
        out = []
        for s in sides:
            if s == "left": out.append({"x": x - buf, "y": y, "length": buf, "width": w})
            if s == "right": out.append({"x": x + l, "y": y, "length": buf, "width": w})
            if s == "bottom": out.append({"x": x, "y": y - buf, "length": l, "width": buf})
            if s == "top": out.append({"x": x, "y": y + w, "length": l, "width": buf})
        return out

    path_rects = _p3_path_rects_from_drawing(drawing)
    def nearest_side(r, allowed):
        x0 = float(r["x"]); y0 = float(r["y"])
        x1 = x0 + float(r["length"]); y1 = y0 + float(r["width"])
        cand = []
        for pr in path_rects:
            px0 = float(pr.get("x", 0.0)); py0 = float(pr.get("y", 0.0))
            px1 = px0 + float(pr.get("length", 0.0)); py1 = py0 + float(pr.get("width", 0.0))
            vo = axis_overlap(y0, y1, py0, py1); ho = axis_overlap(x0, x1, px0, px1)
            if "left" in allowed and px1 <= x0 + EPS: cand.append((x0 - px1, 0 if vo > EPS else 1, "left"))
            if "right" in allowed and px0 >= x1 - EPS: cand.append((px0 - x1, 0 if vo > EPS else 1, "right"))
            if "bottom" in allowed and py1 <= y0 + EPS: cand.append((y0 - py1, 0 if ho > EPS else 1, "bottom"))
            if "top" in allowed and py0 >= y1 - EPS: cand.append((py0 - y1, 0 if ho > EPS else 1, "top"))
        if cand:
            cand.sort(key=lambda t: (t[0], t[1]))
            return cand[0][2]
        return allowed[0]

    hard_layers = ["DISPLAY_WALL", "DISPLAY_GONDOLA", "DISPLAY_MANNEQUIN", "DISPLAY_TABLE"] + [f"INTERACTIVE_T{i}" for i in range(1,10)]
    buffer_layers = ["DISPLAY_WALL_BUFFER", "DISPLAY_GONDOLA_BUFFER", "DISPLAY_MANNEQUIN_BUFFER", "DISPLAY_TABLE_BUFFER_MIN", "DISPLAY_TABLE_BUFFER"] + [f"INTERACTIVE_T{i}_BUFFER_MIN" for i in range(1,10)] + [f"INTERACTIVE_T{i}_BUFFER" for i in range(1,10)]
    tmin_layers = [f"INTERACTIVE_T{i}_BUFFER_MIN" for i in range(1,10)]

    existing_hard = [o for ln in hard_layers for o in (drawing.get(ln, []) or []) if is_rect(o)]
    existing_buffers = [o for ln in buffer_layers for o in (drawing.get(ln, []) or []) if is_rect(o)]
    t_min = [o for ln in tmin_layers for o in (drawing.get(ln, []) or []) if is_rect(o)]

    drawing.setdefault("DISPLAY_GONDOLA", [])
    drawing.setdefault("DISPLAY_GONDOLA_BUFFER", [])
    next_idx = 1
    for obj in drawing.get("DISPLAY_GONDOLA", []) + drawing.get("DISPLAY_GONDOLA_BUFFER", []):
        try:
            if str(obj.get("family", "")) in {"F4", "F5", "F6"}:
                next_idx = max(next_idx, int(obj.get("module_index", 0)) + 1)
        except Exception:
            pass

    def candidate_positions(host, l, w):
        hx = float(host["x"]); hy = float(host["y"]); hl = float(host["length"]); hw = float(host["width"])
        if hl + EPS < l or hw + EPS < w:
            return []
        nx = int((hl - l) / GRID) + 1
        ny = int((hw - w) / GRID) + 1
        pts = []
        for iy in range(max(1, ny)):
            for ix in range(max(1, nx)):
                pts.append((round(hx + ix * GRID, 6), round(hy + iy * GRID, 6)))
        pts.append((round(hx + hl - l, 6), round(hy + hw - w, 6)))
        return list(dict.fromkeys(pts))

    def valid(host, hard, bufs):
        if not host_contains(host, hard):
            return False
        if any(_rects_overlap(hard, r) for r in existing_hard):
            return False
        if any(_rects_overlap(hard, r) for r in existing_buffers):
            return False
        for br in bufs:
            if any(_rects_overlap(br, r) for r in existing_hard):
                return False
            if any(_rects_overlap(br, r) for r in t_min):
                return False
        return True

    def add_module(fam, hard, sides):
        nonlocal next_idx
        fixture = _rect_obj(hard, "display_gondola", family=fam, module_index=next_idx, graphic_class="rack", lineweight="heavy", post_move_recovery=True)
        drawing["DISPLAY_GONDOLA"].append(fixture)
        existing_hard.append(fixture)
        for br in buffer_rects(fam, hard, sides):
            buf = _rect_obj(br, "display_gondola_buffer", family=fam, module_index=next_idx, graphic_class="gondola_buffer", dash=True, lineweight="light", post_move_recovery=True)
            drawing["DISPLAY_GONDOLA_BUFFER"].append(buf)
            existing_buffers.append(buf)
        next_idx += 1

    d1_hosts = [it for it in _p3_display_islands_from_drawing(drawing) if it.get("key") == "D1"]
    for host in d1_hosts:
        # Fill with F6 first.
        placed = True
        while placed:
            placed = False
            for x, y in candidate_positions(host, F6_L, F6_W):
                hard = {"x": x, "y": y, "length": F6_L, "width": F6_W}
                near = nearest_side(hard, ["left", "right", "bottom", "top"])
                sides = ["left", "right"] if near in {"left", "right"} else ["bottom", "top"]
                bufs = buffer_rects("F6", hard, sides)
                if valid(host, hard, bufs):
                    add_module("F6", hard, sides)
                    placed = True
                    break
        # Then compact F5 residuals, facing circulation.
        placed = True
        while placed:
            placed = False
            for l, w, allowed in [(F5_W, F5_L, ["left", "right"]), (F5_L, F5_W, ["bottom", "top"] )]:
                found = None
                for x, y in candidate_positions(host, l, w):
                    hard = {"x": x, "y": y, "length": l, "width": w}
                    side = nearest_side(hard, allowed)
                    bufs = buffer_rects("F5", hard, [side])
                    if valid(host, hard, bufs):
                        found = (hard, [side])
                        break
                if found:
                    add_module("F5", found[0], found[1])
                    placed = True
                    break

    return drawing


def _p3_apply_drag_position(base_drawing: dict, move: dict) -> tuple[dict, str, bool]:
    """Move selected T-family to an exact X/Y centre, auto-detecting target island."""
    drawing = _p3_deepcopy_drawing(base_drawing)
    family = str(move.get("family", "") or "").upper()
    idx = int(move.get("module_index", 1) or 1)
    target_cx = float(move.get("center_x", 0.0))
    target_cy = float(move.get("center_y", 0.0))
    group = _p3_group_t_objects(drawing, family, idx)
    if not group.get("hard"):
        return drawing, f"Move refused: {family}-{idx} was not found in the selected output.", False
    hard = group["hard"][0]
    old_cx, old_cy = _center(hard)
    dx, dy = target_cx - old_cx, target_cy - old_cy
    proposed = dict(hard)
    proposed["x"] = float(proposed.get("x", 0.0)) + dx
    proposed["y"] = float(proposed.get("y", 0.0)) + dy
    target = _p3_find_target_island_by_center(drawing, target_cx, target_cy, proposed)
    if not target:
        return drawing, f"Move refused: {family}-{idx} is not fully inside a valid display island at this position.", False
    for blk in _p3_hard_blockers(drawing, family, idx):
        if _rects_overlap(proposed, blk):
            return drawing, f"Move refused: {family}-{idx} would overlap another hard footprint. Try a nearby position.", False
    for bucket in ["hard", "min", "soft", "labels"]:
        for obj in group.get(bucket, []) or []:
            _p3_move_obj(obj, dx, dy)
            if bucket in {"hard", "min", "soft"}:
                obj["host_key"] = target.get("key", "")
                obj["manual_moved"] = True
                obj["manual_target"] = target.get("id", "")
    drawing = _p3_refill_d1_empty_spaces_with_f_families(drawing)
    return drawing, f"Move applied: {family}-{idx} → {target.get('id', '')} at X={target_cx:.2f}, Y={target_cy:.2f}. D1 empty gaps refilled where rules allowed.", True


def _p3_apply_move(base_drawing: dict, move: dict) -> tuple[dict, str, bool]:
    drawing = _p3_deepcopy_drawing(base_drawing)
    family = str(move.get("family", "") or "").upper()
    idx = int(move.get("module_index", 1) or 1)
    target_id = str(move.get("target_id", "") or "")
    anchor = str(move.get("anchor", "Center") or "Center")
    islands = {item["id"]: item for item in _p3_display_islands_from_drawing(drawing)}
    target = islands.get(target_id)
    if not target:
        return drawing, f"Move refused: target island {target_id} was not found.", False
    group = _p3_group_t_objects(drawing, family, idx)
    if not group.get("hard"):
        return drawing, f"Move refused: {family}-{idx} was not found in the selected output.", False
    hard = group["hard"][0]
    old_cx, old_cy = _center(hard)
    new_cx, new_cy = _p3_anchor_center(target, hard, anchor)
    dx, dy = new_cx - old_cx, new_cy - old_cy
    proposed = dict(hard)
    proposed["x"] = float(proposed.get("x", 0.0)) + dx
    proposed["y"] = float(proposed.get("y", 0.0)) + dy
    if not _p3_rect_inside(proposed, target):
        return drawing, f"Move refused: {family}-{idx} hard footprint does not fit inside {target_id}.", False
    for blk in _p3_hard_blockers(drawing, family, idx):
        if _rects_overlap(proposed, blk):
            return drawing, f"Move refused: {family}-{idx} would overlap another hard footprint. Try another island/anchor.", False
    for bucket in ["hard", "min", "soft", "labels"]:
        for obj in group.get(bucket, []) or []:
            _p3_move_obj(obj, dx, dy)
            if bucket in {"hard", "min", "soft"}:
                obj["host_key"] = target.get("key", "")
                obj["manual_moved"] = True
                obj["manual_target"] = target_id
    return drawing, f"Move applied: {family}-{idx} → {target_id} ({anchor}).", True


def _p3_render_output(drawing: dict, prefix: str = "page3_manual_layout") -> None:
    svg_payload = build_svg_payload(drawing if isinstance(drawing, dict) else {}, params)
    canvas = svg_payload.get("canvas", {})
    canvas_w = float(canvas.get("width_px", 700.0) or 700.0)
    canvas_h = float(canvas.get("height_px", 500.0) or 500.0)
    preview_height = int(min(860, max(560, round(760 * (canvas_h / max(canvas_w, 1.0))))))
    preview_html = f"""
    <html><head><style>
    html, body {{ margin:0; padding:0; background:white; overflow:hidden; }}
    .preview-wrap {{ width:100%; height:{preview_height}px; display:flex; align-items:center; justify-content:center; background:white; }}
    .preview-wrap svg {{ width:100%; height:100%; display:block; }}
    </style></head><body><div class="preview-wrap">{svg_payload.get('svg_markup', '')}</div></body></html>
    """
    components.html(preview_html, height=preview_height, scrolling=False)
    c1, c2, c3 = st.columns(3)
    with c1:
        _download_button_export("Download SVG", data=svg_payload.get("svg_markup", "").encode("utf-8"), file_name=f"{prefix}.svg", mime="image/svg+xml", use_container_width=True)
    with c2:
        png_bytes = render_png_bytes(drawing if isinstance(drawing, dict) else {}, params=params, output_width_px=2400)
        _download_button_export("Download PNG", data=png_bytes, file_name=f"{prefix}.png", mime="image/png", use_container_width=True)
    with c3:
        dxf_bytes = render_dxf_bytes(drawing if isinstance(drawing, dict) else {}, params={})
        _download_button_export("Download DXF", data=dxf_bytes, file_name=f"{prefix}.dxf", mime="application/dxf", use_container_width=True)


def _run_manual_t_move_page() -> None:
    st.title("Manual Device Adjustment")
    st.caption("Adjust interactive-device locations after layout generation. This workspace uses a controlled X/Y movement system, auto-detects the target display island, refuses invalid drops, and refills D1 gaps with F-families where rules allow.")

    sources = []
    if isinstance(st.session_state.get("page1_output_drawing"), dict):
        sources.append("Layout Generator output")
    if isinstance(st.session_state.get("page2_output_drawing"), dict):
        sources.append("Footprint Calculator output")
    if not sources:
        st.warning("No generated output is available yet. Generate a layout in Layout Generator or run the Footprint Calculator first, then return to Manual Device Adjustment.")
        return

    source_label = st.radio("Source Layout", sources, horizontal=False, key="p3_source_label")
    source_key = "page1_output_drawing" if source_label == "Layout Generator output" else "page2_output_drawing"
    base = st.session_state.get(source_key, {})
    # Reset the manual working copy when the source changes or when user asks.
    if st.session_state.get("p3_active_source_key") != source_key or not isinstance(st.session_state.get("p3_working_drawing"), dict):
        st.session_state["p3_active_source_key"] = source_key
        st.session_state["p3_working_drawing"] = _p3_deepcopy_drawing(base)
        st.session_state["p3_move_log"] = []

    left, right = st.columns([1.15, 0.85])
    with right:
        st.subheader("Move Interactive Device")
        if st.button("Reset to Selected Output", use_container_width=True, key="p3_reset_btn"):
            st.session_state["p3_working_drawing"] = _p3_deepcopy_drawing(base)
            st.session_state["p3_move_log"] = []
            st.rerun()

        drawing = st.session_state.get("p3_working_drawing", {})
        instances = _p3_collect_t_instances(drawing)
        islands = _p3_display_islands_from_drawing(drawing)
        if not instances:
            st.info("No interactive-device instances are available in this output.")
        elif not islands:
            st.info("No display islands were found in this output.")
        else:
            inst_options = [it["id"] for it in instances]
            inst_id = st.selectbox("Select Interactive Device to Move", inst_options, key="p3_instance_select")
            selected = next((it for it in instances if it["id"] == inst_id), None)
            if selected:
                st.caption(f"Selected: {selected['id']} | Current host: {selected.get('host_key', '')} | Size: {selected['length']:.2f} × {selected['width']:.2f} m")
                all_x0 = min(float(it["x"]) for it in islands)
                all_y0 = min(float(it["y"]) for it in islands)
                all_x1 = max(float(it["x"]) + float(it["length"]) for it in islands)
                all_y1 = max(float(it["y"]) + float(it["width"]) for it in islands)
                min_cx = round(all_x0 + selected["length"] / 2.0, 2)
                max_cx = round(all_x1 - selected["length"] / 2.0, 2)
                min_cy = round(all_y0 + selected["width"] / 2.0, 2)
                max_cy = round(all_y1 - selected["width"] / 2.0, 2)
                default_x = round(min(max(float(selected["center_x"]), min_cx), max_cx), 2)
                default_y = round(min(max(float(selected["center_y"]), min_cy), max_cy), 2)
                st.markdown("#### Controlled Position")
                st.caption("Use X/Y controls to move the device. The application auto-detects the island under the device and refuses invalid drops.")
                cx = st.slider("X Position (m)", min_value=float(min_cx), max_value=float(max_cx), value=float(default_x), step=0.10, key=f"p3_drag_x_{inst_id}")
                cy = st.slider("Y Position (m)", min_value=float(min_cy), max_value=float(max_cy), value=float(default_y), step=0.10, key=f"p3_drag_y_{inst_id}")
                proposed = {"x": cx - selected["length"] / 2.0, "y": cy - selected["width"] / 2.0, "length": selected["length"], "width": selected["width"]}
                detected = _p3_find_target_island_by_center(drawing, cx, cy, proposed)
                if detected:
                    st.caption(f"Detected target island: {detected['id']}")
                else:
                    st.caption("Detected target island: none / invalid")
                if st.button("Apply Device Move + Refill D1 Gaps", type="primary", use_container_width=True, key="p3_apply_drag_btn"):
                    fam, midx = inst_id.split("-", 1)
                    new_drawing, msg, ok = _p3_apply_drag_position(drawing, {"family": fam, "module_index": int(midx), "center_x": cx, "center_y": cy})
                    st.session_state["p3_working_drawing"] = new_drawing
                    log = list(st.session_state.get("p3_move_log", []))
                    log.append(msg)
                    st.session_state["p3_move_log"] = log[-10:]
                    if ok:
                        st.success(msg)
                    else:
                        st.warning(msg)
                    st.rerun()

            with st.expander("Advanced fallback: island / anchor placement"):
                target_options = [it["id"] for it in islands]
                target_id = st.selectbox("Target Display Island", target_options, key="p3_target_select")
                anchor = st.selectbox("Placement Anchor", ["Center", "Top Left", "Top Center", "Top Right", "Middle Left", "Middle Right", "Bottom Left", "Bottom Center", "Bottom Right"], index=0, key="p3_anchor_select")
                if st.button("Apply Anchor Placement + Refill D1 Gaps", use_container_width=True, key="p3_apply_move_btn"):
                    fam, midx = inst_id.split("-", 1)
                    new_drawing, msg, ok = _p3_apply_move(drawing, {"family": fam, "module_index": int(midx), "target_id": target_id, "anchor": anchor})
                    if ok:
                        new_drawing = _p3_refill_d1_empty_spaces_with_f_families(new_drawing)
                        msg += " D1 empty gaps refilled where rules allowed."
                    st.session_state["p3_working_drawing"] = new_drawing
                    log = list(st.session_state.get("p3_move_log", []))
                    log.append(msg)
                    st.session_state["p3_move_log"] = log[-10:]
                    if ok:
                        st.success(msg)
                    else:
                        st.warning(msg)
                    st.rerun()

        if st.session_state.get("p3_move_log"):
            st.markdown("### Adjustment Log")
            for item in reversed(st.session_state.get("p3_move_log", [])):
                st.caption(item)

    with left:
        st.subheader("Adjustment Preview")
        _p3_render_output(st.session_state.get("p3_working_drawing", {}), prefix="manual_tfamily_move_plan")


# Page 2 — Minimum Footprint from T-Family Counts
# Reverse direction: required interactive devices -> minimum feasible store shell.
# This page is intentionally isolated from Page 1 so the existing generator logic
# remains unchanged. It reuses the same zoning, circulation, display, T-family
# insertion, buffer, and drawing logic, then searches upward from W=4m and D=8m.
# -----------------------------------------------------------------------------
def _count_interactive_from_drawing(_drawing: dict) -> dict:
    counts = {f"T{i}": 0 for i in range(1, 10)}
    if not isinstance(_drawing, dict):
        return counts
    for i in range(1, 10):
        counts[f"T{i}"] = len([o for o in (_drawing.get(f"INTERACTIVE_T{i}", []) or []) if isinstance(o, dict)])
    return counts



def _page2_report_pdf_bytes(best: dict, program_intent: str = "Balanced") -> bytes:
    """Build the same PDF report payload used by Page 1, but from Page 2 result objects.

    This function is intentionally read-only: it does not alter generation, zoning,
    circulation, F-family, T-family, density, or buffer logic.
    """
    drawing_layers = best.get("drawing", {}) if isinstance(best, dict) else {}
    if not isinstance(drawing_layers, dict):
        drawing_layers = {}

    fixture_items = []
    for layer_name in ["DISPLAY_WALL", "DISPLAY_GONDOLA", "DISPLAY_MANNEQUIN", "DISPLAY_TABLE"]:
        for obj in (drawing_layers.get(layer_name, []) or []):
            if isinstance(obj, dict):
                fixture_items.append(dict(obj))

    def _page2_infer_f_family(obj):
        fam_raw = str(obj.get("family", "") or "").strip().upper()
        if fam_raw.startswith("F7"):
            return "F7"
        if fam_raw in {f"F{i}" for i in range(1, 9)}:
            return fam_raw
        variant = str(obj.get("variant", "") or "").strip().lower()
        subfamily = str(obj.get("subfamily", "") or "").strip().lower()
        length = float(obj.get("length", 0.0) or 0.0)
        width = float(obj.get("width", 0.0) or 0.0)
        depth = min(length, width) if length and width else 0.0
        if fam_raw == "WALL_BAYS":
            if variant == "shirts_wall_bay":
                return "F1"
            if variant == "coats_wall_bay":
                return "F2"
            if variant in {"folded_apparel_wall_bay", "freestanding_wall_bay"}:
                return "F3"
            if depth <= 0.35 + 1e-6:
                return "F1"
            if depth <= 0.45 + 1e-6:
                return "F2"
            return "F3"
        if fam_raw == "GONDOLA_RACK_SYSTEM":
            if variant == "double_sided_gondola":
                return "F4"
            if variant in {"single_sided_gondola", "shirts_straight_rack", "coats_straight_rack"}:
                return "F5"
            if variant == "two_way_rack":
                return "F6"
            if subfamily == "rack":
                return "F5"
            if subfamily == "gondola":
                return "F4" if max(length, width) >= 1.0 and min(length, width) >= 0.9 else "F5"
        if fam_raw == "TABLES":
            return "F8"
        if fam_raw == "MANNEQUINS":
            return "F7"
        return fam_raw

    fixture_counts = {f"F{i}": 0 for i in range(1, 9)}
    for obj in fixture_items:
        fam = _page2_infer_f_family(obj)
        if fam in fixture_counts:
            fixture_counts[fam] += 1

    interactive_items = []
    for i in range(1, 10):
        layer_name = f"INTERACTIVE_T{i}"
        for obj in (drawing_layers.get(layer_name, []) or []):
            if isinstance(obj, dict):
                cp = dict(obj)
                cp.setdefault("family", f"T{i}")
                interactive_items.append(cp)
    interactive_counts = _count_interactive_from_drawing(drawing_layers)

    payload = build_zone_ratio_report_payload(
        shell=best.get("shell", {}),
        zoning=best.get("zoning", {}),
        store_band=best.get("store_band", ""),
        program_intent_ui=program_intent,
        added=None,
        display_classes=best.get("display_classes", None),
        fixture_lists={
            "display_wall": list((drawing_layers.get("DISPLAY_WALL", []) or [])),
            "display_gondola": list((drawing_layers.get("DISPLAY_GONDOLA", []) or [])),
            "display_mannequin": list((drawing_layers.get("DISPLAY_MANNEQUIN", []) or [])),
            "display_table": list((drawing_layers.get("DISPLAY_TABLE", []) or [])),
        },
        fixture_items=fixture_items,
        fixture_counts=fixture_counts,
        interactive_items=interactive_items,
        interactive_counts=interactive_counts,
        preview_drawing_layers=drawing_layers,
    )
    return render_zone_ratio_report_pdf(payload)

def _minfoot_auto_spacing(store_band: str, program_intent: str) -> float:
    """Automatic horizontal spacing used only during Page 2 minimum-footprint search.

    Page 2 must find the smallest feasible footprint using engine-selected
    circulation parameters. Manual spacing/sliders are applied only after the
    footprint has been found, as an optional refinement feature.
    """
    band = str(store_band or "").lower()
    intent = str(program_intent or "Balanced").lower()
    if band in ("micro", "small"):
        base = 2.00
    elif band in ("normal", "medium"):
        base = 2.50
    else:
        base = 3.00
    if "sales" in intent:
        base -= 0.10
    elif "service" in intent or "fitting" in intent:
        base += 0.10
    return max(1.50, min(3.60, round(base, 2)))


def _minfoot_build_candidate(
    width_m: float,
    depth_m: float,
    requested_counts: dict,
    requested_dims: dict | None = None,
    entrance_position: str = "Center",
    program_intent: str = "Balanced",
    fitting_side: str = "Left",
    fitting_layout_mode: str = "Attached fitting rooms",
    recommended_spacing_m: float | None = None,
    user_spine_width_m: float | None = None,
    enable_d7_display: bool = False,
    enable_d8_display: bool = True,
    enable_d11_display: bool = False,
) -> dict:
    """Build one candidate using the exact existing application pipeline.

    The returned feasibility is based on actual objects drawn in the final layers,
    not on an independent simplified estimate. Therefore it follows the same
    placement, buffer, overlap, and anchoring behavior as Page 1.
    """
    area_m2 = float(width_m) * float(depth_m)
    normalized_inputs = _normalize_inputs("Length × Width", area_m2, float(depth_m), float(width_m), entrance_position)
    shell_validation = validate_step1_inputs(normalized_inputs, params)
    if not shell_validation.get("is_valid", False):
        return {"ok": False, "reason": "invalid shell", "counts": {f"T{i}": 0 for i in range(1, 10)}}

    store_band = classify_store_band(area_m2)
    intent_map = {"Balanced": "balanced", "Sales-first": "sales_first", "Fitting-first": "fitting_first", "Service-first": "service_first"}
    try:
        shell = generate_store_shell(normalized_inputs, params)
        zoning = build_zoning(shell, fitting_side=fitting_side.lower(), program_intent=intent_map.get(program_intent, "balanced"))
        zval = validate_zoning(shell, zoning)
        if not zval.get("is_valid", False):
            return {"ok": False, "reason": "invalid zoning", "counts": {f"T{i}": 0 for i in range(1, 10)}}

        spine_width = float(user_spine_width_m) if user_spine_width_m is not None else _computed_spine_width(store_band, program_intent)
        spacing_width = float(recommended_spacing_m) if recommended_spacing_m is not None else _minfoot_auto_spacing(store_band, program_intent)
        circulation = build_circulation(
            shell,
            zoning,
            recommended_spacing_m=float(spacing_width),
            user_spine_width_m=float(spine_width),
            left_territory_mode="Double Gondola",
            right_territory_mode="Double Gondola",
        )
        cval = validate_circulation(shell, zoning, circulation)
        if not cval.get("is_valid", False):
            return {"ok": False, "reason": "invalid circulation", "counts": {f"T{i}": 0 for i in range(1, 10)}}

        frontage = build_frontage_zones(shell, zoning, circulation)
        display_classes = build_display_classification(shell, zoning, circulation, frontage)
        fit_mode = "attached" if fitting_layout_mode == "Attached fitting rooms" else "separated"
        fitting_rooms = _generate_fitting_rooms(zoning, fitting_side.lower(), area_m2, circulation, layout_mode=fit_mode)

        dims = requested_dims or {}
        def _dim(t_key, axis, default):
            try:
                return float((dims.get(t_key, {}) or {}).get(axis, default))
            except Exception:
                return float(default)

        drawing = _build_drawing(
            shell, zoning, None, circulation, frontage, display_classes,
            fitting_rooms=fitting_rooms,
            enable_d7_display=bool(enable_d7_display),
            enable_d8_display=bool(enable_d8_display),
            enable_d11_display=bool(enable_d11_display),
            t1_enabled=int(requested_counts.get("T1", 0)) > 0, t1_count=int(requested_counts.get("T1", 0)), t1_width_m=_dim("T1", "w", 0.60), t1_depth_m=_dim("T1", "d", 0.30),
            t2_enabled=int(requested_counts.get("T2", 0)) > 0, t2_count=int(requested_counts.get("T2", 0)), t2_width_m=_dim("T2", "w", 0.60), t2_depth_m=_dim("T2", "d", 0.60),
            t3_enabled=int(requested_counts.get("T3", 0)) > 0, t3_count=int(requested_counts.get("T3", 0)), t3_width_m=_dim("T3", "w", 0.60), t3_depth_m=_dim("T3", "d", 0.30),
            t4_enabled=int(requested_counts.get("T4", 0)) > 0, t4_count=int(requested_counts.get("T4", 0)), t4_width_m=_dim("T4", "w", 0.80), t4_depth_m=_dim("T4", "d", 0.60),
            t5_enabled=int(requested_counts.get("T5", 0)) > 0, t5_count=int(requested_counts.get("T5", 0)), t5_width_m=_dim("T5", "w", 1.50), t5_depth_m=_dim("T5", "d", 1.50),
            t6_enabled=int(requested_counts.get("T6", 0)) > 0, t6_count=int(requested_counts.get("T6", 0)), t6_width_m=_dim("T6", "w", 0.80), t6_depth_m=_dim("T6", "d", 0.80),
            t7_enabled=int(requested_counts.get("T7", 0)) > 0, t7_count=int(requested_counts.get("T7", 0)), t7_width_m=_dim("T7", "w", 1.20), t7_depth_m=_dim("T7", "d", 1.20),
            t8_enabled=int(requested_counts.get("T8", 0)) > 0, t8_count=int(requested_counts.get("T8", 0)), t8_width_m=_dim("T8", "w", 0.60), t8_depth_m=_dim("T8", "d", 0.30),
            t9_enabled=int(requested_counts.get("T9", 0)) > 0, t9_count=int(requested_counts.get("T9", 0)), t9_width_m=_dim("T9", "w", 1.20), t9_depth_m=_dim("T9", "d", 0.60),
        )
        placed_counts = _count_interactive_from_drawing(drawing)
        ok = all(int(placed_counts.get(k, 0)) >= int(v or 0) for k, v in requested_counts.items())
        return {
            "ok": bool(ok),
            "reason": "feasible" if ok else "not all requested T-families placed",
            "width": float(width_m),
            "depth": float(depth_m),
            "area": float(area_m2),
            "store_band": store_band,
            "shell": shell,
            "zoning": zoning,
            "circulation": circulation,
            "frontage": frontage,
            "display_classes": display_classes,
            "fitting_rooms": fitting_rooms,
            "used_spine_width_m": float(spine_width),
            "used_spacing_m": float(spacing_width),
            "drawing": drawing,
            "counts": placed_counts,
        }
    except Exception as exc:
        return {"ok": False, "reason": f"error: {exc}", "counts": {f"T{i}": 0 for i in range(1, 10)}}


def _run_minimum_footprint_page():
    st.title("Minimum Footprint Calculator")
    st.caption("Reverse computation: enter the required interactive-device counts, then the application searches upward from width 4 m and depth 8 m using the same layout, anchoring, buffer, and insertion logic as the layout generator.")

    # Hidden fixed search constants: requested by user to remove the search-range UI.
    min_width = 4.00
    min_depth = 8.00
    max_width = 24.00
    max_depth = 36.00
    search_step = 0.50

    # Page 2 store parameters are placed in the left sidebar exactly like Page 1.
    # The reverse search range remains hidden/fixed internally.
    with st.sidebar:
        if st.button("Reset Footprint Calculator", type="secondary", use_container_width=True, key="minfoot_reset_btn"):
            _page2_reset_prefixes = ("minfoot_",)
            _page2_reset_keys = [
                "minfoot_result",
                "page2_output_drawing",
                "page2_last_source",
            ]
            _page2_reset_keys += [k for k in list(st.session_state.keys()) if isinstance(k, str) and k.startswith(_page2_reset_prefixes)]
            for _k in sorted(set(_page2_reset_keys)):
                if _k != "minfoot_reset_btn":
                    st.session_state.pop(_k, None)
            st.rerun()

        st.header("Store Geometry")
        st.caption("Reverse search: frontage starts at 4.00 m and depth starts at 8.00 m.")
        entrance_position = st.radio("Entrance Location", ["Left", "Center", "Right"], index=1, horizontal=True, key="minfoot_entrance")

        st.markdown("#### Planning Strategy & Circulation")
        st.caption("Set the planning priority. The engine automatically selects the primary spine width and secondary circulation spacing during the minimum-footprint search.")
        program_intent = st.selectbox(
            "Planning Priority",
            ["Balanced", "Sales-first", "Fitting-first", "Service-first"],
            index=0,
            key="minfoot_program",
            format_func=lambda x: {"Balanced": "Balanced", "Sales-first": "Display-priority", "Fitting-first": "Fitting-priority", "Service-first": "Service-priority"}.get(x, x),
        )
        st.info("Automatic search mode: primary spine width and secondary circulation spacing are selected by the engine during **Calculate Minimum Footprint**. After a footprint is found, they can be adjusted as optional post-generation controls.")
        fitting_side = st.radio("Fitting Suite Side", ["Left", "Right"], index=0, horizontal=True, key="minfoot_fitting_side")
        fitting_layout_mode = st.selectbox("Fitting Room Arrangement", ["Attached fitting rooms", "Separated fitting rooms"], index=0, key="minfoot_fit_mode")

        st.header("Display Fixture Controls")
        enable_d7_display = st.checkbox("Fitting-side Display (D7)", value=False, key="minfoot_d7")
        enable_d8_display = st.checkbox("Checkout-side Display (D8)", value=False, key="minfoot_d8")
        enable_d11_display = st.checkbox("Frontage Mannequin Display (D11/F7)", value=False, key="minfoot_d11")

    # Page 2 main area: results / demand summary on the left, T-Family controls on the right.
    col1, col2 = st.columns([0.95, 1.05], gap="large")

    with col2:
        st.markdown('<h2 style="color:#0f172a !important;-webkit-text-fill-color:#0f172a !important;">Technology Families</h2>', unsafe_allow_html=True)
        st.header("Interactive Device Controls")
        st.caption("These device counts and dimensions are used as spatial demand to find the smallest feasible store footprint.")

        requested_counts = {f"T{i}": 0 for i in range(1, 10)}
        requested_dims = {
            "T1": {"w": 0.60, "d": 0.30}, "T2": {"w": 0.60, "d": 0.60},
            "T3": {"w": 0.60, "d": 0.30}, "T4": {"w": 0.80, "d": 0.60},
            "T5": {"w": 1.50, "d": 1.50}, "T6": {"w": 0.80, "d": 0.80},
            "T7": {"w": 1.20, "d": 1.20}, "T8": {"w": 0.60, "d": 0.30},
            "T9": {"w": 1.20, "d": 0.60},
        }

        def _minfoot_t_control(t_key, title, caption, default_w, default_d, min_w, min_d, fixed=False):
            with st.expander(title, expanded=False):
                enabled = st.checkbox("Use Device", value=False, key=f"minfoot_{t_key.lower()}_enabled_ui")
                st.caption(caption)
                if enabled:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        requested_counts[t_key] = int(st.number_input("Required Count", min_value=1, max_value=20, value=1, step=1, key=f"minfoot_{t_key.lower()}_count_ui"))
                    with c2:
                        if fixed:
                            st.number_input("W (m)", min_value=float(default_w), max_value=float(default_w), value=float(default_w), step=0.10, format="%.2f", key=f"minfoot_{t_key.lower()}_width_ui", disabled=True)
                            requested_dims[t_key]["w"] = float(default_w)
                        else:
                            requested_dims[t_key]["w"] = float(st.number_input("W (m)", min_value=float(min_w), value=float(default_w), step=0.10, format="%.2f", key=f"minfoot_{t_key.lower()}_width_ui"))
                    with c3:
                        if fixed:
                            st.number_input("D (m)", min_value=float(default_d), max_value=float(default_d), value=float(default_d), step=0.10, format="%.2f", key=f"minfoot_{t_key.lower()}_depth_ui", disabled=True)
                            requested_dims[t_key]["d"] = float(default_d)
                        else:
                            requested_dims[t_key]["d"] = float(st.number_input("D (m)", min_value=float(min_d), value=float(default_d), step=0.10, format="%.2f", key=f"minfoot_{t_key.lower()}_depth_ui"))
                else:
                    st.caption("Not selected")

        _minfoot_t_control("T1", "T1 — Interactive Screen", "Priority: D6 → D5 | Recommended: W = 0.60 m, D = 0.30 m | Side soft = 0.50 m", 0.60, 0.30, 0.30, 0.10)
        _minfoot_t_control("T2", "T2 — Interactive Kiosk", "Priority: D1 → D2 | Recommended: W = 0.60 m, D = 0.60 m | Color = Green", 0.60, 0.60, 0.30, 0.10)
        _minfoot_t_control("T3", "T3 — Smart / Magic Mirror", "Priority: Fitting Area Buffer top boundary | Recommended: W = 0.60 m, D = 0.30 m | Color = Blue", 0.60, 0.30, 0.30, 0.10)
        _minfoot_t_control("T4", "T4 — Free-standing Smart / Magic Mirror", "Priority: D1 near Fitting Suite only | Recommended: W = 0.80 m, D = 0.60 m | Color = Green", 0.80, 0.60, 0.30, 0.10)
        _minfoot_t_control("T6", "T6 — Seated VR Station", "Priority: D1 → D2 | Recommended: W = 0.80 m, D = 0.80 m | Color = Cyan", 0.80, 0.80, 0.40, 0.40)
        _minfoot_t_control("T7", "T7 — Standing VR Station", "Priority: D1 → D2 | Recommended: W = 1.20 m, D = 1.20 m | Color = Purple", 1.20, 1.20, 0.60, 0.60)
        _minfoot_t_control("T8", "T8 — Express Checkout", "Priority: Checkout boundary only | Side offset = 0.60 m | Front soft = 2.40 m | Front min = 1.20 m", 0.60, 0.30, 0.40, 0.30)
        _minfoot_t_control("T9", "T9 — Fixed Self Checkout", "Host priority: D1 beside Checkout → D2 | Hard / minimum / soft buffers follow T8", 1.20, 0.60, 0.40, 0.30)
        _minfoot_t_control("T5", "T5 — 3D Body Scanner", "Copy of T3 behavior | Fixed hard footprint: W = 1.50 m, D = 1.50 m | Color = Magenta", 1.50, 1.50, 1.50, 1.50, fixed=True)

        run_search = st.button("Calculate Minimum Footprint", type="primary", use_container_width=True, key="minfoot_find_btn")

    with col1:
        st.subheader("Footprint Calculation Setup")
        st.markdown("#### Store Parameters")
        st.caption("Store parameters are controlled from the left sidebar. Interactive-device demand remains on the right.")

        if sum(int(v or 0) for v in requested_counts.values()) <= 0:
            st.info("Enter at least one interactive-device count on the right side to start the reverse footprint calculation.")
            return

        st.markdown("### Requested Interactive-Device Demand")
        st.table([{
            "Device family": k,
            "Required count": v,
            "W × D (m)": f"{requested_dims.get(k, {}).get('w', 0):.2f} × {requested_dims.get(k, {}).get('d', 0):.2f}",
        } for k, v in requested_counts.items() if int(v or 0) > 0])

        if not run_search and "minfoot_result" not in st.session_state:
            st.info("Press **Calculate Minimum Footprint** to search for the smallest feasible frontage × depth.")
            return

        if run_search:
            widths = []
            w = float(min_width)
            while w <= float(max_width) + 1e-6:
                widths.append(round(w, 3)); w += float(search_step)
            depths = []
            d = float(min_depth)
            while d <= float(max_depth) + 1e-6:
                depths.append(round(d, 3)); d += float(search_step)
            candidates = sorted([(w, d, w*d) for w in widths for d in depths], key=lambda x: (x[2], x[1], x[0]))
            progress = st.progress(0, text="Testing candidate store footprints...")
            best = None
            tested = 0
            last_reason = "No candidate tested."
            for idx, (w, d, _a) in enumerate(candidates):
                result = _minfoot_build_candidate(
                    w, d, requested_counts, requested_dims,
                    entrance_position=entrance_position,
                    program_intent=program_intent,
                    fitting_side=fitting_side,
                    fitting_layout_mode=fitting_layout_mode,
                    recommended_spacing_m=None,
                    user_spine_width_m=None,
                    enable_d7_display=enable_d7_display,
                    enable_d8_display=enable_d8_display,
                    enable_d11_display=enable_d11_display,
                )
                tested += 1
                last_reason = result.get("reason", "not feasible")
                if idx % 10 == 0 or idx == len(candidates)-1:
                    progress.progress(min(1.0, (idx + 1) / max(1, len(candidates))), text=f"Testing {w:.2f} × {d:.2f} m")
                if result.get("ok"):
                    best = result
                    break
            progress.empty()
            st.session_state["minfoot_result"] = {"best": best, "tested": tested, "last_reason": last_reason, "requested_counts": dict(requested_counts), "requested_dims": dict(requested_dims)}

        saved = st.session_state.get("minfoot_result", {})
        best = saved.get("best")
        tested = saved.get("tested", 0)
        if not best:
            st.error(f"No feasible footprint found within the tested range. Tested candidates: {tested}. Last status: {saved.get('last_reason', 'not feasible')}.")
            st.caption("Reduce requested counts or enable D7/D8 fallback displays if relevant.")
            return

        st.success(f"Minimum feasible footprint found: {best['width']:.2f} m × {best['depth']:.2f} m = {best['area']:.2f} m²")
        st.caption(f"Auto-selected during search: Main spine = {float(best.get('used_spine_width_m', 0.0)):.2f} m; horizontal spacing = {float(best.get('used_spacing_m', 0.0)):.2f} m.")

        with st.expander("Optional post-generation circulation controls", expanded=False):
            st.caption("These sliders do not control the automated minimum-footprint search. They only rebuild the already-found footprint as an optional refinement feature.")
            adj_c1, adj_c2 = st.columns(2)
            with adj_c1:
                post_spine_width_ui = st.slider(
                    "Primary Spine Width (m)",
                    min_value=0.90, max_value=2.40,
                    value=float(best.get('used_spine_width_m', _computed_spine_width(best.get('store_band', ''), program_intent))),
                    step=0.05, key="minfoot_post_spine_width_slider",
                )
            with adj_c2:
                post_spacing_ui = st.slider(
                    "Secondary Circulation Spacing (m)",
                    min_value=1.50, max_value=3.60,
                    value=float(best.get('used_spacing_m', _minfoot_auto_spacing(best.get('store_band', ''), program_intent))),
                    step=0.10, key="minfoot_post_spacing_slider",
                )
            if st.button("Apply post-generation circulation adjustment", use_container_width=True, key="minfoot_apply_post_circ"):
                adjusted = _minfoot_build_candidate(
                    best['width'], best['depth'], saved.get('requested_counts', {}), saved.get('requested_dims', {}),
                    entrance_position=entrance_position, program_intent=program_intent, fitting_side=fitting_side,
                    fitting_layout_mode=fitting_layout_mode, recommended_spacing_m=post_spacing_ui, user_spine_width_m=post_spine_width_ui,
                    enable_d7_display=enable_d7_display, enable_d8_display=enable_d8_display, enable_d11_display=enable_d11_display,
                )
                if adjusted.get('ok'):
                    st.session_state["minfoot_result"]["best"] = adjusted
                    best = adjusted
                    st.success("Post-generation circulation adjustment applied to the found footprint.")
                else:
                    st.warning(f"Adjustment not applied because the requested T-family demand no longer fits: {adjusted.get('reason', 'not feasible')}.")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Width", f"{best['width']:.2f} m")
        m2.metric("Depth", f"{best['depth']:.2f} m")
        m3.metric("Area", f"{best['area']:.2f} m²")
        m4.metric("Store band", str(best.get("store_band", "")).upper())

        placed_counts = best.get("counts", {})
        st.markdown("### Requested vs. placed T-families")
        st.table([
            {"T-family": fam, "Requested": int(saved.get("requested_counts", {}).get(fam, 0)), "Placed": int(placed_counts.get(fam, 0)), "Status": "OK" if int(placed_counts.get(fam, 0)) >= int(saved.get("requested_counts", {}).get(fam, 0)) else "Short"}
            for fam in ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9"]
            if int(saved.get("requested_counts", {}).get(fam, 0)) > 0
        ])

        drawing = best.get("drawing", {})
        if isinstance(drawing, dict):
            st.session_state["page2_output_drawing"] = _p3_deepcopy_drawing(drawing)
        svg_payload = build_svg_payload(drawing if isinstance(drawing, dict) else {}, params)
        canvas = svg_payload.get("canvas", {})
        canvas_w = float(canvas.get("width_px", 700.0) or 700.0)
        canvas_h = float(canvas.get("height_px", 500.0) or 500.0)
        preview_height = int(min(860, max(520, round(760 * (canvas_h / max(canvas_w, 1.0))))))
        preview_html = f"""
        <html><head><style>
        html, body {{ margin:0; padding:0; background:white; overflow:hidden; }}
        .preview-wrap {{ width:100%; height:{preview_height}px; display:flex; align-items:center; justify-content:center; background:white; }}
        .preview-wrap svg {{ width:100%; height:100%; display:block; }}
        </style></head><body><div class="preview-wrap">{svg_payload.get('svg_markup', '')}</div></body></html>
        """
        components.html(preview_html, height=preview_height, scrolling=False)

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            _download_button_export("Download SVG", data=svg_payload.get("svg_markup", "").encode("utf-8"), file_name="minimum_footprint_plan.svg", mime="image/svg+xml", use_container_width=True)
        with col_b:
            png_bytes = render_png_bytes(drawing if isinstance(drawing, dict) else {}, params=params, output_width_px=2400)
            _download_button_export("Download PNG", data=png_bytes, file_name="minimum_footprint_plan.png", mime="image/png", use_container_width=True)
        with col_c:
            dxf_bytes = render_dxf_bytes(drawing if isinstance(drawing, dict) else {}, params={})
            _download_button_export("Download DXF", data=dxf_bytes, file_name="minimum_footprint_plan.dxf", mime="application/dxf", use_container_width=True)
        with col_d:
            report_pdf_bytes = _page2_report_pdf_bytes(best, program_intent=program_intent)
            _download_button_export("Report (PDF)", data=report_pdf_bytes, file_name="minimum_footprint_report.pdf", mime="application/pdf", use_container_width=True)


st.sidebar.markdown("### ESMF Retail Spatial Application")
st.sidebar.caption("Version 2C — Desktop Shell")

_app_page = st.sidebar.radio(
    "Design Workflow",
    ["Layout Generator", "Footprint Calculator", "Device Adjustment"],
    index=0,
)

if _app_page == "Footprint Calculator":
    _run_minimum_footprint_page()
    st.stop()

if _app_page == "Device Adjustment":
    _run_manual_t_move_page()
    st.stop()

st.markdown('<h1 style="color:#0f172a !important;-webkit-text-fill-color:#0f172a !important;">Retail Store Layout Generator</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#0f172a !important;-webkit-text-fill-color:#0f172a !important;">Evidence-based retail spatial planning workspace for layout generation, footprint calculation, and manual interactive-device adjustment.</p>', unsafe_allow_html=True)
with st.expander("ℹ️ Display classification notes", expanded=False):
    st.caption("Display islands are classified by store location into D1–D12 and drawn as light solid closed boundaries on separate layers. Frontage zone title is hidden; D3, D4, D11, and D12 remain labeled for debugging. D12 is rebuilt per opening mode as the corner frontage island between the wall and the nearest D4, falling back to D3 when needed.")
    st.caption("Center-right D5/D6 now mirror the validated left-side strip width directly from the right wall; strip validation is rounded to prevent equal-width loss from floating-point precision.")

with st.sidebar:
    st.header("Store Geometry")
    size_mode_ui = st.radio("Input Method", ["Area + Width", "Length × Width"], index=1, format_func=lambda x: {"Area + Width": "Area + Frontage", "Length × Width": "Depth × Frontage"}.get(x, x))

    if size_mode_ui == "Area + Width":
        area_m2 = st.number_input("Store Area (m²)", min_value=20.0, value=120.0, step=5.0)
        width_m = st.number_input("Frontage Width (m)", min_value=4.0, value=12.0, step=0.5)
        length_m = area_m2 / width_m if width_m > 0 else 0.0
        st.caption(f"Calculated store depth: **{length_m:.2f} m**")
    else:
        width_m = st.number_input("Frontage Width (m)", min_value=4.0, value=12.0, step=0.5)
        length_m = st.number_input("Store Depth (m)", min_value=4.0, value=18.0, step=0.5)
        area_m2 = width_m * length_m
        st.caption(f"Calculated store area: **{area_m2:.2f} m²**")

    store_band = classify_store_band(area_m2)
    st.markdown(f"**Store size classification:** {store_band.upper()}")
    entrance_position_ui = st.radio("Entrance Location", ["Left", "Center", "Right"], index=1, horizontal=True)

    st.markdown("#### Planning Strategy & Circulation")
    st.caption("Set the planning priority, then refine the primary spine and circulation spacing.")
    program_intent_ui = st.selectbox(
        "Planning Priority",
        ["Balanced", "Sales-first", "Fitting-first", "Service-first"],
        index=0,
        help="Controls the spatial bias used by the baseline allocation logic.",
        format_func=lambda x: {"Balanced": "Balanced", "Sales-first": "Display-priority", "Fitting-first": "Fitting-priority", "Service-first": "Service-priority"}.get(x, x),
    )

    computed_spine_width = _computed_spine_width(store_band, program_intent_ui)
    dims_signature = f"{width_m:.3f}_{length_m:.3f}_{store_band}_{program_intent_ui}"
    if st.session_state.get("spine_width_dims_signature") != dims_signature:
        st.session_state["spine_width_dims_signature"] = dims_signature
        st.session_state["spine_width_slider"] = computed_spine_width

    spine_width_ui = st.slider(
        "Primary Spine Width (m)",
        min_value=1.60,
        max_value=2.40,
        value=float(st.session_state.get("spine_width_slider", computed_spine_width)),
        step=0.10,
        key="spine_width_slider",
        help="Manual override for the primary circulation spine width.",
    )
    st.caption(f"Computed recommendation from store size and planning priority: **{computed_spine_width:.2f} m**")

    st.markdown("##### Circulation Spacing")
    recommended_spacing_m = st.slider(
        "Secondary Circulation Spacing (m)",
        min_value=1.50,
        max_value=3.60,
        value=2.50,
        step=0.10,
        help="Recommended clear spacing between horizontal circulation bands.",
    )

    fitting_side_ui = st.radio("Fitting Suite Side", ["Left", "Right"], index=0, horizontal=True)
    fitting_layout_mode_ui = st.selectbox("Fitting Room Arrangement", ["Attached fitting rooms", "Separated fitting rooms"], index=0)

    st.header("Display Fixture Controls")
    enable_d7_display_ui = st.checkbox("Fitting-side Display (D7)", value=False)
    enable_d8_display_ui = st.checkbox("Checkout-side Display (D8)", value=False)
    enable_d11_display_ui = st.checkbox("Frontage Mannequin Display (D11/F7)", value=False)

    st.header("Added-Value Spatial Zones")
    selected_ui = st.multiselect("Select Added-Value Zones", list(UI_NAME_TO_KEY.keys()), default=[])
    intensity_ui = st.selectbox("Added-Value Intensity", ["Low", "Medium", "High"], index=1)

    
    st.caption("")
    st.caption("")

    st.caption("")
    st.caption("")

    st.header("Territorial Aisle System")
    left_territory_mode_ui = st.selectbox("Left Territory Fixture Mode", ["Single Gondola", "Double Gondola"], index=1)
    right_territory_mode_ui = st.selectbox("Right Territory Fixture Mode", ["Single Gondola", "Double Gondola"], index=1)
    st.caption("Territorial aisles are vertical dividers generated independently between each side aisle and the main spine.")


normalized_inputs = _normalize_inputs(size_mode_ui, area_m2, length_m, width_m, entrance_position_ui)
shell_validation = validate_step1_inputs(normalized_inputs, params)
intent_map = {"Balanced": "balanced", "Sales-first": "sales_first", "Fitting-first": "fitting_first", "Service-first": "service_first"}
intensity_map = {"Low": "low", "Medium": "medium", "High": "high"}

col1, col2 = st.columns([1.25, 0.75])

with col2:
    st.markdown('<h2 style="color:#0f172a !important;-webkit-text-fill-color:#0f172a !important;">Technology Families</h2>', unsafe_allow_html=True)
    st.header("Interactive Device Controls")
    _auto_fill_apply = st.session_state.pop("_auto_fill_t_apply", None)
    if isinstance(_auto_fill_apply, dict):
        for _k, _v in _auto_fill_apply.items():
            st.session_state[_k] = _v
    if "auto_fill_t_level" not in st.session_state:
        st.session_state["auto_fill_t_level"] = "Moderate"
    if "auto_fill_t_enabled" not in st.session_state:
        st.session_state["auto_fill_t_enabled"] = True
    st.markdown("""
    <style>
    div[data-testid="stToggle"] label p {
        font-size: 0px;
        margin: 0;
    }
    div[data-testid="stToggle"] {
        display: flex;
        justify-content: flex-end;
        padding-top: 0.15rem;
    }
    </style>
    """, unsafe_allow_html=True)
    _af_col_btn, _af_col_toggle = st.columns([6, 1])
    with _af_col_btn:
        auto_fill_t_clicked = st.button("Auto-fill Interactive Devices", use_container_width=True, key="auto_fill_tfamilies_btn")
    _prev_auto_fill_t_enabled = st.session_state.get("_auto_fill_t_prev_enabled", st.session_state.get("auto_fill_t_enabled", True))
    with _af_col_toggle:
        auto_fill_t_enabled = st.toggle("Auto-fill enabled", value=st.session_state.get("auto_fill_t_enabled", True), key="auto_fill_t_enabled", label_visibility="collapsed")
    if (not auto_fill_t_enabled) and _prev_auto_fill_t_enabled:
        st.session_state["_auto_fill_t_apply"] = {
            "t1_enabled_ui": False, "t1_count_ui": 1,
            "t2_enabled_ui": False, "t2_count_ui": 1,
            "t3_enabled_ui": False, "t3_count_ui": 1,
            "t4_enabled_ui": False, "t4_count_ui": 1,
            "t8_enabled_ui": False, "t8_count_ui": 1,
            "t9_enabled_ui": False, "t9_count_ui": 1,
        }
        st.session_state["_auto_fill_t_request"] = False
        st.session_state["_auto_fill_t_active"] = False
        st.session_state["_auto_fill_t_prev_level"] = st.session_state.get("auto_fill_t_level", "Moderate")
        st.session_state["_auto_fill_t_prev_enabled"] = auto_fill_t_enabled
        st.rerun()
    if auto_fill_t_clicked and auto_fill_t_enabled:
        st.session_state["_auto_fill_t_request"] = True
        st.session_state["_auto_fill_t_prev_enabled"] = auto_fill_t_enabled
        st.rerun()
    st.session_state["_auto_fill_t_prev_enabled"] = auto_fill_t_enabled
    auto_fill_t_level = st.select_slider(
        "Technology Density",
        options=["Low", "Moderate", "Max"],
        value=st.session_state.get("auto_fill_t_level", "Moderate"),
        key="auto_fill_t_level",
    )
    _prev_auto_fill_t_level = st.session_state.get("_auto_fill_t_prev_level", auto_fill_t_level)
    _auto_fill_t_is_active = bool(st.session_state.get("_auto_fill_t_active", False))
    if _auto_fill_t_is_active and auto_fill_t_level != _prev_auto_fill_t_level:
        st.session_state["_auto_fill_t_request"] = True
    st.session_state["_auto_fill_t_prev_level"] = auto_fill_t_level
    auto_fill_t_request = bool(st.session_state.get("_auto_fill_t_request", False))
    auto_t1_active = bool(st.session_state.get("t1_enabled_ui", False) or auto_fill_t_request)
    auto_t2_active = bool(st.session_state.get("t2_enabled_ui", False) or auto_fill_t_request)
    auto_t3_active = bool(st.session_state.get("t3_enabled_ui", False) or auto_fill_t_request)
    auto_t4_active = bool(st.session_state.get("t4_enabled_ui", False) or auto_fill_t_request)
    auto_t8_active = bool(st.session_state.get("t8_enabled_ui", False) or auto_fill_t_request)
    auto_t9_active = bool(st.session_state.get("t9_enabled_ui", False) or auto_fill_t_request)
    t1_count_ui = 0
    t1_width_ui = 0.60
    t1_depth_ui = 0.30
    with st.expander("T1 — Interactive Screen", expanded=False):
        t1_enabled_ui = st.checkbox("Use Device", value=False, key="t1_enabled_ui")
        st.caption("Priority: D6 → D5 | Recommended: W = 0.60 m, D = 0.30 m | Side soft = 0.50 m")
        if auto_t1_active:
            c1, c2, c3 = st.columns(3)
            with c1:
                t1_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t1_count_ui"))
            with c2:
                t1_width_ui = float(st.number_input("W (m)", min_value=0.30, value=0.60, step=0.10, format="%.2f", key="t1_width_ui"))
            with c3:
                t1_depth_ui = float(st.number_input("D (m)", min_value=0.10, value=0.30, step=0.10, format="%.2f", key="t1_depth_ui"))
        else:
            st.caption("Not selected")

    t2_count_ui = 0
    t2_width_ui = 0.60
    t2_depth_ui = 0.60
    with st.expander("T2 — Interactive Kiosk", expanded=False):
        t2_enabled_ui = st.checkbox("Use Device", value=False, key="t2_enabled_ui")
        st.caption("Priority: D1 → D2 | Recommended: W = 0.60 m, D = 0.60 m | Color = Green")
        if t2_enabled_ui:
            c1, c2, c3 = st.columns(3)
            with c1:
                t2_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t2_count_ui"))
            with c2:
                t2_width_ui = float(st.number_input("W (m)", min_value=0.30, value=0.60, step=0.10, format="%.2f", key="t2_width_ui"))
            with c3:
                t2_depth_ui = float(st.number_input("D (m)", min_value=0.10, value=0.60, step=0.10, format="%.2f", key="t2_depth_ui"))
        else:
            st.caption("Not selected")

    t3_count_ui = 0
    t3_width_ui = 0.60
    t3_depth_ui = 0.30
    with st.expander("T3 — Smart / Magic Mirror", expanded=False):
        t3_enabled_ui = st.checkbox("Use Device", value=False, key="t3_enabled_ui")
        st.caption("Priority: Fitting Area Buffer top boundary | Recommended: W = 0.60 m, D = 0.30 m | Color = Blue")
        if t3_enabled_ui:
            c1, c2, c3 = st.columns(3)
            with c1:
                t3_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t3_count_ui"))
            with c2:
                t3_width_ui = float(st.number_input("W (m)", min_value=0.30, value=0.60, step=0.10, format="%.2f", key="t3_width_ui"))
            with c3:
                t3_depth_ui = float(st.number_input("D (m)", min_value=0.10, value=0.30, step=0.10, format="%.2f", key="t3_depth_ui"))
        else:
            st.caption("Not selected")

    t4_count_ui = 0
    t4_width_ui = 0.80
    t4_depth_ui = 0.60
    with st.expander("T4 — Free-standing Smart / Magic Mirror", expanded=False):
        t4_enabled_ui = st.checkbox("Use Device", value=False, key="t4_enabled_ui")
        st.caption("Priority: D1 near Fitting Suite only | Recommended: W = 0.80 m, D = 0.60 m | Color = Green")
        if t4_enabled_ui:
            c1, c2, c3 = st.columns(3)
            with c1:
                t4_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t4_count_ui"))
            with c2:
                t4_width_ui = float(st.number_input("W (m)", min_value=0.30, value=0.80, step=0.10, format="%.2f", key="t4_width_ui"))
            with c3:
                t4_depth_ui = float(st.number_input("D (m)", min_value=0.10, value=0.60, step=0.10, format="%.2f", key="t4_depth_ui"))
        else:
            st.caption("Not selected")


    t6_count_ui = 0
    t6_width_ui = 0.80
    t6_depth_ui = 0.80
    with st.expander("T6 — Seated VR Station", expanded=False):
        t6_enabled_ui = st.checkbox("Use Device", value=False, key="t6_enabled_ui")
        st.caption("Priority: D1 → D2 | Recommended: W = 0.80 m, D = 0.80 m | Color = Cyan")
        if t6_enabled_ui:
            c1, c2, c3 = st.columns(3)
            with c1:
                t6_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t6_count_ui"))
            with c2:
                t6_width_ui = float(st.number_input("W (m)", min_value=0.40, value=0.80, step=0.10, format="%.2f", key="t6_width_ui"))
            with c3:
                t6_depth_ui = float(st.number_input("D (m)", min_value=0.40, value=0.80, step=0.10, format="%.2f", key="t6_depth_ui"))
        else:
            st.caption("Not selected")

    t7_count_ui = 0
    t7_width_ui = 1.20
    t7_depth_ui = 1.20
    with st.expander("T7 — Standing VR Station", expanded=False):
        t7_enabled_ui = st.checkbox("Use Device", value=False, key="t7_enabled_ui")
        st.caption("Priority: D1 → D2 | Recommended: W = 1.20 m, D = 1.20 m | Color = Purple")
        if t7_enabled_ui:
            c1, c2, c3 = st.columns(3)
            with c1:
                t7_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t7_count_ui"))
            with c2:
                t7_width_ui = float(st.number_input("W (m)", min_value=0.60, value=1.20, step=0.10, format="%.2f", key="t7_width_ui"))
            with c3:
                t7_depth_ui = float(st.number_input("D (m)", min_value=0.60, value=1.20, step=0.10, format="%.2f", key="t7_depth_ui"))
        else:
            st.caption("Not selected")

    t8_count_ui = 0
    t8_width_ui = 0.60
    t8_depth_ui = 0.30
    with st.expander("T8 — Express Checkout", expanded=False):
        t8_enabled_ui = st.checkbox("Use Device", value=False, key="t8_enabled_ui")
        st.caption("Priority: Checkout boundary only | Fixed placement start = side opposite fitting/check-out shared boundary | Recommended: W = 0.80 m, D = 0.60 m | Side offset = 0.60 m | Front soft = 2.40 m | Front min = 1.20 m")
        if t8_enabled_ui:
            c1, c2, c3 = st.columns(3)
            with c1:
                t8_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t8_count_ui"))
            with c2:
                t8_width_ui = float(st.number_input("W (m)", min_value=0.40, value=0.60, step=0.10, format="%.2f", key="t8_width_ui"))
            with c3:
                t8_depth_ui = float(st.number_input("D (m)", min_value=0.30, value=0.30, step=0.10, format="%.2f", key="t8_depth_ui"))
        else:
            st.caption("Not selected")

    t9_count_ui = 0
    t9_width_ui = 1.20
    t9_depth_ui = 0.60
    with st.expander("T9 — Fixed Self Checkout", expanded=False):
        t9_enabled_ui = st.checkbox("Use Device", value=False, key="t9_enabled_ui")
        st.caption("Host priority: D1 beside Checkout → D2 | Hard / minimum / soft buffers follow T8")
        if t9_enabled_ui:
            c1, c2, c3 = st.columns(3)
            with c1:
                t9_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t9_count_ui"))
            with c2:
                t9_width_ui = float(st.number_input("W (m)", min_value=0.40, value=1.20, step=0.10, format="%.2f", key="t9_width_ui"))
            with c3:
                t9_depth_ui = float(st.number_input("D (m)", min_value=0.30, value=0.60, step=0.10, format="%.2f", key="t9_depth_ui"))
        else:
            st.caption("Not selected")

    t5_count_ui = 0
    t5_width_ui = 1.50
    t5_depth_ui = 1.50
    with st.expander("T5 — 3D Body Scanner", expanded=False):
        t5_enabled_ui = st.checkbox("Use Device", value=False, key="t5_enabled_ui")
        st.caption("Copy of T3 behavior | Fixed hard footprint: W = 1.50 m, D = 1.50 m | Color = Magenta")
        if t5_enabled_ui:
            c1, c2, c3 = st.columns(3)
            with c1:
                t5_count_ui = int(st.number_input("Count", min_value=1, max_value=20, value=1, step=1, key="t5_count_ui"))
            with c2:
                st.number_input("W (m)", min_value=1.50, max_value=1.50, value=1.50, step=0.10, format="%.2f", key="t5_width_ui", disabled=True)
                t5_width_ui = 1.50
            with c3:
                st.number_input("D (m)", min_value=1.50, max_value=1.50, value=1.50, step=0.10, format="%.2f", key="t5_depth_ui", disabled=True)
                t5_depth_ui = 1.50
        else:
            st.caption("Not selected")


with col1:
    st.markdown('<h2 style="color:#0f172a !important;-webkit-text-fill-color:#0f172a !important;">Layout Preview</h2>', unsafe_allow_html=True)
    if shell_validation["is_valid"]:
        shell = generate_store_shell(normalized_inputs, params)
        zoning = build_zoning(shell, fitting_side=fitting_side_ui.lower(), program_intent=intent_map[program_intent_ui])
        zval = validate_zoning(shell, zoning)
        if zval["is_valid"]:
            circulation = build_circulation(
                shell,
                zoning,
                recommended_spacing_m=recommended_spacing_m,
                user_spine_width_m=spine_width_ui,
                left_territory_mode=left_territory_mode_ui,
                right_territory_mode=right_territory_mode_ui,
            )
            frontage = build_frontage_zones(shell, zoning, circulation)
            display_classes = build_display_classification(shell, zoning, circulation, frontage)
            cval = validate_circulation(shell, zoning, circulation)
            spacing = analyze_spacing(circulation, recommended_spacing_m=recommended_spacing_m)
            fitting_layout_mode = "attached" if fitting_layout_mode_ui == "Attached fitting rooms" else "separated"
            fitting_rooms = _generate_fitting_rooms(zoning, fitting_side_ui.lower(), area_m2, circulation, layout_mode=fitting_layout_mode)
            selected_keys = [UI_NAME_TO_KEY[n] for n in selected_ui]
            added = build_added_zones(zoning, selected_keys, intensity_map[intensity_ui], frontage=frontage)
            aval = validate_added_zones(added)
            t1_capacity = None
            t1_placed_preview = None
            t2_capacity = None
            t2_placed_preview = None
            t3_capacity = None
            t3_placed_preview = None
            t4_capacity = None
            t4_placed_preview = None
            t5_capacity = None
            t5_placed_preview = None
            t8_capacity = None
            t8_placed_preview = None
            t6_capacity = None
            t6_placed_preview = None
            t7_capacity = None
            t7_placed_preview = None
            if auto_t1_active:
                _t1_preview = _build_t1_placements(display_classes, zoning, 9999, float(t1_width_ui), float(t1_depth_ui))
                t1_capacity = int(_t1_preview.get("capacity", 0) or 0)
                t1_placed_preview = min(int(t1_count_ui), t1_capacity)
            _t4_preview_for_t2 = None
            if auto_t4_active:
                _t4_preview_for_t2 = _build_t4_placements(display_classes, zoning, 9999, float(t4_width_ui), float(t4_depth_ui))
            if auto_t2_active:
                _t2_preview = _build_t2_placements(display_classes, zoning, 9999, float(t2_width_ui), float(t2_depth_ui), blocked_soft_rects=list((_t4_preview_for_t2 or {}).get("soft", [])))
                t2_capacity = int(_t2_preview.get("capacity", 0) or 0)
                t2_placed_preview = min(int(t2_count_ui), t2_capacity)
            joint_t3_t5_preview = None
            if t3_enabled_ui and t5_enabled_ui:
                joint_t3_t5_preview = _build_t3_t5_joint_placements(display_classes, zoning, circulation, fitting_rooms, 9999, float(t3_width_ui), float(t3_depth_ui), 9999, 1.50, 1.50, allow_d7=enable_d7_display_ui)
            if auto_t3_active:
                _t3_preview = (joint_t3_t5_preview or {}).get("t3") if joint_t3_t5_preview else _build_t3_placements(display_classes, zoning, circulation, fitting_rooms, 9999, float(t3_width_ui), float(t3_depth_ui), allow_d7=enable_d7_display_ui)
                t3_capacity = int((_t3_preview or {}).get("capacity", 0) or 0)
                t3_placed_preview = min(int(t3_count_ui), t3_capacity)
            _t5_preview_for_t4 = None
            if t5_enabled_ui:
                _t5_preview_for_t4 = (joint_t3_t5_preview or {}).get("t5") if joint_t3_t5_preview else _build_t5_placements(display_classes, zoning, circulation, fitting_rooms, 9999, 1.50, 1.50, allow_d7=enable_d7_display_ui)
                t5_capacity = int((_t5_preview_for_t4 or {}).get("capacity", 0) or 0)
                t5_placed_preview = min(int(t5_count_ui), t5_capacity)
            if auto_t4_active:
                _t4_preview = _build_t4_placements(display_classes, zoning, 9999, float(t4_width_ui), float(t4_depth_ui), blocked_soft_rects=(list((_t2_preview or {}).get("soft", [])) if auto_t2_active else []) + (list((_t5_preview_for_t4 or {}).get("soft", [])) if t5_enabled_ui else []))
                t4_capacity = int(_t4_preview.get("capacity", 0) or 0)
                t4_placed_preview = min(int(t4_count_ui), t4_capacity)

            if t6_enabled_ui:
                _t6_preview = _build_t6_placements(display_classes, 9999, float(t6_width_ui), float(t6_depth_ui), blocked_soft_rects=(list((_t4_preview or {}).get("min", [])) if t4_enabled_ui else []) + (list((_t2_preview or {}).get("min", [])) if t2_enabled_ui else []))
                t6_capacity = int(_t6_preview.get("capacity", 0) or 0)
                t6_placed_preview = min(int(t6_count_ui), t6_capacity)
            if t7_enabled_ui:
                _t7_preview = _build_t7_placements(display_classes, 9999, float(t7_width_ui), float(t7_depth_ui), blocked_soft_rects=(list((_t4_preview or {}).get("min", [])) if t4_enabled_ui else []) + (list((_t2_preview or {}).get("min", [])) if t2_enabled_ui else []) + (list((_t6_preview or {}).get("min", [])) if t6_enabled_ui else []))
                t7_capacity = int(_t7_preview.get("capacity", 0) or 0)
                t7_placed_preview = min(int(t7_count_ui), t7_capacity)
            if auto_t8_active:
                _t8_preview = _build_t8_placements(display_classes, zoning, circulation, 9999, float(t8_width_ui), float(t8_depth_ui), side_offset_m=0.60, front_soft_m=2.40, front_min_m=1.20)
                t8_capacity = int((_t8_preview or {}).get("capacity", 0) or 0)
                t8_placed_preview = min(int(t8_count_ui), t8_capacity)
            if auto_t9_active:
                _t9_preview = _build_t9_placements(display_classes, zoning, 9999, float(t9_width_ui), float(t9_depth_ui), side_offset_m=0.60, front_soft_m=2.40, front_min_m=1.20, blocked_soft_rects=[])
                t9_capacity = int((_t9_preview or {}).get("capacity", 0) or 0)
                t9_placed_preview = min(int(t9_count_ui), t9_capacity)
            if t5_enabled_ui:
                _t5_preview = (joint_t3_t5_preview or {}).get("t5") if joint_t3_t5_preview else _build_t5_placements(display_classes, zoning, circulation, fitting_rooms, 9999, 1.50, 1.50, allow_d7=enable_d7_display_ui, blocked_soft_rects=(list((_t4_preview or {}).get("soft", [])) if t4_enabled_ui else []) + (list((_t3_preview or {}).get("soft", [])) if t3_enabled_ui else []))
                t5_capacity = int((_t5_preview or {}).get("capacity", 0) or 0)
                t5_placed_preview = min(int(t5_count_ui), t5_capacity)
                if t3_enabled_ui and int(t5_count_ui) > 0 and t5_capacity <= 0:
                    st.info("No place available for T5 under the current settings after giving priority to T3.")
            if auto_fill_t_request:
                _auto_fill_factor = {"Low": 0.25, "Moderate": 0.50, "Max": 1.00}.get(auto_fill_t_level, 1.00)

                def _scaled_auto_fill_count(_capacity):
                    _capacity = int(_capacity or 0)
                    if _capacity <= 0:
                        return 1
                    return max(1, int(_capacity * _auto_fill_factor))

                # Auto-fill balancing rule for checkout logic:
                # If T9 is feasible in a lighter mode, Max must not remove it by letting
                # D1/D2 experience devices consume all protected space first. Therefore,
                # auto-fill keeps T9 as a reserved anchor and trims T2/T4 counts only when
                # necessary so that at least one T9 remains placeable under the same
                # hard/min-buffer rules used by the drawing engine.
                _auto_t2_count = _scaled_auto_fill_count(t2_capacity) if (t2_capacity or 0) > 0 else 1
                _auto_t4_count = _scaled_auto_fill_count(t4_capacity) if (t4_capacity or 0) > 0 else 1
                _auto_t9_count = _scaled_auto_fill_count(t9_capacity) if (t9_capacity or 0) > 0 else 1

                def _preview_t9_after_t2_t4(_t2c, _t4c, _t9c):
                    try:
                        _t4_block = _build_t4_placements(
                            display_classes, zoning, int(_t4c), float(t4_width_ui), float(t4_depth_ui),
                            side_offset_m=0.60, front_soft_m=1.60, front_min_m=1.20, blocked_soft_rects=[]
                        ) if bool((t4_capacity or 0) > 0) and int(_t4c) > 0 else {}
                        _t2_pack_sim = _build_t2_placements(
                            display_classes, zoning, int(_t2c), float(t2_width_ui), float(t2_depth_ui),
                            side_offset_m=0.60, front_soft_m=1.60, front_min_m=1.20,
                            blocked_soft_rects=list((_t4_block or {}).get("soft", []))
                        ) if bool((t2_capacity or 0) > 0) and int(_t2c) > 0 else {}
                        _t4_pack_sim = _build_t4_placements(
                            display_classes, zoning, int(_t4c), float(t4_width_ui), float(t4_depth_ui),
                            side_offset_m=0.60, front_soft_m=1.60, front_min_m=1.20,
                            blocked_soft_rects=list((_t2_pack_sim or {}).get("soft", []))
                        ) if bool((t4_capacity or 0) > 0) and int(_t4c) > 0 else {}
                        _t9_pack_sim = _build_t9_placements(
                            display_classes, zoning, int(_t9c), float(t9_width_ui), float(t9_depth_ui),
                            side_offset_m=0.60, front_soft_m=2.40, front_min_m=1.20,
                            blocked_soft_rects=list((_t4_pack_sim or {}).get("min", [])) + list((_t2_pack_sim or {}).get("min", []))
                        ) if bool((t9_capacity or 0) > 0) and int(_t9c) > 0 else {}
                        return len(list((_t9_pack_sim or {}).get("hard", [])))
                    except Exception:
                        return 0

                if (t9_capacity or 0) > 0:
                    _auto_t9_count = max(1, int(_auto_t9_count))
                    # Prefer preserving T9 by reducing T2 first, then T4 only if needed.
                    # This keeps checkout technology stable while still allowing the
                    # maximum possible mix of other D1/D2 T-families.
                    _guard = 0
                    while _preview_t9_after_t2_t4(_auto_t2_count, _auto_t4_count, _auto_t9_count) <= 0 and (_auto_t2_count > 1 or _auto_t4_count > 1) and _guard < 50:
                        if _auto_t2_count >= _auto_t4_count and _auto_t2_count > 1:
                            _auto_t2_count -= 1
                        elif _auto_t4_count > 1:
                            _auto_t4_count -= 1
                        elif _auto_t2_count > 1:
                            _auto_t2_count -= 1
                        _guard += 1

                st.session_state["_auto_fill_t_apply"] = {
                    "t1_enabled_ui": bool((t1_capacity or 0) > 0),
                    "t1_count_ui": _scaled_auto_fill_count(t1_capacity),
                    "t2_enabled_ui": bool((t2_capacity or 0) > 0),
                    "t2_count_ui": max(1, int(_auto_t2_count)),
                    "t3_enabled_ui": bool((t3_capacity or 0) > 0),
                    "t3_count_ui": _scaled_auto_fill_count(t3_capacity),
                    "t4_enabled_ui": bool((t4_capacity or 0) > 0),
                    "t4_count_ui": max(1, int(_auto_t4_count)),
                    "t8_enabled_ui": bool((t8_capacity or 0) > 0),
                    "t8_count_ui": _scaled_auto_fill_count(t8_capacity),
                    "t9_enabled_ui": bool((t9_capacity or 0) > 0),
                    "t9_count_ui": max(1, int(_auto_t9_count)),
                }
                st.session_state["_auto_fill_t_request"] = False
                st.session_state["_auto_fill_t_active"] = True
                st.rerun()
            if (aval["is_valid"] or not selected_keys) and cval["is_valid"]:
                    drawing = _build_drawing(shell, zoning, added if selected_keys else None, circulation, frontage, display_classes, fitting_rooms=fitting_rooms, enable_d7_display=enable_d7_display_ui, enable_d8_display=enable_d8_display_ui, enable_d11_display=enable_d11_display_ui, t1_enabled=t1_enabled_ui, t1_count=t1_count_ui, t1_width_m=t1_width_ui, t1_depth_m=t1_depth_ui, t2_enabled=t2_enabled_ui, t2_count=t2_count_ui, t2_width_m=t2_width_ui, t2_depth_m=t2_depth_ui, t3_enabled=t3_enabled_ui, t3_count=t3_count_ui, t3_width_m=t3_width_ui, t3_depth_m=t3_depth_ui, t4_enabled=t4_enabled_ui, t4_count=t4_count_ui, t4_width_m=t4_width_ui, t4_depth_m=t4_depth_ui, t5_enabled=t5_enabled_ui, t5_count=t5_count_ui, t5_width_m=1.50, t5_depth_m=1.50, t6_enabled=t6_enabled_ui, t6_count=t6_count_ui, t6_width_m=t6_width_ui, t6_depth_m=t6_depth_ui, t7_enabled=t7_enabled_ui, t7_count=t7_count_ui, t7_width_m=t7_width_ui, t7_depth_m=t7_depth_ui, t8_enabled=t8_enabled_ui, t8_count=t8_count_ui, t8_width_m=t8_width_ui, t8_depth_m=t8_depth_ui, t9_enabled=t9_enabled_ui, t9_count=t9_count_ui, t9_width_m=t9_width_ui, t9_depth_m=t9_depth_ui)
                    if isinstance(drawing, dict):
                        st.session_state["page1_output_drawing"] = _p3_deepcopy_drawing(drawing)
                    svg_payload = build_svg_payload(drawing, params)
                    canvas = svg_payload.get("canvas", {})
                    canvas_w = float(canvas.get("width_px", 700.0) or 700.0)
                    canvas_h = float(canvas.get("height_px", 500.0) or 500.0)
                    aspect_ratio = canvas_h / max(canvas_w, 1.0)
                    preview_height = int(min(860, max(560, round(760 * aspect_ratio))))
                    preview_html = f"""
                    <html><head><style>
                    html, body {{ margin:0; padding:0; background:white; overflow:hidden; }}
                    .preview-wrap {{ width:100%; height:{preview_height}px; display:flex; align-items:center; justify-content:center; background:white; }}
                    .preview-wrap svg {{ width:100%; height:100%; display:block; }}
                    </style></head><body><div class="preview-wrap">{svg_payload["svg_markup"]}</div></body></html>
                    """
                    components.html(preview_html, height=preview_height, scrolling=False)
                    if t1_enabled_ui and t1_capacity is not None:
                        if t1_capacity <= 0:
                            st.warning("T1 max. capacity reached in this store setting: 0. No valid place inside D6 or D5 for the current T1 dimensions.")
                        elif int(t1_count_ui) > int(t1_capacity):
                            st.warning(f"T1 max. capacity reached in this store setting: {t1_capacity}. Requested: {int(t1_count_ui)}. Placed: {t1_placed_preview}.")
                        else:
                            st.caption(f"T1 capacity in current D6/D5 setting: {t1_capacity}. Requested: {int(t1_count_ui)}. Placed: {t1_placed_preview}.")
                    if t2_enabled_ui and t2_capacity is not None:
                        if t2_capacity <= 0:
                            st.warning("T2 max. capacity reached in this store setting: 0. No valid place inside D1 or D2 for the current T2 dimensions.")
                        elif int(t2_count_ui) > int(t2_capacity):
                            st.warning(f"T2 max. capacity reached in this store setting: {t2_capacity}. Requested: {int(t2_count_ui)}. Placed: {t2_placed_preview}.")
                        else:
                            st.caption(f"T2 capacity in current D1/D2 setting: {t2_capacity}. Requested: {int(t2_count_ui)}. Placed: {t2_placed_preview}.")
                    if t3_enabled_ui and t3_capacity is not None:
                        if t3_capacity <= 0:
                            st.warning("T3 max. capacity reached in this store setting: 0. No valid place along the top boundary of the Fitting Area Buffer or, if D7 is enabled, inside D7 for the current T3 dimensions.")
                        elif int(t3_count_ui) > int(t3_capacity):
                            st.warning(f"T3 max. capacity reached in this store setting: {t3_capacity}. Requested: {int(t3_count_ui)}. Placed: {t3_placed_preview}.")
                        else:
                            st.caption(f"T3 capacity in current fitting-buffer/(D7 only if enabled) setting: {t3_capacity}. Requested: {int(t3_count_ui)}. Placed: {t3_placed_preview}.")
                    if t4_enabled_ui and t4_capacity is not None:
                        if t4_capacity <= 0:
                            st.warning("T4 max. capacity reached in this store setting: 0. No valid place inside D1 near the Fitting Suite for the current T4 dimensions.")
                        elif int(t4_count_ui) > int(t4_capacity):
                            st.warning(f"T4 max. capacity reached in this store setting: {t4_capacity}. Requested: {int(t4_count_ui)}. Placed: {t4_placed_preview}.")
                        else:
                            st.caption(f"T4 capacity in current D1-near-fitting setting: {t4_capacity}. Requested: {int(t4_count_ui)}. Placed: {t4_placed_preview}.")

                    if t6_enabled_ui and t6_capacity is not None:
                        if t6_capacity <= 0:
                            st.warning("T6 max. capacity reached in this store setting: 0. No valid place inside D1 or D2 for the current T6 dimensions.")
                        elif int(t6_count_ui) > int(t6_capacity):
                            st.warning(f"T6 max. capacity reached in this store setting: {t6_capacity}. Requested: {int(t6_count_ui)}. Placed: {t6_placed_preview}.")
                        else:
                            st.caption(f"T6 capacity in current D1/D2 setting: {t6_capacity}. Requested: {int(t6_count_ui)}. Placed: {t6_placed_preview}.")

                    if t7_enabled_ui and t7_capacity is not None:
                        if t7_capacity <= 0:
                            st.warning("T7 max. capacity reached in this store setting: 0. No valid place inside D1 or D2 for the current T7 dimensions.")
                        elif int(t7_count_ui) > int(t7_capacity):
                            st.warning(f"T7 max. capacity reached in this store setting: {t7_capacity}. Requested: {int(t7_count_ui)}. Placed: {t7_placed_preview}.")
                        else:
                            st.caption(f"T7 capacity in current D1/D2 setting: {t7_capacity}. Requested: {int(t7_count_ui)}. Placed: {t7_placed_preview}.")
                    if t8_enabled_ui and t8_capacity is not None:
                        if t8_capacity <= 0:
                            st.warning("T8 max. capacity reached in this store setting: 0. No valid place inside the checkout boundary or D8 for the current T8 dimensions.")
                        elif int(t8_count_ui) > int(t8_capacity):
                            st.warning(f"T8 max. capacity reached in this store setting: {t8_capacity}. Requested: {int(t8_count_ui)}. Placed: {t8_placed_preview}.")
                        else:
                            st.caption(f"T8 capacity in the current checkout/D8 setting: {t8_capacity}. Requested: {int(t8_count_ui)}. Placed: {t8_placed_preview}. When T8 is hosted in Checkout, Checkout Counter and Checkout Buffer keep a minimum remaining width of 1.5 m. In D8 fallback, T8 is allowed whenever its hard footprint fits inside D8, even if min/soft buffers project beyond D8.")
                    if t9_enabled_ui and t9_capacity is not None:
                        if t9_capacity <= 0:
                            st.warning("T9 max. capacity reached in this store setting: 0. No valid place inside D1 beside Checkout or D2 for the current T9 dimensions.")
                        elif int(t9_count_ui) > int(t9_capacity):
                            st.warning(f"T9 max. capacity reached in this store setting: {t9_capacity}. Requested: {int(t9_count_ui)}. Placed: {t9_placed_preview}.")
                        else:
                            st.caption(f"T9 capacity in the current D1/D2 setting: {t9_capacity}. Requested: {int(t9_count_ui)}. Placed: {t9_placed_preview}.")
                    if t5_enabled_ui and t5_capacity is not None:
                        if t5_capacity <= 0:
                            st.warning("T5 max. capacity reached in this store setting: 0. No valid place along the top boundary of the Fitting Area Buffer or, if D7 is enabled, inside D7 for the current T5 dimensions.")
                        elif int(t5_count_ui) > int(t5_capacity):
                            st.warning(f"T5 max. capacity reached in this store setting: {t5_capacity}. Requested: {int(t5_count_ui)}. Placed: {t5_placed_preview}.")
                        else:
                            st.caption(f"T5 capacity in current fitting-buffer/(D7 only if enabled) setting: {t5_capacity}. Requested: {int(t5_count_ui)}. Placed: {t5_placed_preview}.")
            elif not cval["is_valid"]:
                st.error("Circulation generation failed. Open the validation panel.")
            else:
                st.error("Added zones are invalid for the current selection.")
        else:
            st.error("Core zoning is invalid.")
    else:
        st.error("Store geometry inputs are invalid.")

with col2:
    if shell_validation["is_valid"] and 'zval' in locals() and zval["is_valid"] and 'cval' in locals() and cval["is_valid"]:
        _final_fixture_items = []
        _display_state = (state.display or {}) if 'state' in locals() and hasattr(state, 'display') else {}
        _source_lists = [
            ("WALL_BAYS", _display_state.get("wall", [])),
            ("GONDOLA_RACK_SYSTEM", _display_state.get("gondola", [])),
            ("MANNEQUINS", _display_state.get("mannequin", [])),
            ("TABLES", _display_state.get("table", [])),
        ]
        for _source_family, _lst in _source_lists:
            for _obj in (_lst or []):
                if isinstance(_obj, dict):
                    _copy = dict(_obj)
                    _copy.setdefault("family", _source_family)
                    _final_fixture_items.append(_copy)
        _drawing_layers = drawing if isinstance(globals().get("drawing", None), dict) else (locals().get("drawing") if isinstance(locals().get("drawing"), dict) else {})
        if not _final_fixture_items:
            for _layer_name in ["DISPLAY_WALL", "DISPLAY_GONDOLA", "DISPLAY_MANNEQUIN", "DISPLAY_TABLE"]:
                _lst = _drawing_layers.get(_layer_name, []) if isinstance(_drawing_layers, dict) else []
                _final_fixture_items.extend([obj for obj in (_lst or []) if isinstance(obj, dict)])
        def _infer_report_f_family(_obj):
            _fam_raw = str(_obj.get("family", "") or "").strip().upper()
            if _fam_raw.startswith("F7"):
                return "F7"
            if _fam_raw in {f"F{i}" for i in range(1, 9)}:
                return _fam_raw
            _variant = str(_obj.get("variant", "") or "").strip().lower()
            _subfamily = str(_obj.get("subfamily", "") or "").strip().lower()
            _length = float(_obj.get("length", 0.0) or 0.0)
            _width = float(_obj.get("width", 0.0) or 0.0)
            _depth = min(_length, _width) if _length and _width else 0.0
            if _fam_raw == "WALL_BAYS":
                if _variant == "shirts_wall_bay":
                    return "F1"
                if _variant == "coats_wall_bay":
                    return "F2"
                if _variant in {"folded_apparel_wall_bay", "freestanding_wall_bay"}:
                    return "F3"
                if _depth <= 0.35 + 1e-6:
                    return "F1"
                if _depth <= 0.45 + 1e-6:
                    return "F2"
                return "F3"
            if _fam_raw == "GONDOLA_RACK_SYSTEM":
                if _variant == "double_sided_gondola":
                    return "F4"
                if _variant in {"single_sided_gondola", "shirts_straight_rack", "coats_straight_rack"}:
                    return "F5"
                if _variant == "two_way_rack":
                    return "F6"
                if _subfamily == "rack":
                    return "F5"
                if _subfamily == "gondola":
                    return "F4" if max(_length, _width) >= 1.0 and min(_length, _width) >= 0.9 else "F5"
            if _fam_raw == "TABLES":
                return "F8"
            if _fam_raw == "MANNEQUINS":
                return "F7"
            return _fam_raw

        _final_fixture_counts = {f"F{i}": 0 for i in range(1, 9)}
        for _obj in _final_fixture_items:
            _fam = _infer_report_f_family(_obj)
            if _fam in _final_fixture_counts:
                _final_fixture_counts[_fam] += 1

        _final_interactive_items = []
        for _layer_name in [f"INTERACTIVE_T{i}" for i in range(1, 10)]:
            _lst = _drawing_layers.get(_layer_name, []) if isinstance(_drawing_layers, dict) else []
            for _obj in (_lst or []):
                if isinstance(_obj, dict):
                    _copy = dict(_obj)
                    _fam = str(_copy.get("family", "") or "").strip().upper()
                    if not _fam and _layer_name.startswith("INTERACTIVE_"):
                        _fam = _layer_name.replace("INTERACTIVE_", "")
                    _copy["family"] = _fam
                    _final_interactive_items.append(_copy)

        _final_interactive_counts = {f"T{i}": 0 for i in range(1, 10)}
        for _obj in _final_interactive_items:
            _fam = str(_obj.get("family", "") or "").strip().upper().split(".")[0]
            if _fam in _final_interactive_counts:
                _final_interactive_counts[_fam] += 1

        report_payload = build_zone_ratio_report_payload(
            shell=shell,
            zoning=zoning,
            store_band=store_band,
            program_intent_ui=program_intent_ui,
            added=added if selected_keys else None,
            display_classes=display_classes if 'display_classes' in locals() else None,
            fixture_lists={
                "display_wall": list((_drawing_layers.get("DISPLAY_WALL", []) if isinstance(_drawing_layers, dict) else []) or []),
                "display_gondola": list((_drawing_layers.get("DISPLAY_GONDOLA", []) if isinstance(_drawing_layers, dict) else []) or []),
                "display_mannequin": list((_drawing_layers.get("DISPLAY_MANNEQUIN", []) if isinstance(_drawing_layers, dict) else []) or []),
                "display_table": list((_drawing_layers.get("DISPLAY_TABLE", []) if isinstance(_drawing_layers, dict) else []) or []),
            },
            fixture_items=_final_fixture_items,
            fixture_counts=_final_fixture_counts,
            interactive_items=_final_interactive_items,
            interactive_counts=_final_interactive_counts,
            preview_drawing_layers=(_drawing_layers if isinstance(_drawing_layers, dict) else {}),
        )
        report_pdf_bytes = render_zone_ratio_report_pdf(report_payload)

        _download_button_export(
            "Report (PDF)",
            data=report_pdf_bytes,
            file_name="baseline_zone_ratio_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        # SVG download uses the same final drawing layers as the on-screen preview/export.
        # This does not change any baseline, F-family, T-family, density, or buffer logic.
        svg_export_payload = build_svg_payload(_drawing_layers if isinstance(_drawing_layers, dict) else {}, params)
        svg_bytes = svg_export_payload.get("svg_markup", "").encode("utf-8")
        _download_button_export(
            "Download SVG",
            data=svg_bytes,
            file_name="plan_preview.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )

        # PNG download uses the final drawing layers. It uses CairoSVG when available,
        # with a Pillow fallback so the app does not fail if CairoSVG is missing.
        png_bytes = render_png_bytes(_drawing_layers if isinstance(_drawing_layers, dict) else {}, params=params, output_width_px=2400)
        _download_button_export(
            "Download PNG",
            data=png_bytes,
            file_name="plan_preview.png",
            mime="image/png",
            use_container_width=True,
        )

        dxf_bytes = render_dxf_bytes(_drawing_layers if isinstance(_drawing_layers, dict) else {}, params={})
        _download_button_export(
            "Download DXF",
            data=dxf_bytes,
            file_name="plan_preview.dxf",
            mime="application/dxf",
            use_container_width=True,
        )
