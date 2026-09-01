"""Fast 2.5D campus map (Plotly) with clickable buildings + info panel.

Concept adapted from Smart-Campus-Digital-Twin (Three.js + IoT). We trade 3D for
a stable Plotly footprint map with native click selection and live-ish
'current conditions' from the synthetic snapshot.
"""
import html
import plotly.graph_objects as go
import streamlit as st

from data.campus_data import (BUILDINGS, ROADS, ZONES, TYPE_STYLE, CAMPUS_THEMES,
                              CAMPUS_NAME, building_center, BUILDING_LINKS)

_LEVEL_COLOR = {"LOW": "#37d99a", "MEDIUM": "#ffcf5c", "HIGH": "#ff9f5c", "CRITICAL": "#ff6f8b"}


def _rgba(hex_color: str, alpha: float) -> str:
    """#rrggbb -> rgba(r,g,b,a).  Plotly shape fillcolor rejects 8-digit hex."""
    h = hex_color.lstrip("#")
    if len(h) >= 6:
        r, g, bl = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{bl},{alpha})"
    return hex_color


def render_campus(data, *, theme="default", highlight_direct=None, highlight_indirect=None,
                  key="campus", height=520, title_suffix="", moves=None, recolor=None):
    highlight_direct = set(highlight_direct or [])
    highlight_indirect = set(highlight_indirect or [])
    moves = moves or {}            # {bid: [x, y]} -> building physically relocates
    recolor = recolor or {}        # {bid: delta_pct} -> fill washes red (up) / green (down)
    th = CAMPUS_THEMES.get(theme, CAMPUS_THEMES["default"])
    snap = data.get("snapshot", {})

    def _pos(b):
        """current footprint origin, honouring any move"""
        if b["id"] in moves:
            mx, my = moves[b["id"]]
            return float(mx), float(my)
        return float(b["x"]), float(b["y"])

    fig = go.Figure()

    # zones (decorative)
    for z in ZONES:
        fig.add_shape(type="rect", x0=z["x"], y0=z["y"], x1=z["x"] + z["w"], y1=z["y"] + z["h"],
                      line=dict(width=0), fillcolor="rgba(31,111,63,0.13)", layer="below")

    # roads (dim the central spine when a car-free / pedestrian wish is active)
    for r in ROADS:
        xs = [p[0] for p in r["pts"]]
        ys = [p[1] for p in r["pts"]]
        dim = theme == "pedestrian" or (r["id"] == "spine" and theme == "pedestrian")
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
            line=dict(color="#39507e", width=3 if dim else 9,
                      dash="dot" if dim else "solid"),
            opacity=0.35 if dim else 0.8))

    # building footprints
    for b in BUILDINGS:
        stl = TYPE_STYLE.get(b["type"], {"color": "#4f9dff", "icon": "▪"})
        bx, by = _pos(b)

        # ghost of the old location + arrow when a building has moved
        if b["id"] in moves:
            fig.add_shape(type="rect", x0=b["x"], y0=b["y"],
                          x1=b["x"] + b["w"], y1=b["y"] + b["h"],
                          line=dict(color="rgba(255,255,255,0.25)", width=1, dash="dot"),
                          fillcolor="rgba(255,255,255,0.03)", layer="below")
            oc = building_center(b)
            fig.add_annotation(x=bx + b["w"] / 2, y=by + b["h"] / 2, ax=oc[0], ay=oc[1],
                               xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=3, arrowsize=1.4,
                               arrowwidth=2, arrowcolor="#4fe3ff", text="")

        border = "rgba(255,255,255,0.13)"
        width = 1
        fill = _rgba(stl["color"], 0.8)
        d = recolor.get(b["id"])
        if d is not None and abs(d) >= 0.1:
            fill = _rgba("#ff5c78" if d > 0 else "#37d99a", 0.78)
        if b["id"] in highlight_direct:
            border, width = "#ff6f8b", 3
        elif b["id"] in highlight_indirect:
            border, width = "#f6c14b", 2
        fig.add_shape(type="rect", x0=bx, y0=by, x1=bx + b["w"], y1=by + b["h"],
                      line=dict(color=border, width=width), fillcolor=fill, layer="below")

        # delta label on changed buildings
        if d is not None and abs(d) >= 0.1:
            arrow = "▲" if d > 0 else "▼"
            fig.add_annotation(x=bx + b["w"] / 2, y=by + b["h"] + 14, showarrow=False,
                               text=f"<b>{arrow} {abs(d):.0f}%</b>",
                               font=dict(color="#ff9bb0" if d > 0 else "#8ff5cf", size=11))

    # clickable centroids
    cx, cy, txt, cd, hov, msz, mcol, mline = [], [], [], [], [], [], [], []
    for b in BUILDINGS:
        bx, by = _pos(b)
        c = (bx + b["w"] / 2, by + b["h"] / 2)
        stl = TYPE_STYLE.get(b["type"], {"color": "#4f9dff", "icon": "▪"})
        s = snap.get(b["id"], {})
        cx.append(c[0]); cy.append(c[1]); cd.append(b["id"])
        txt.append(f"{stl['icon']}<br><span style='font-size:10px'>{html.escape(b['name'])}</span>")
        occ = s.get("occupancy_rate")
        crowd = s.get("crowd", "—")
        hov.append(
            f"<b>{html.escape(b['name'])}</b><br>"
            + (f"Occupancy {occ:.0%} · Crowd {crowd}<br>Students {s.get('students','–')} · "
               f"Faculty {s.get('faculty','–')} · Staff {s.get('staff','–')}" if s else "Click to inspect")
            + "<extra></extra>")
        big = b["id"] in highlight_direct or b["id"] in highlight_indirect
        msz.append(30 if big else 20)
        mcol.append("rgba(255,255,255,0.04)")
        mline.append("#ff6f8b" if b["id"] in highlight_direct else
                     ("#f6c14b" if b["id"] in highlight_indirect else "rgba(255,255,255,0.2)"))

    fig.add_trace(go.Scatter(
        x=cx, y=cy, mode="markers+text", text=txt, textposition="middle center",
        textfont=dict(color="#eaf1ff", size=13),
        customdata=cd, hovertemplate=hov,
        marker=dict(size=msz, color=mcol, line=dict(color=mline, width=2), symbol="square"),
        showlegend=False, name="buildings"))

    fig.update_layout(
        height=height, margin=dict(l=6, r=6, t=6, b=6),
        paper_bgcolor=th["bg"], plot_bgcolor=th["bg"],
        xaxis=dict(range=[0, 1000], visible=False, fixedrange=True),
        yaxis=dict(range=[0, 700], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1),
        dragmode=False, hoverlabel=dict(bgcolor="#0e1a33", font_size=12),
    )
    fig.add_annotation(x=14, y=686, text=f"<b>{CAMPUS_NAME}</b> · {th['label']} {title_suffix}",
                       showarrow=False, xanchor="left", font=dict(color="#93a3c4", size=12))

    event = st.plotly_chart(fig, key=key, on_select="rerun", use_container_width=True,
                            config={"displayModeBar": False, "scrollZoom": False})
    return _selected_id(event)


