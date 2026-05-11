"""pages/1_WebManual.py — 運用者向け WebManual ビュー。"""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from kabusys.config import Settings

st.set_page_config(page_title="WebManual", layout="wide", page_icon="📘")
st.title("📘 WebManual — 運用マニュアル")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _manual_dir() -> Path:
    return _project_root() / "documents" / "WebManual"


def _manual_order() -> list[str]:
    return [
        "INDEX.md",
        "A_Overview.md",
        "A_StrategyFlow.md",
        "A_OperationsCycle.md",
        "B_CoreSetup.md",
        "C_PaperTrading.md",
        "D_LiveOperation.md",
        "E_FailureRecovery.md",
        "MAPPING.md",
        "INDEX_DESIGN.md",
    ]


def _display_name(filename: str) -> str:
    names = {
        "INDEX.md": "INDEX",
        "A_Overview.md": "A. Overview",
        "A_StrategyFlow.md": "A. Strategy Flow",
        "A_OperationsCycle.md": "A. Operations Cycle",
        "B_CoreSetup.md": "B. Core Setup",
        "C_PaperTrading.md": "C. Paper Trading",
        "D_LiveOperation.md": "D. Live Operation",
        "E_FailureRecovery.md": "E. Failure Recovery",
        "MAPPING.md": "Mapping",
        "INDEX_DESIGN.md": "Index Design",
    }
    return names.get(filename, filename)


def _load_manuals() -> dict[str, Path]:
    manual_dir = _manual_dir()
    existing = {path.name: path for path in manual_dir.glob("*.md")}
    ordered: dict[str, Path] = {}
    for name in _manual_order():
        path = existing.pop(name, None)
        if path is not None:
            ordered[name] = path
    for name in sorted(existing):
        ordered[name] = existing[name]
    return ordered


def _extract_headings(markdown_text: str) -> list[str]:
    return [
        line.strip() for line in markdown_text.splitlines() if re.match(r"^#{1,3}\s+", line.strip())
    ]


def _rewrite_relative_links(markdown_text: str) -> str:
    """相対 Markdown リンクは Streamlit 内ナビゲーションの案内文に置き換える。"""

    def repl(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        if target.startswith("./") and target.endswith(".md"):
            return f"`{label}`"
        return match.group(0)

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, markdown_text)


settings = Settings()
manuals = _load_manuals()

if not manuals:
    st.error("documents/WebManual に Markdown ファイルが見つかりません。")
    st.stop()

manual_names = list(manuals.keys())
current_name = st.session_state.get("webmanual_current", "INDEX.md")
if current_name not in manuals:
    current_name = manual_names[0]

with st.sidebar:
    st.caption(f"環境: **{settings.env}**")
    selected_name = st.selectbox(
        "表示ドキュメント",
        manual_names,
        index=manual_names.index(current_name),
        format_func=_display_name,
    )
    st.session_state["webmanual_current"] = selected_name
    if st.button("🔄 Refresh"):
        st.rerun()

selected_path = manuals[selected_name]
content = selected_path.read_text(encoding="utf-8")
rendered_content = _rewrite_relative_links(content)
headings = _extract_headings(content)

nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
current_index = manual_names.index(selected_name)

with nav_col1:
    if current_index > 0 and st.button("← Prev", use_container_width=True):
        st.session_state["webmanual_current"] = manual_names[current_index - 1]
        st.rerun()

with nav_col2:
    st.markdown(
        f"**{_display_name(selected_name)}**  \n`{selected_path.relative_to(_project_root())}`"
    )

with nav_col3:
    if current_index < len(manual_names) - 1 and st.button("Next →", use_container_width=True):
        st.session_state["webmanual_current"] = manual_names[current_index + 1]
        st.rerun()

info_col1, info_col2 = st.columns([2, 1])
with info_col1:
    st.info(
        "WebManual 内の相対リンクは、左のドキュメント選択または Prev / Next で移動してください。"
    )
with info_col2:
    with st.expander("見出し一覧", expanded=False):
        if headings:
            for heading in headings:
                st.write(heading)
        else:
            st.caption("見出しはありません。")

st.markdown(rendered_content)
