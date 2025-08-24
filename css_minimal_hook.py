from __future__ import annotations
from pathlib import Path
import streamlit as st

try:
    from stylekit import load as load_css, open_div, close_div  # type: ignore
except Exception:
    def load_css(_): pass
    def open_div(_): pass
    def close_div(): pass

def css_start(answering: bool, root: str | Path | None = None) -> None:
    root = Path(root) if root else Path(__file__).resolve().parent
    try:
        load_css([
            str(root / "styles/base.css"),
            str(root / "styles/components/chatbar.css"),
            str(root / "styles/components/uploader.css"),
        ])
        if answering:
            load_css([str(root / "styles/states/answering.css")])
        open_div(f'app {"answering" if answering else "idle"}')
    except Exception:
        pass

def css_end() -> None:
    try:
        close_div()
    except Exception:
        pass