def _selected_id(event):
    try:
        pts = event["selection"]["points"] if isinstance(event, dict) else event.selection["points"]
    except Exception:
        return None
    for p in pts or []:
        cd = p.get("customdata")
        if isinstance(cd, list):
            cd = cd[0] if cd else None
        if cd:
            return cd
    return None


def building_buttons(key_prefix="bb"):
    """Reliable fallback selector: a grid of building buttons."""
    picked = None
    cols = st.columns(4)
    for i, b in enumerate(BUILDINGS):
        stl = TYPE_STYLE.get(b["type"], {"icon": "▪"})
        if cols[i % 4].button(f"{stl['icon']} {b['name']}", key=f"{key_prefix}_{b['id']}",
                              use_container_width=True):
            picked = b["id"]
    return picked


def building_panel(bid, data):
    from data.campus_data import BUILDING_BY_ID
    b = BUILDING_BY_ID.get(bid)
    s = data.get("snapshot", {}).get(bid, {})
    if not b:
        return
    name = b["name"]
    if not s:  # gate / parking without full snapshot
        st.markdown(f'<div class="gp-card"><h3>{html.escape(name)}</h3>'
                    f'<p class="gp-muted">{b["type"].title()} · capacity {b["capacity"]}</p>'
                    f'<span class="gp-synthetic">Synthetic demonstration data</span></div>',
                    unsafe_allow_html=True)
        return

    crowd = s.get("crowd", "LOW")
    traffic = s.get("traffic", "LOW")
    occ = s.get("occupancy_rate", 0)
    rows = [
        ("Rooms", s.get("rooms")), ("Available rooms", s.get("available_rooms")),
        ("Classes running", s.get("classes_running")), ("Faculty present", s.get("faculty_present")),
        ("Faculty in class", s.get("faculty_in_class")), ("Faculty in offices", s.get("faculty_in_office")),
        ("Staff", s.get("staff")),
    ]
    rows_html = "".join(
        f'<div class="impact-row"><span class="gp-muted">{k}</span><b>{v}</b></div>'
        for k, v in rows if v is not None)

    who = s
    who_html = (
        f'<div class="impact-row"><span class="gp-muted">Students</span><b>{who.get("students","–")}</b></div>'
        f'<div class="impact-row"><span class="gp-muted">Faculty</span><b>{who.get("faculty","–")}</b></div>'
        f'<div class="impact-row"><span class="gp-muted">Workers</span><b>{who.get("workers","–")}</b></div>'
        f'<div class="impact-row"><span class="gp-muted">Visitors</span><b>{who.get("visitors","–")}</b></div>'
    )
    links = BUILDING_LINKS.get(bid, [])
    from data.campus_data import BUILDING_BY_ID as B
    link_html = " ".join(f'<span class="pill indirect">{html.escape(B[l]["name"])}</span>'
                         for l in links if l in B) or '<span class="gp-muted">—</span>'

    st.markdown(
        f"""
        <div class="gp-card">
          <div style="display:flex; justify-content:space-between; align-items:baseline;">
            <h3>{html.escape(name)}</h3>
            <span class="gp-muted">{b['type'].title()}</span>
          </div>
          <div style="display:flex; gap:.5rem; margin:.2rem 0 .7rem; flex-wrap:wrap;">
            <span class="pill" style="background:{_LEVEL_COLOR[crowd]}22;color:{_LEVEL_COLOR[crowd]};border:1px solid {_LEVEL_COLOR[crowd]}55;">Crowd {crowd}</span>
            <span class="pill" style="background:{_LEVEL_COLOR[traffic]}22;color:{_LEVEL_COLOR[traffic]};border:1px solid {_LEVEL_COLOR[traffic]}55;">Traffic {traffic}</span>
            <span class="pill" style="background:#4fe3ff22;color:#4fe3ff;border:1px solid #4fe3ff55;">Occupancy {occ:.0%}</span>
          </div>
          <div class="bar" style="margin-bottom:.6rem;"><i style="width:{min(occ*100,100):.0f}%"></i></div>
          <h4 style="margin:.4rem 0 .2rem;">Current conditions</h4>
          {rows_html}
          <h4 style="margin:.8rem 0 .2rem;">Who's here?</h4>
          {who_html}
          <h4 style="margin:.8rem 0 .2rem;">Connected to</h4>
          {link_html}
          <div style="margin-top:.7rem;"><span class="gp-synthetic">Synthetic demonstration data</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def conditions_strip(data, hour=16):
    """Campus-wide LOW/MED/HIGH indicators for a given hour (slider-driven)."""
    snap = data.get("snapshot", {})
    pk = data["parking"]; tr = data["traffic"]
    park = float(pk[pk.hour == hour].occupancy_rate.mean())
    traf = float(tr[tr.hour == hour].congestion.mean())
    canteen = snap.get("cafeteria", {}).get("occupancy_rate", 0.4)
    washr = snap.get("washroom_block", {}).get("occupancy_rate", 0.4)
    ground = snap.get("ground", {}).get("occupancy_rate", 0.4)
    items = [("Parking", park), ("Traffic", traf), ("Canteen", canteen),
             ("Washroom", washr), ("Sports ground", ground)]
    bars = ""
    for name, v in items:
        v = max(0.0, min(v, 1.0))
        filled = int(round(v * 10))
        bar = "█" * filled + "░" * (10 - filled)
        col = "#ff6f8b" if v >= .9 else "#ff9f5c" if v >= .72 else "#ffcf5c" if v >= .45 else "#37d99a"
        bars += (f'<div class="impact-row"><span class="gp-muted" style="width:120px">{name}</span>'
                 f'<span style="font-family:monospace;color:{col}">{bar}</span>'
                 f'<b style="color:{col}">{v:.0%}</b></div>')
    st.markdown(f'<div class="gp-card"><h3>Campus conditions · {hour:02d}:00</h3>{bars}'
                f'<span class="gp-synthetic">Synthetic demonstration data</span></div>',
                unsafe_allow_html=True)
