from __future__ import annotations

def make_rectangle(length: float, width: float, origin=(0.0, 0.0)) -> dict:
    x0, y0 = origin
    return {"x": float(x0), "y": float(y0), "length": float(length), "width": float(width)}

def rect_area(rect: dict) -> float:
    return float(rect["length"]) * float(rect["width"])

def north_edge(rect: dict) -> dict:
    return {"x1": rect["x"], "y1": rect["y"] + rect["width"], "x2": rect["x"] + rect["length"], "y2": rect["y"] + rect["width"]}

def south_edge(rect: dict) -> dict:
    return {"x1": rect["x"], "y1": rect["y"], "x2": rect["x"] + rect["length"], "y2": rect["y"]}

def inset_rectangle(rect: dict, left: float = 0.0, right: float = 0.0, bottom: float = 0.0, top: float = 0.0) -> dict:
    return {
        "x": rect["x"] + left,
        "y": rect["y"] + bottom,
        "length": max(0.0, rect["length"] - left - right),
        "width": max(0.0, rect["width"] - bottom - top),
    }

def band_from_south(rect: dict, depth: float) -> dict:
    return {"x": rect["x"], "y": rect["y"], "length": rect["length"], "width": min(depth, rect["width"])}

def vertical_band(rect: dict, center_x: float, width: float) -> dict:
    x = max(rect["x"], center_x - width / 2.0)
    max_x = rect["x"] + rect["length"]
    if x + width > max_x:
        x = max(rect["x"], max_x - width)
    return {"x": x, "y": rect["y"], "length": min(width, rect["length"]), "width": rect["width"]}

def left_strip(rect: dict, depth: float) -> dict:
    return {"x": rect["x"], "y": rect["y"], "length": min(depth, rect["length"]), "width": rect["width"]}

def right_strip(rect: dict, depth: float) -> dict:
    return {"x": rect["x"] + max(0.0, rect["length"] - depth), "y": rect["y"], "length": min(depth, rect["length"]), "width": rect["width"]}

def top_strip(rect: dict, depth: float) -> dict:
    return {"x": rect["x"], "y": rect["y"] + max(0.0, rect["width"] - depth), "length": rect["length"], "width": min(depth, rect["width"])}

def intersects(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["length"] <= b["x"] or
        b["x"] + b["length"] <= a["x"] or
        a["y"] + a["width"] <= b["y"] or
        b["y"] + b["width"] <= a["y"]
    )

def rect_center(rect: dict) -> tuple[float, float]:
    return rect["x"] + rect["length"] / 2.0, rect["y"] + rect["width"] / 2.0

def classify_rect(rect: dict) -> tuple[float, float]:
    return rect["length"], rect["width"]
