"""
GENIEPOLIS — a Genie-powered campus what-if simulator.
HackCulture · Track B · Creative Campus Intelligence.

Run:  streamlit run app.py
"""
import os
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Streamlit Community Cloud injects config via st.secrets, not a .env file.
# Copy the three keys into the environment so genie_client (which uses os.getenv)
# works identically whether run locally or hosted.
try:
    for _k in ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "GENIE_SPACE_ID"):
        if not os.getenv(_k) and _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

from data.synthetic_data import generate_all, build_snapshot
from databricks.genie_client import GenieBridge, GENIE_CONNECTED
from simulation.scenarios import (classify, get_tree, build_structured_wish, confirm_sentence,
                                  GENIE_REACTIONS)
from simulation.engine import simulate
from simulation.relationships import label as node_label

from components.style import inject_css, header, synthetic_tag
from components.genie import genie_say, genie_appears, wish_progress, magic_transition
from components.campus import render_campus, building_panel, conditions_strip, building_buttons
from components.wish_panel import inspiration, wish_input, akinator_question, confirm_card
from components.ripple import ripple_animation, ripple_origin_caption
from components.impact import final_impact_screen, alternatives
from components.stats import campus_pulse

st.set_page_config(page_title="GENIEPOLIS", page_icon="✨", layout="wide")
inject_css()


# ---------------------------------------------------------------------------
# resources
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _data():
    return generate_all()


def get_bridge(data):
    if "bridge" not in st.session_state:
        st.session_state.bridge = GenieBridge(data)
    return st.session_state.bridge


DATA = _data()
BRIDGE = get_bridge(DATA)

SS = st.session_state
SS.setdefault("phase", "campus")           # campus | genie_intro | wish | pulse
SS.setdefault("wish_no", 1)
SS.setdefault("stage", "input")            # input|narrow|confirm|magic|ripple|impact|alternatives|complete
SS.setdefault("wish_text", "")
SS.setdefault("prefill", "")
SS.setdefault("domain", None)
SS.setdefault("q_index", 0)
SS.setdefault("answers", {})
SS.setdefault("sim", None)
SS.setdefault("explanation", "")
SS.setdefault("session_wishes", [])
SS.setdefault("selected_building", "academic_block")
SS.setdefault("theme", "default")


def reset_wish(keep_prefill=""):
    SS.stage = "input"
    SS.wish_text = ""
    SS.prefill = keep_prefill
    SS.domain = None
    SS.q_index = 0
    SS.answers = {}
    SS.sim = None
    SS.explanation = ""


def mode_badge():
    if BRIDGE.mode == GENIE_CONNECTED:
        return '<span class="gp-badge ok">● Databricks Genie connected</span>'
    return '<span class="gp-badge demo">● Demo fallback mode</span>'


header(mode_badge())
st.caption(BRIDGE.status_note)


# ---------------------------------------------------------------------------
# Genie data Q&A (uses real Databricks Genie when connected)
# ---------------------------------------------------------------------------
def genie_data_box(where: str):
    with st.expander("💬 Ask the Campus Genie a data question  (Databricks Genie)"):
        q = st.text_input("Question", key=f"gq_{where}",
                          placeholder="Which buildings have the highest occupancy?")
        c1, c2 = st.columns([1, 3])
        if c1.button("Ask", key=f"gqb_{where}") and q.strip():
            with st.spinner("Genie is consulting the campus tables..."):
                ans = BRIDGE.data_answer(q.strip())
            st.session_state[f"gans_{where}"] = ans
        ans = st.session_state.get(f"gans_{where}")
        if ans:
            src = {"genie": "Databricks Genie", "demo": "Demo mode (synthetic)",
                   "demo_fallback": "Demo fallback"}.get(ans.get("source"), ans.get("source"))
            genie_say(ans.get("text", ""))
            st.caption(f"source: {src}" + (f" · {ans['note']}" if ans.get("note") else ""))
            if ans.get("sql"):
                st.code(ans["sql"], language="sql")
            if ans.get("rows"):
                import pandas as pd
                st.dataframe(pd.DataFrame(ans["rows"], columns=ans.get("columns")),
                             use_container_width=True, hide_index=True)


