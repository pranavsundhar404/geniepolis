"""Campus Pulse — turning repeated wishes into campus intelligence."""
import html
import plotly.graph_objects as go
import streamlit as st

SIGNAL_THRESHOLD = 50


def campus_pulse(data, session_wishes=None):
    wh = data["wish_history"]
    by_text = wh["wish_text"].value_counts()
    by_domain = wh["domain"].value_counts()

    st.markdown(
        '<div class="gp-card"><h2>🫀 Campus Pulse</h2>'
        '<p class="gp-muted">Traditional feedback forms collect isolated complaints. '
        'GENIEPOLIS turns <b>repeated wishes</b> into a campus-level signal.</p>'
        '<span class="gp-synthetic">Synthetic demonstration data</span></div>',
        unsafe_allow_html=True)
    st.write("")

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown('<div class="gp-card"><h3>Top student wishes</h3></div>', unsafe_allow_html=True)
        top = by_text.head(6)
        fig = go.Figure(go.Bar(
            x=top.values[::-1], y=[t[:38] for t in top.index[::-1]], orientation="h",
            marker=dict(color=top.values[::-1], colorscale=[[0, "#2aa7c7"], [1, "#b58bff"]]),
            text=top.values[::-1], textposition="outside"))
        fig.update_layout(height=300, margin=dict(l=6, r=20, t=6, b=6),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#eaf1ff"), xaxis=dict(gridcolor="rgba(255,255,255,0.07)"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.markdown('<div class="gp-card"><h3>By domain</h3></div>', unsafe_allow_html=True)
        rows = "".join(
            f'<div class="impact-row"><span>{html.escape(d.title())}</span><b>{c} wishes</b></div>'
            for d, c in by_domain.head(8).items())
        st.markdown(f'<div class="gp-card">{rows}</div>', unsafe_allow_html=True)

    # ---- campus signals ----
    st.write("")
    st.markdown('<div class="gp-card"><h3>🚨 Campus signals</h3>'
                f'<p class="gp-muted">A wish becomes a <b>signal</b> when ≥ {SIGNAL_THRESHOLD} students ask for it.</p></div>',
                unsafe_allow_html=True)
    any_signal = False
    for text, count in by_text.items():
        if count >= SIGNAL_THRESHOLD:
            any_signal = True
            st.markdown(
                f'<div class="gp-card signal"><div class="kpi">{count} students</div>'
                f'<div style="font-size:1.05rem;font-weight:700">requested: “{html.escape(text)}”</div>'
                f'<p class="gp-muted" style="margin:.4rem 0 0">Repeated requests may indicate a campus-level issue. '
                f'Recommended action: campus administration should investigate this.</p>'
                f'<span class="gp-synthetic">Synthetic demonstration data</span></div>',
                unsafe_allow_html=True)
            st.write("")
    if not any_signal:
        st.info("No wish has crossed the signal threshold in this synthetic dataset.")

    # ---- issues + affected buildings ----
    c3, c4 = st.columns(2)
    with c3:
        top_iss = data["issues"]["type"].value_counts().head(6)
        rows = "".join(
            f'<div class="impact-row"><span>{"🔴" if i==0 else "🟠" if i<2 else "🟡"} {html.escape(t)}</span>'
            f'<b>{c}</b></div>' for i, (t, c) in enumerate(top_iss.items()))
        st.markdown(f'<div class="gp-card"><h3>Top reported issues</h3>{rows}'
                    f'<span class="gp-synthetic">Synthetic demonstration data</span></div>',
                    unsafe_allow_html=True)
    with c4:
        aff = data["issues"]["building_id"].value_counts().head(6)
        names = data["buildings"].set_index("id")["name"].to_dict()
        rows = "".join(
            f'<div class="impact-row"><span>{html.escape(names.get(b,b))}</span><b>{c} issues</b></div>'
            for b, c in aff.items())
        st.markdown(f'<div class="gp-card"><h3>Most affected buildings</h3>{rows}</div>',
                    unsafe_allow_html=True)

    if session_wishes:
        made = "".join(f'<div class="impact-row"><span>🧞 {html.escape(w)}</span></div>'
                       for w in session_wishes)
        st.write("")
        st.markdown(f'<div class="gp-card"><h3>Your three wishes this session</h3>{made}'
                    f'<p class="gp-muted" style="margin-top:.5rem">'
                    f'Every wish a student makes is logged here — that is how isolated wishes become a pulse.</p></div>',
                    unsafe_allow_html=True)
