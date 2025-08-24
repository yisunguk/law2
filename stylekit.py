
# stylekit.py — tiny CSS loader & scoped wrappers for Streamlit
from pathlib import Path
from functools import lru_cache
import streamlit as st

@lru_cache(maxsize=256)
def _read(p:str)->str:
    return Path(p).read_text(encoding="utf-8")

def load(paths:list[str])->None:
    """Inject CSS files in order. Missing files are ignored."""
    bundle = []
    for p in paths:
        try:
            if Path(p).exists():
                bundle.append(_read(p))
        except Exception:
            pass
    if bundle:
        st.markdown("""<style>{}</style>""".format("\n".join(bundle)), unsafe_allow_html=True)

def open_div(cls:str)->None:
    st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)

def close_div()->None:
    st.markdown('</div>', unsafe_allow_html=True)