# ===========================================================================
# PHASE 1 — CAMPUS
# ===========================================================================
def phase_campus():
    st.markdown("### 🏙️ See the campus")
    st.markdown('<p class="gp-muted">This is a synthetic digital twin of BMS College of Engineering. '
                'Click any building to inspect its live conditions. Everything here is synthetic.</p>',
                unsafe_allow_html=True)
    hour = st.slider("🕒 Scrub the day — see how crowd & traffic build and fade",
                     min_value=6, max_value=22, value=SS.get("explore_hour", 16),
                     step=1, format="%d:00", key="explore_hour")
    view = {**DATA, "snapshot": build_snapshot(DATA, hour)}

    left, right = st.columns([1.55, 1])
    with left:
        clicked = render_campus(view, theme=SS.theme, key=f"campus_explore_{hour}",
                                height=560, title_suffix=f"· {hour:02d}:00")
        if clicked:
            SS.selected_building = clicked
        with st.expander("Prefer buttons? Pick a building"):
            b = building_buttons("explore")
            if b:
                SS.selected_building = b
        synthetic_tag()
    with right:
        building_panel(SS.selected_building, view)
        conditions_strip(view, hour)

    st.write("")
    genie_data_box("campus")
    st.write("")
    c1, c2, c3 = st.columns([1, 1, 1])
    if c1.button("🧞 Summon the Genie  →", type="primary", use_container_width=True):
        SS.phase = "genie_intro"
        st.rerun()
    if c2.button("🫀 Skip to Campus Pulse", use_container_width=True):
        SS.phase = "pulse"
        st.rerun()


# ===========================================================================
# PHASE 2 — GENIE INTRO
# ===========================================================================
def phase_genie_intro():
    genie_appears()
    st.write("")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="gp-card"><h3>The rules</h3>'
                    '<p class="gp-muted">You get <b>three independent wishes</b>. '
                    'Wish 1 finishes completely before Wish 2 begins. For each wish I will '
                    'ask a few narrowing questions, confirm what you <i>really</i> meant, then '
                    'show how it ripples across the whole campus.</p></div>', unsafe_allow_html=True)
    with c2:
        pick = inspiration("reco_intro")
        if pick:
            reset_wish(keep_prefill=pick)
            SS.phase = "wish"
            st.rerun()
    st.write("")
    if st.button("✨ I'm ready — Wish 1", type="primary"):
        reset_wish()
        SS.phase = "wish"
        st.rerun()


# ===========================================================================
# PHASE 3 — THE WISH (repeats 3x)
# ===========================================================================
def phase_wish():
    wish_progress(SS.wish_no)
    st.write("")
    left, right = st.columns([1.5, 1])

    # campus with highlights once we have a simulation
    hl_d = hl_i = []
    theme = SS.theme
    if SS.sim:
        hl_d = [x["building_id"] for x in SS.sim["direct_impacts"] if x.get("building_id")]
        hl_i = [x["building_id"] for x in SS.sim["indirect_impacts"] if x.get("building_id")]
        theme = SS.sim.get("theme", SS.theme)

    with left:
        render_campus(DATA, theme=theme, highlight_direct=hl_d, highlight_indirect=hl_i,
                      key=f"campus_wish_{SS.wish_no}_{SS.stage}", height=440)
        synthetic_tag()

    with right:
        stage = SS.stage
        if stage == "input":
            _stage_input()
        elif stage == "narrow":
            _stage_narrow()
        elif stage == "confirm":
            _stage_confirm()
        elif stage in ("magic", "ripple", "impact", "alternatives", "complete"):
            genie_say("The wish is cast. Scroll down — the campus is still settling. 🌀")

    if SS.stage in ("magic", "ripple", "impact", "alternatives", "complete"):
        st.write("")
        _stage_results()


def _stage_input():
    pick = inspiration(f"reco_w{SS.wish_no}")
    if pick:
        SS.prefill = pick
        st.rerun()
    text = wish_input(SS.wish_no, prefill=SS.prefill)
    if text:
        SS.wish_text = text
        SS.domain = classify(text)
        SS.q_index = 0
        SS.answers = {}
        SS.stage = "narrow"
        st.rerun()


def _stage_narrow():
    genie_say(GENIE_REACTIONS.get(SS.domain, "Interesting. Go on."))
    tree = get_tree(SS.domain)
    if SS.q_index >= len(tree):
        SS.stage = "confirm"
        st.rerun()
        return
    q = tree[SS.q_index]
    choice = akinator_question(q, SS.wish_no, SS.q_index)
    st.caption(f"“{SS.wish_text}”  ·  narrowing {SS.q_index+1}/{len(tree)}")
    if choice is not None:
        SS.answers[q["key"]] = choice
        SS.q_index += 1
        if SS.q_index >= len(tree):
            SS.stage = "confirm"
        st.rerun()


def _stage_confirm():
    sw = build_structured_wish(SS.domain, SS.wish_text, SS.answers)
    SS.structured = sw
    sentence = confirm_sentence(sw)
    genie_say("Hold still. I'm reading the shape of your wish...", thinking=True)
    go, redo = confirm_card(sentence, SS.wish_no)
    with st.expander("structured wish (what the simulation engine receives)"):
        st.json(sw)
    if redo:
        reset_wish()
        st.rerun()
    if go:
        SS.sim = simulate(sw, DATA)
        SS.explanation = BRIDGE.explain_scenario(SS.sim)
        SS.stage = "magic"
        st.rerun()


