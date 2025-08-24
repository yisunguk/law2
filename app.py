from __future__ import annotations

import sys
from pathlib import Path
import traceback
import streamlit as st

# ---------------- Optional project modules ----------------
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))  # prefer local modules

try:
    import modules.advice_engine as advice_engine  # type: ignore
except Exception:
    advice_engine = None  # graceful fallback

try:
    import modules.linking as linking  # type: ignore
except Exception:
    linking = None

try:
    import modules.legal_modes as legal_modes  # type: ignore
except Exception:
    legal_modes = None

# ---------------- CSS ONLY (minimal hook) -----------------
try:
    from css_minimal_hook import css_start, css_end  # type: ignore
except Exception:
    # If hook file is missing, make no-ops so logic keeps working
    def css_start(*_a, **_k): pass
    def css_end(*_a, **_k): pass


# ======================= STATE ============================
def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("messages", [])
    ss.setdefault("chat_started", False)
    ss.setdefault("_pending_user_q", False)
    ss.setdefault("_pending_text", "")


def _push_user_from_pending() -> str:
    """Convert pending text to a concrete user message once per run."""
    ss = st.session_state
    if not ss.get("_pending_user_q"):
        return ""
    text = (ss.get("_pending_text") or "").strip()
    # reset flags immediately to avoid latching
    ss["_pending_user_q"] = False
    ss["_pending_text"] = ""
    if text:
        ss["messages"].append({"role": "user", "content": text})
        ss["chat_started"] = True
    return text


# ======================= UI PARTS =========================
def render_pre_chat_center() -> None:
    """First screen center area: uploader + input + send button."""
    st.markdown("## 무엇을 도와드릴까요?")
    st.caption("Drag and drop files here")
    st.file_uploader("Drag and drop files here", key="first_files", accept_multiple_files=True)
    col1, col2 = st.columns([10, 1])
    with col1:
        text = st.text_input("질문을 입력해 주세요...", key="first_input")
    with col2:
        if st.button("전송", key="first_send") and text.strip():
            st.session_state["_pending_user_q"] = True
            st.session_state["_pending_text"] = text.strip()
            st.rerun()


def render_messages() -> None:
    """Render conversation history."""
    for msg in st.session_state.get("messages", []):
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "user":
            st.markdown(f"**🙋 질문:** {content}")
        else:
            st.markdown(content)


def render_bottom_chatbar() -> None:
    """Bottom chat input (Streamlit chat_input)."""
    text = st.chat_input("법령에 대한 질문을 입력하거나, 인터넷 URL, 관련 문서를 첨부해서 문의해 보세요…")
    if text and text.strip():
        st.session_state["_pending_user_q"] = True
        st.session_state["_pending_text"] = text.strip()
        st.rerun()


def render_bottom_uploader() -> None:
    """Bottom uploader (kept visible when not answering)."""
    st.file_uploader("첨부 파일", key="bottom_files", accept_multiple_files=True)


# ======================= DOMAIN ===========================
def _safe_str(x) -> str:
    try:
        return str(x)
    except Exception:
        return repr(x)


def generate_answer(user_q: str) -> str:
    """Use user's advice_engine.answer() if provided, else echo."""
    if advice_engine and hasattr(advice_engine, "answer"):
        try:
            return _safe_str(advice_engine.answer(user_q))  # type: ignore[attr-defined]
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


# ======================= APP ==============================
def main() -> None:
    st.set_page_config(page_title="법제처 법무 상담사", layout="wide")
    _init_state()

    # 1) Move pending user text -> concrete message for this run
    user_q = _push_user_from_pending()

    # 2) Decide answering state for this run
    ANSWERING = bool(user_q)

    # 3) CSS-only hook (scoped; no JS, no monkeypatch)
    css_start(ANSWERING)

    # 4) First screen (only when chat not started and not answering)
    if (not st.session_state.get("chat_started", False)) and (not ANSWERING):
        render_pre_chat_center()
        # Do not close css here; keep the wrapper for consistent scope
        st.stop()

    # 5) Render history
    render_messages()

    # 6) Generate answer for this turn
    if ANSWERING:
        answer = generate_answer(user_q)
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        render_search_results(user_q)

    # 7) Show bottom input/uploader when not answering
    if not ANSWERING:
        render_bottom_chatbar()
        render_bottom_uploader()

    # 8) Close CSS wrapper
    try:
        css_end()
    except Exception:
        pass


if __name__ == "__main__":
    main()
