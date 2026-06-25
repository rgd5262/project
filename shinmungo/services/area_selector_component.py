from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

APP_DIR = Path(__file__).resolve().parents[1]

area_selector_component = components.declare_component(
    "terminal_area_selector",
    path=str(APP_DIR / "components" / "area_selector"),
)
