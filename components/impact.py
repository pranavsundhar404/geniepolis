"""Impact panels: direct vs indirect, before/after, risk/benefit, alternatives."""
import html
import streamlit as st


def _delta_span(pct):
    if pct is None:
        return '<span class="delta flat">—</span>'
    if abs(pct) < 0.1:
        return '<span class="delta flat">no change</span>'
    cls = "up" if pct > 0 else "down"
    arrow = "▲" if pct > 0 else "▼"
    return f'<span class="delta {cls}">{arrow} {abs(pct):.0f}%</span>'


def direct_indirect(res):
    d_rows = "".join(
        f'<div class="impact-row"><span>🔴 <b>{html.escape(x["label"])}</b>'
        f'<span class="gp-muted"> — {html.escape(x.get("note",""))}</span></span>'
        f'<span class="pill direct">{html.escape(str(x.get("status","changed")))}</span></div>'
        for x in res.get("direct_impacts", []))
    i_rows = "".join(
        f'<div class="impact-row"><span>🟡 <b>{html.escape(x["label"])}</b>'
        f'<span class="gp-muted"> — {html.escape(x.get("note",""))}</span></span>'
        f'{_delta_span(x.get("delta_pct"))}</div>'
        for x in res.get("indirect_impacts", []))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="gp-card"><h3>Direct impacts</h3>'
                    f'<p class="gp-muted">The wish changes these on purpose.</p>{d_rows}</div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="gp-card"><h3>Indirect impacts</h3>'
                    f'<p class="gp-muted">These moved because something else moved.</p>{i_rows}</div>',
                    unsafe_allow_html=True)


def before_after(res):
    table = res.get("metrics_table", [])
    if not table:
        st.markdown('<div class="gp-card"><h3>Before / After</h3>'
                    '<p class="gp-muted">This is a creative wish — operational metrics are left unchanged.</p></div>',
                    unsafe_allow_html=True)
        return
    rows = '<div class="ba"><span class="gp-muted">Metric</span><span class="gp-muted">Before</span>' \
           '<span class="gp-muted">After</span><span class="gp-muted">Change</span></div>'
    for m in table:
        unit = m.get("unit", "")
        before = f'{m["before"]}{unit}'
        after = f'{m["after"]}{unit}'
        rows += (f'<div class="ba"><span>{html.escape(m["metric"])}</span>'
                 f'<span class="b">{before}</span><span class="a">{after}</span>'
                 f'{_delta_span(m.get("delta_pct"))}</div>')
    st.markdown(f'<div class="gp-card"><h3>Before / After</h3>{rows}'
                f'<span class="gp-synthetic">Synthetic demonstration data</span></div>',
                unsafe_allow_html=True)


def risk_benefit(res, genie_explanation: str):
    ben = "".join(f'<div class="impact-row"><span>✓ {html.escape(b)}</span></div>'
                  for b in res.get("benefits", []))
    rk = "".join(f'<div class="impact-row"><span>⚠ {html.escape(r)}</span></div>'
                 for r in res.get("risks", []))
    tr = "".join(f'<li>{html.escape(t)}</li>' for t in res.get("tradeoffs", []))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="gp-card"><h3 style="color:#8ff5cf">Benefits</h3>{ben}</div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="gp-card"><h3 style="color:#ff9bb0">Risks</h3>{rk}</div>',
                    unsafe_allow_html=True)
    st.markdown(
        f'<div class="gp-card" style="margin-top:.8rem"><h3>Trade-offs</h3><ul>{tr}</ul>'
        f'<h4 style="margin:.6rem 0 .2rem">Why? <span class="gp-muted">(Genie explains the engine\'s numbers)</span></h4>'
        f'<p>{html.escape(genie_explanation).replace(chr(10),"<br>")}</p></div>',
        unsafe_allow_html=True)


def alternatives(res, wish_no: int):
    st.markdown('<div class="gp-card"><h3>What if you tried this instead?</h3></div>',
                unsafe_allow_html=True)
    picked = None
    for i, alt in enumerate(res.get("recommendations", [])):
        c1, c2 = st.columns([4, 1])
        c1.markdown(f'**{html.escape(alt["label"])}**  \n'
                    f'<span class="gp-muted">{html.escape(alt["why"])}</span>', unsafe_allow_html=True)
        if c2.button("Explore", key=f"alt_{wish_no}_{i}"):
            picked = alt["label"]
    return picked


def final_impact_screen(res, genie_explanation, wish_no):
    sc = res.get("scenario", {})
    st.markdown(
        f'<div class="gp-card"><span class="gp-muted">YOUR WISH · {sc.get("type","")}</span>'
        f'<h2 style="margin:.2rem 0">“{html.escape(res.get("raw_text") or sc.get("title",""))}”</h2>'
        f'<p class="gp-muted">{html.escape(sc.get("description",""))}</p></div>',
        unsafe_allow_html=True)
    st.write("")
    direct_indirect(res)
    st.write("")
    before_after(res)
    st.write("")
    risk_benefit(res, genie_explanation)
