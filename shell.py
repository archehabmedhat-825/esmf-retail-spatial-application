from __future__ import annotations

from geometry import make_rectangle, inset_rectangle


MICRO_MAX_M2 = 80.0
SMALL_MAX_M2 = 150.0
NORMAL_MAX_M2 = 300.0
LARGE_MAX_M2 = 600.0


def classify_store_band(area_m2: float) -> str:
    area_m2 = float(area_m2)
    if area_m2 < MICRO_MAX_M2:
        return "micro"
    if area_m2 < SMALL_MAX_M2:
        return "small"
    if area_m2 < NORMAL_MAX_M2:
        return "normal"
    if area_m2 < LARGE_MAX_M2:
        return "large"
    return "xl"


def _entrance_opening_x_range(store_width_m: float, entrance_position: str, entrance_width_m: float, entrance_margin_m: float) -> tuple[float, float]:
    if entrance_position == "center":
        x1 = (store_width_m - entrance_width_m) / 2.0
    elif entrance_position == "left":
        x1 = entrance_margin_m
    elif entrance_position == "right":
        x1 = store_width_m - entrance_margin_m - entrance_width_m
    else:
        raise ValueError(f"Unsupported entrance position: {entrance_position}")
    x2 = x1 + entrance_width_m
    return round(x1, 6), round(x2, 6)


def validate_step1_inputs(inputs: dict, params: dict) -> dict:
    messages: list[str] = []

    size_mode = inputs.get("size_mode")
    area_m2 = float(inputs.get("area_m2", 0.0))
    store_width_m = float(inputs.get("width_m", 0.0))
    store_depth_m = float(inputs.get("length_m", 0.0))
    if size_mode == "AW" and store_width_m > 0:
        store_depth_m = area_m2 / store_width_m

    entrance_width_m = float(params["entrance_width_m"])
    entrance_margin_m = float(params["entrance_corner_margin_m"])

    if store_width_m <= 0 or store_depth_m <= 0:
        messages.append("Store width and depth must be greater than zero.")

    if inputs.get("entrance_position") in {"left", "right"}:
        required_width = 2 * entrance_margin_m + entrance_width_m
        if store_width_m < required_width:
            messages.append(
                f"Frontage width is too small for {inputs.get('entrance_position')} entrance. Minimum required frontage is {required_width:.2f} m."
            )
    elif store_width_m < entrance_width_m:
        messages.append(f"Frontage width must be at least {entrance_width_m:.2f} m for a centered entrance.")

    if store_width_m <= 2 * float(params["wall_thickness_external_m"]):
        messages.append("Store width is too small after external wall thickness is applied.")
    if store_depth_m <= float(params["wall_thickness_external_m"]) + float(params["wall_thickness_glass_m"]):
        messages.append("Store depth is too small after north/south wall thickness is applied.")

    return {"is_valid": len(messages) == 0, "messages": messages}


def generate_store_shell(inputs: dict, params: dict) -> dict:
    if inputs["size_mode"] == "LW":
        store_width_m = float(inputs["width_m"])
        store_depth_m = float(inputs["length_m"])
        area_m2 = store_width_m * store_depth_m
    else:
        area_m2 = float(inputs["area_m2"])
        store_width_m = float(inputs["width_m"])
        store_depth_m = area_m2 / store_width_m

    outer_boundary = make_rectangle(store_width_m, store_depth_m, origin=(0.0, 0.0))
    outer_wall_t = float(params["wall_thickness_external_m"])
    glass_t = float(params["wall_thickness_glass_m"])
    entrance_width_m = float(params["entrance_width_m"])
    entrance_margin_m = float(params["entrance_corner_margin_m"])

    inner_clear = inset_rectangle(
        outer_boundary,
        left=outer_wall_t,
        right=outer_wall_t,
        bottom=glass_t,
        top=outer_wall_t,
    )

    ent_x1, ent_x2 = _entrance_opening_x_range(
        store_width_m,
        inputs["entrance_position"],
        entrance_width_m,
        entrance_margin_m,
    )

    entrance_opening = {
        "side": "south",
        "position": inputs["entrance_position"],
        "x1": ent_x1,
        "x2": ent_x2,
        "y": 0.0,
        "width_m": entrance_width_m,
        "corner_margin_m": entrance_margin_m,
    }

    return {
        "step": 1,
        "title": "Empty Store Shell",
        "orientation": "south_frontage",
        "store_band": classify_store_band(area_m2),
        "area_m2": round(area_m2, 3),
        "length_m": round(store_width_m, 3),
        "width_m": round(store_depth_m, 3),
        "outer_boundary": outer_boundary,
        "inner_clear_boundary": inner_clear,
        "walls": {
            "north": {"type": "external_solid", "thickness_m": outer_wall_t},
            "east": {"type": "external_solid", "thickness_m": outer_wall_t},
            "west": {"type": "external_solid", "thickness_m": outer_wall_t},
            "south": {"type": "glass_frontage", "thickness_m": glass_t},
        },
        "entrance_opening": entrance_opening,
        "clear_dimensions": {
            "width_m": round(store_width_m - 2 * outer_wall_t, 3),
            "depth_m": round(store_depth_m - outer_wall_t - glass_t, 3),
        },
    }
