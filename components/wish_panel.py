"""Wish input + Akinator-style narrowing UI."""
import html
import streamlit as st

from simulation.scenarios import RECOMMENDED_WISHES


def inspiration(on_pick_key="pick_reco"):
    st.markdown('<div class="gp-card"><h3>Need inspiration?</h3>'
                '<p class="gp-muted">The Genie suggests:</p></div>', unsafe_allow_html=True)
    picked = None
    cols = st.columns(2)
    for i, (emoji, text, _domain) in enumerate(RECOMMENDED_WISHES):
        if cols[i % 2].button(f"{emoji}  {text}", key=f"{on_pick_key}_{i}", use_container_width=True):
            picked = text
    return picked


def wish_input(wish_no: int, prefill: str = ""):
    st.markdown(f'<div class="gp-card"><h3>Wish {wish_no} of 3</h3>'
                f'<p class="gp-muted">Tell me what you want to change about the campus. '
                f'Anything. I dare you.</p></div>', unsafe_allow_html=True)
    with st.form(key=f"wish_form_{wish_no}", clear_on_submit=False):
        text = st.text_input("Your wish", value=prefill, key=f"wish_text_{wish_no}",
                             placeholder="e.g. I want classes to start at 10 AM",
                             label_visibility="collapsed")
        submitted = st.form_submit_button("Make a wish  ✨", type="primary")
    return (text.strip() if submitted and text.strip() else None)


def akinator_question(q: dict, wish_no: int, step: int):
    """Render one narrowing question; return the chosen value or None."""
    st.markdown(
        f'<div class="gp-card"><span class="gp-muted">Narrowing · question {step+1}</span>'
        f'<h3 style="margin:.2rem 0">{html.escape(q["genie"])}</h3>'
        f'<p class="gp-muted">{html.escape(q["prompt"])}</p></div>',
        unsafe_allow_html=True)
    choice = None
    cols = st.columns(2)
    for i, opt in enumerate(q["options"]):
        if cols[i % 2].button(opt["label"], key=f"akq_{wish_no}_{step}_{i}",
                              use_container_width=True):
            choice = opt["value"]
    return choice


def confirm_card(sentence: str, wish_no: int):
    st.markdown(
        f'<div class="gp-card" style="border-color:#4fe3ff55">'
        f'<h3>🧞 “Ahhh. NOW I understand.”</h3>'
        f'<p style="font-size:1.05rem">{html.escape(sentence)}</p>'
        f'<p class="gp-muted">If that\'s wrong, restart the wish. If it\'s right — let\'s break the campus.</p>'
        f'</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    go = c1.button("⚡ MAKE IT HAPPEN", key=f"make_{wish_no}", type="primary", use_container_width=True)
    redo = c2.button("↺ Restart this wish", key=f"redo_{wish_no}", use_container_width=True)
    return go, redo
