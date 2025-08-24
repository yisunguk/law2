
from pathlib import Path
import re, sys

APP = Path(sys.argv[1] if len(sys.argv)>1 else "app.py").resolve()
src = APP.read_text(encoding="utf-8", errors="ignore")
orig = src

# 1) Ensure import
if "from css_minimal_hook import css_start, css_end" not in src:
    m = list(re.finditer(r"^(import\s+[^\n]+|from\s+[^\n]+import\s+[^\n]+)\s*$", src, re.MULTILINE))
    insert_at = m[-1].end() if m else 0
    src = src[:insert_at] + "\nfrom css_minimal_hook import css_start, css_end\n" + src[insert_at:]

# 2) Replace css_hook -> css_start
src = src.replace("css_hook(ANSWERING)", "css_start(ANSWERING)")

# 3) Find ANSWERING assignment to capture its indentation
m_ans = re.search(r"^(\s*)ANSWERING\s*=\s*.+$", src, flags=re.MULTILINE)
indent = m_ans.group(1) if m_ans else ""

# 4) Normalize indentation of css_start(ANSWERING) to match ANSWERING line
def repl_indent(m):
    return f"{indent}css_start(ANSWERING)"
src = re.sub(r"^\s*css_start\(ANSWERING\)\s*$", repl_indent, src, flags=re.MULTILINE)

# 5) Ensure css_end() exists before EOF (once)
if "css_end()" not in src:
    block = "\ntry:\n    css_end()\nexcept Exception:\n    pass\n"
    # try to insert before if __name__ == '__main__'
    m_main = re.search(r'^\s*if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:\s*$', src, flags=re.MULTILINE)
    if m_main:
        src = src[:m_main.start()] + block + src[m_main.start():]
    else:
        if not src.endswith("\n"):
            src += "\n"
        src += block

# Write backup and patched
APP.with_suffix(".py.bak2").write_text(orig, encoding="utf-8")
APP.write_text(src, encoding="utf-8")
print("[ok] Fixed indentation and imports for CSS hook on", APP)
