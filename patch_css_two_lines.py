
import argparse, re, sys
from pathlib import Path

CSS_HOOK_IMPORT = "from css_minimal_hook import css_start, css_end"
CSS_START_LINE  = "css_start(ANSWERING)"
CSS_END_BLOCK   = "try:\n    css_end()\nexcept Exception:\n    pass\n"

ANSWERING_PATTERNS = [
    r"^\s*ANSWERING\s*=\s*.+$",
    r"^\s*ANSWERING\s*:\s*bool\s*=\s*.+$",
]

HOOK_CODE = r'''from __future__ import annotations
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
'''

ANSWERING_CSS = r'''/* Hide only main-area inputs/uploader while answering */
.app.answering [data-testid="stAppViewContainer"] section main section[data-testid="stChatInput"],
.app.answering [data-testid="stAppViewContainer"] section main [data-testid="stFileUploader"],
.app.answering [data-testid="stAppViewContainer"] section main [data-testid="stFileUploaderDropzone"],
.app.answering #chatbar-fixed {
  display: none !important;
}
'''

def ensure_css_assets(project_root: Path) -> None:
    hook_path = project_root / "css_minimal_hook.py"
    if not hook_path.exists():
        hook_path.write_text(HOOK_CODE, encoding="utf-8")
    states_dir = project_root / "styles" / "states"
    states_dir.mkdir(parents=True, exist_ok=True)
    ans_css = states_dir / "answering.css"
    if not ans_css.exists():
        ans_css.write_text(ANSWERING_CSS, encoding="utf-8")

def patch_app(app_path: Path) -> None:
    src = app_path.read_text(encoding="utf-8", errors="ignore")
    original = src

    # add import if missing
    if CSS_HOOK_IMPORT not in src:
        m = list(re.finditer(r"^(import\s+[^\n]+|from\s+[^\n]+import\s+[^\n]+)\s*$", src, re.MULTILINE))
        insert_at = m[-1].end() if m else 0
        src = src[:insert_at] + "\n" + CSS_HOOK_IMPORT + "\n" + src[insert_at:]

    # add css_start after ANSWERING=
    if CSS_START_LINE not in src:
        m_ans = None
        for pat in ANSWERING_PATTERNS:
            m_ans = re.search(pat, src, flags=re.MULTILINE)
            if m_ans:
                break
        if m_ans:
            line_end = src.find("\n", m_ans.end())
            if line_end == -1:
                line_end = len(src)
            insertion_point = line_end + 1
            src = src[:insertion_point] + CSS_START_LINE + "\n" + src[insertion_point:]
        else:
            print("[warn] ANSWERING assignment not found; skipped css_start insertion.")

    # add css_end near EOF
    if "css_end()" not in src:
        m_main = re.search(r'^\s*if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:\s*$', src, flags=re.MULTILINE)
        if m_main:
            src = src[:m_main.start()] + CSS_END_BLOCK + src[m_main.start():]
        else:
            if not src.endswith("\n"):
                src += "\n"
            src += CSS_END_BLOCK

    # write backup and result
    backup = app_path.with_suffix(".py.bak")
    backup.write_text(original, encoding="utf-8")
    app_path.write_text(src, encoding="utf-8")
    print(f"[ok] Patched {app_path.name}. Backup -> {backup.name}")

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Insert two CSS hook lines into Streamlit app.py safely.")
    ap.add_argument("app", nargs="?", default="app.py", help="Path to Streamlit app file (default: app.py)")
    args = ap.parse_args()

    app_path = Path(args.app).resolve()
    if not app_path.exists():
        print(f"[err] {app_path} not found."); sys.exit(1)

    ensure_css_assets(app_path.parent)
    patch_app(app_path)
    print("[next] Run: streamlit run", app_path)

if __name__ == "__main__":
    main()
