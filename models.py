from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class BaselineState:
    inputs: Dict[str, Any]
    params: Dict[str, Any]
    shell: Dict[str, Any] = field(default_factory=dict)
    zones: Dict[str, Any] = field(default_factory=dict)
    walls_internal: Dict[str, Any] = field(default_factory=dict)
    bands: Dict[str, Any] = field(default_factory=dict)
    display: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    drawing: Dict[str, Any] = field(default_factory=dict)
    exports: Dict[str, Any] = field(default_factory=dict)
    status: str = "initialized"
