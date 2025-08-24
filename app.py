from __future__ import annotations

import sys
from pathlib import Path
import traceback
import streamlit as st

from css_minimal_hook import css_start, css_end

# ================= Project setup =================
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))  # local imports first

# Optional user modules (graceful import so nothing breaks)
try:
    import modules.advice_engine as advice_engine  # type: ignore
except Exception:
    advice_engine = None
try:
    import modules.linking as linking  # type: ignore
except Exception:
    linking = None
try:
    import modules.legal_modes as legal_modes  # type: ignore
except Exception:
    legal_modes = None

# ================= CSS module hook =================
try:
    from stylekit import load as load_css, open_div, close_div  # type: ignore
except Exception:
    # If stylekit.py is missing, make no-op shims so the app still works
    def load_css(_paths): pass
    def open_div(_cls: str): pass
    def close_div(): pass

def css_hook(answering: bool) -> None:
    """Load modular CSS and open a scoped wrapper. No JS, no monkeypatch."""
    try:
        load_css([
            str(ROOT / "styles/base.css"),
            str(ROOT / "styles/components/chatbar.css"),
            str(ROOT / "styles/components/uploader.css"),
        ])
        if answering:
            load_css([str(ROOT / "styles/states/answering.css")])
        open_div(f'app {"answering" if answering else "idle"}')
    except Exception:
        pass  # CSS가 실패해도 로직은 그대로 진행

# ================= State helpers ===================
def _init_state():
    ss = st.session_state
    ss.setdefault("messages", [])
    ss.setdefault("chat_started", False)
    ss.setdefault("_pending_user_q", False)
    ss.setdefault("_pending_text", "")

def _push_user_from_pending() -> str:
    """Convert pending input to a concrete user turn (single-run)."""
    ss = st.session_state
    if not ss.get("_pending_user_q"):
        return ""
    text = (ss.get("_pending_text") or "").strip()
    # clear immediately to avoid latching
    ss["_pending_user_q"] = False
    ss["_pending_text"] = ""
    if text:
        ss["messages"].append({"role": "user", "content": text})
        ss["chat_started"] = True
    return text

# ================= Render helpers ==================
def render_pre_chat_center() -> None:
    st.markdown("### 무엇을 도와드릴까요?")
    st.file_uploader("Drag and drop files here", key="first_files", accept_multiple_files=True)
    col1, col2 = st.columns([4, 1])
    with col1:
        text = st.text_input("질문을 입력해 주세요...", key="first_input")
    with col2:
        if st.button("전송", key="first_send") and text.strip():
            st.session_state["_pending_user_q"] = True
            st.session_state["_pending_text"] = text.strip()
            st.rerun()

def render_messages() -> None:
    for m in st.session_state.get("messages", []):
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            st.markdown(f"**🙋 질문:** {content}")
        else:
            st.markdown(content)

def render_bottom_chatbar() -> None:
    text = st.chat_input("법령에 대한 질문을 입력하거나, 인터넷 URL, 관련 문서를 첨부해서 문의해 보세요…")
    if text and text.strip():
        st.session_state["_pending_user_q"] = True
        st.session_state["_pending_text"] = text.strip()
        st.rerun()

def render_bottom_uploader() -> None:
    st.file_uploader("첨부 파일", key="bottom_files", accept_multiple_files=True)

# ================= Domain actions ==================
def generate_answer(user_q: str) -> str:
    """Use user's advice_engine if available; otherwise echo back safely."""
    if advice_engine and hasattr(advice_engine, "answer"):
        try:
            return str(advice_engine.answer(user_q))  # type: ignore[attr-defined]
        except Exception:
            traceback.print_exc()
            return "처리 중 오류가 발생했어요. 입력만 에코합니다:\n\n" + user_q
    return f"**요청하신 내용**\n\n> {user_q}\n\n(임시 응답: advice_engine.answer()가 없어 에코로 대체)"

def render_search_results(user_q: str) -> None:
    st.markdown("### 📚 통합 검색 결과")
    try:
        if linking and hasattr(linking, "search"):
            results = linking.search(user_q)  # type: ignore[attr-defined]
            if results:
                for i, r in enumerate(results, 1):
                    st.write(i, r)
            else:
                st.caption("검색 결과 없음")
        else:
            st.caption("검색 모듈(linking.py)이 없어 샘플 메시지만 표시합니다.")
    except Exception:
        st.caption("검색 중 오류가 발생했습니다.")

# ========================== APP ====================
def main():
    st.set_page_config(page_title="법제처 법무 상담사", layout="wide")
    _init_state()

    # 1) pending -> concrete user turn for this run
    user_q = _push_user_from_pending()

    # 2) Determine answering (single-run flag)
    ANSWERING = bool(user_q)
    css_start(ANSWERING)

    # 3) CSS modules (scoped to .app wrapper; no global side-effects)

    # 4) Pre-chat (first screen)
    if (not st.session_state.get("chat_started", False)) and (not ANSWERING):
        # 중앙 히어로 (스코프 한정)
        from stylekit import open_div as _open, close_div as _close  # type: ignore
        _open("center-hero")
        render_pre_chat_center()
        _close()
        try: close_div()
        except Exception: pass
        st.stop()

    # 5) Messages
    render_messages()

    # 6) Answer this turn
    if ANSWERING:
        answer = generate_answer(user_q)
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        # (optional) integrated search
        render_search_results(user_q)

    # 7) Bottom chatbar & uploader (only when not answering)
    if not ANSWERING:
        from stylekit import open_div as _open, close_div as _close  # type: ignore
        _open("chatbar");   render_bottom_chatbar();  _close()
        _open("uploader");  render_bottom_uploader(); _close()

    try: close_div()
    except Exception: pass
try:
    css_end()
except Exception:
    pass

if __name__ == "__main__":
    main()
