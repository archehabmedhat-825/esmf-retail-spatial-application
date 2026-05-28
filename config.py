from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PARAMS = {
    "entrance_width_m": 1.50,
    "entrance_corner_margin_m": 1.20,
    "frontage_depth_m": 2.40,
    "perimeter_strip_depth_m": 0.60,
    "primary_path_width_m": 1.50,
    "secondary_aisle_min_m": 1.20,
    "gondola_depth_m": 1.00,
    "row_band_min_length_m": 3.20,
    "side_strip_min_width_m": 0.90,
    "side_strip_min_length_m": 2.00,
    "table_size_options_m": [[0.80, 0.80], [1.20, 0.80]],
    "wall_thickness_external_m": 0.25,
    "wall_thickness_glass_m": 0.10,
    "wall_thickness_boh_m": 0.12,
    "wall_thickness_fitting_m": 0.10,
}

DATA_DIR = Path(__file__).parent / "data"


def _load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_parameters() -> dict:
    loaded = _load_json("parameters.json")
    merged = dict(DEFAULT_PARAMS)
    merged.update(loaded)
    return merged


def load_display_families() -> dict:
    return _load_json("display_families.json")
