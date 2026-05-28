from __future__ import annotations

from models import BaselineState
from shell import generate_store_shell
from zoning import generate_baseline_zones
from walls import generate_internal_walls
from bands import build_layout_bands
from display import generate_display_system
from validate import validate_baseline_state
from draw import assemble_baseline_drawing_objects
from export import assemble_baseline_export_payloads


def run_baseline_engine(inputs: dict, params: dict) -> BaselineState:
    """
    Step 3 baseline pipeline.

    Zoning may return a private `_meta` block with target areas and zoning-stage
    integrity values. This hook extracts it cleanly before the remaining modules
    run, so downstream code receives only drawable zone objects.
    """
    state = BaselineState(inputs=inputs, params=params)

    state.shell = generate_store_shell(inputs, params)

    zoning_output = generate_baseline_zones(state.shell, inputs, params)
    zoning_meta = zoning_output.pop("_meta", {}) if isinstance(zoning_output, dict) else {}
    state.zones = zoning_output

    state.walls_internal = generate_internal_walls(state.zones, inputs, params)
    # Ensure fitting subdivision artifacts remain cleanly accessible in state
    state.walls_internal.setdefault("fitting_rooms", [])
    state.walls_internal.setdefault("fitting_meta", {})
    state.bands = build_layout_bands(state, params)
    state.display = generate_display_system(state, params)
    state.validation = validate_baseline_state(state, params)

    if zoning_meta:
        state.validation.setdefault("zoning_meta", zoning_meta)

    state.status = "baseline_valid" if state.validation.get("hard_pass", False) else "baseline_invalid"
    state.drawing = assemble_baseline_drawing_objects(state, params)
    state.exports = assemble_baseline_export_payloads(state, params)
    return state
