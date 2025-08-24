from __future__ import annotations

import sys
from pathlib import Path
import traceback
import streamlit as st

# ========= Project setup =========
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))  # prefer local modules in ./

# ---- Optional modules (fail-safe) ----
def _try_import(modname: str):
    try:
        return __import__(modname, fromlist=["*"])
    except Exception:
        return None

advice_engine   = _try_import("modules.advice_engine")
linking         = _try_import("modules.linking")
legal_modes     = _try_import("modules.legal_modes")
external        = _try_import("external_content")   # 좌측 패널 등
chatbar_ext     = _try_import("chatbar")            # 커스텀 입력바

# ---- CSS only hook (no JS) ----
try:
    from css_minimal_hook import css_start, css_end  # type: ignore
except Exception:
    def css_start(*_a, **_k): pass
    def css_end(*_a, **_k): pass

# ========= STATE =========
def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("messages", [])
    ss.setdefault("chat_started", False)
    ss.setdefault("_pending_user_q", False)
    ss.setdefault("_pending_text", "")

def _push_user_from_pending() -> str:
    ss = st.session_state
    if not ss.get("_pending_user_q"):
        return ""
    text = (ss.get("_pending_text") or "").strip()
    ss["_pending_user_q"] = False
    ss["_pending_text"] = ""
    if text:
        ss["messages"].append({"role": "user", "content": text})
        ss["chat_started"] = True
    return text

# ========= UI helpers =========
def render_left_panel() -> None:
    """좌측 커스텀 패널(있으면 그대로 호출)"""
    if external:
        # external_content.py 에서 제공하는 함수가 있다면 그대로 호출
        for fn_name in ("render_link_builder", "render_left_panel", "render_sidebar"):
            if hasattr(external, fn_name):
                try:
                    getattr(external, fn_name)()
                    return
                except Exception:
                    traceback.print_exc()
    # 안전한 기본 대체(아무 것도 없으면 빈 공간만 유지)
    st.markdown("### 링크 생성기 (무인증)")
    st.caption("external_content.render_left_panel() 를 찾을 수 없어 기본 패널을 표시합니다.")

def render_center_pre_chat() -> None:
    st.caption("Drag and drop files here")
    st.file_uploader("Drag and drop files here", key="first_files", accept_multiple_files=True)
    col1, col2, col3 = st.columns([8, 1, 1])
    with col1:
        txt = st.text_input("질문을 입력해 주세요...", key="first_input")
    with col2:
        sent = st.button("전송", key="first_send")
        if sent and txt.strip():
            st.session_state["_pending_user_q"] = True
            st.session_state["_pending_text"] = txt.strip()
            st.rerun()
    with col3:
        st.empty()

def render_center_messages() -> None:
    for m in st.session_state.get("messages", []):
        role, content = m.get("role"), m.get("content", "")
        if role == "user":
            st.markdown(f"**🙋 질문:** {content}")
        else:
            st.markdown(content)

def render_bottom_input() -> None:
    """하단 입력 바: chatbar.py > render() 가 있으면 사용"""
    if chatbar_ext and hasattr(chatbar_ext, "render"):
        try:
            if chatbar_ext.render():
                return
        except Exception:
            traceback.print_exc()

    # 기본 입력바 (Streamlit chat_input)
    text = st.chat_input("법령에 대한 질문을 입력하거나, 인터넷 URL, 관련 문서를 첨부해서 문의해 보세요…")
    if text and text.strip():
        st.session_state["_pending_user_q"] = True
        st.session_state["_pending_text"] = text.strip()
        st.rerun()

def render_bottom_uploader() -> None:
    st.file_uploader("첨부 파일", key="bottom_files", accept_multiple_files=True)

# ========= Domain =========
def generate_answer(user_q: str) -> str:
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

# ========= APP =========
def main() -> None:
    st.set_page_config(page_title="법제처 법무 상담사", layout="wide")
    _init_state()

    # 1) capture pending input
    user_q = _push_user_from_pending()
    ANSWERING = bool(user_q)

    # 2) CSS-only
    css_start(ANSWERING)

    # 3) 레이아웃: 좌/중/우
    left, center, right = st.columns([28, 46, 26])

    with left:
        render_left_panel()

    with center:
        st.markdown("### Drag and drop files here")
        if (not st.session_state.get("chat_started")) and (not ANSWERING):
            render_center_pre_chat()
        render_center_messages()

        if ANSWERING:
            ans = generate_answer(user_q)
            st.session_state["messages"].append({"role": "assistant", "content": ans})

        # 하단 입력·업로더: 답변 중이 아닐 때만
        if not ANSWERING:
            render_bottom_input()
            render_bottom_uploader()

    with right:
        if user_q:
            render_search_results(user_q)

    # 4) CSS end
    try:
        css_end()
    except Exception:
        pass

if __name__ == "__main__":
    main()