def _stage_results():
    sim = SS.sim
    if not sim:
        return
    sc = sim["scenario"]

    if SS.stage == "magic":
        magic_transition(sc["title"])
        st.write("")
        if st.button("🌀 Reveal the ripple  →", type="primary"):
            SS.stage = "ripple"
            st.rerun()
        return

    # ---- ripple ----
    st.markdown("## 🌀 The ripple effect")
    ripple = sim.get("ripple", [])
    origin = ripple[0]["label"] if ripple else sc["title"]
    ripple_origin_caption(origin)
    c1, c2 = st.columns([1, 1])
    with c1:
        ripple_animation(ripple)
    with c2:
        genie_say(sim.get("genie_closer", ""))
        st.markdown('<div class="gp-card"><h4>Legend</h4>'
                    '<span class="pill direct">DIRECT — the wish itself</span>'
                    '<span class="pill indirect">RIPPLE — knock-on effect</span></div>',
                    unsafe_allow_html=True)
    if SS.stage == "ripple":
        if st.button("📊 See direct + indirect impacts  →", type="primary"):
            SS.stage = "impact"
            st.rerun()
        return

    # ---- impact + before/after + risk/benefit ----
    st.write("")
    final_impact_screen(sim, SS.explanation, SS.wish_no)
    if SS.stage == "impact":
        st.write("")
        if st.button("💡 Show alternative wishes  →", type="primary"):
            SS.stage = "alternatives"
            st.rerun()
        return

    # ---- alternatives + complete ----
    st.write("")
    picked = alternatives(sim, SS.wish_no)
    if picked:
        genie_say(f"“{picked}” — a wiser path. Noted for the campus record.")
    st.write("")
    genie_say(sim.get("genie_closer", ""))
    st.markdown(f'<div class="gp-card" style="text-align:center;border-color:#f6c14b55">'
                f'<h2>✅ WISH {SS.wish_no} COMPLETE</h2>'
                f'<p class="gp-muted">{"Two" if SS.wish_no==1 else "One" if SS.wish_no==2 else "Zero"} wishes remain.</p>'
                f'</div>', unsafe_allow_html=True)
    st.write("")
    if SS.wish_text not in SS.session_wishes:
        SS.session_wishes.append(SS.wish_text)

    if SS.wish_no < 3:
        if st.button(f"🧞 Wish {SS.wish_no+1} → your turn", type="primary"):
            SS.wish_no += 1
            reset_wish()
            st.rerun()
    else:
        if st.button("🫀 Your wishes are complete — see the Campus Pulse", type="primary"):
            SS.phase = "pulse"
            st.rerun()


# ===========================================================================
# PHASE 4 — CAMPUS PULSE
# ===========================================================================
def phase_pulse():
    genie_say("Your wishes are spent. But the campus? The campus is still whispering.")
    st.write("")
    campus_pulse(DATA, SS.session_wishes)
    st.write("")
    genie_data_box("pulse")
    st.write("")
    st.markdown(
        '<div class="gp-card"><h3>The GENIEPOLIS story</h3>'
        '<p>Traditional campus dashboards tell you <b>what</b> is happening. GENIEPOLIS lets students ask '
        '<b>what if?</b> — the Genie narrows the wish, a deterministic engine simulates the ripple, and '
        'Databricks Genie grounds and explains it. Repeated wishes stop being isolated complaints and '
        'become a <b>campus signal</b>.</p>'
        '<span class="gp-synthetic">All values are synthetic demonstration data</span></div>',
        unsafe_allow_html=True)
    if st.button("↺ Start over"):
        for k in list(SS.keys()):
            if k not in ("bridge",):
                del SS[k]
        st.rerun()


# ---------------------------------------------------------------------------
PHASES = {"campus": phase_campus, "genie_intro": phase_genie_intro,
          "wish": phase_wish, "pulse": phase_pulse}
PHASES.get(SS.phase, phase_campus)()

with st.sidebar:
    st.markdown("### ✨ GENIEPOLIS")
    st.caption("Three Wishes. One Campus. Infinite Ripples.")
    st.divider()
    st.write(f"**Mode:** {'Databricks Genie' if BRIDGE.mode==GENIE_CONNECTED else 'Demo fallback'}")
    if st.button("Re-check Databricks connection"):
        BRIDGE.force_recheck()
        st.rerun()
    st.caption(BRIDGE.status_note)
    st.divider()
    st.write(f"**Phase:** {SS.phase}")
    if SS.phase == "wish":
        st.write(f"Wish {SS.wish_no}/3 · stage: {SS.stage}")
    st.progress(len(SS.session_wishes) / 3.0, text=f"{len(SS.session_wishes)}/3 wishes done")
    st.divider()
    if st.button("🏙️ Campus"):
        SS.phase = "campus"; st.rerun()
    if st.button("🫀 Campus Pulse"):
        SS.phase = "pulse"; st.rerun()
    st.divider()
    st.caption("Synthetic demonstration data — not real institutional data. "
               "Visualization concept adapted from Smart-Campus-Digital-Twin.")
