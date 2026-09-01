"""Animated ripple / butterfly-effect chain (self-contained HTML + CSS)."""
import html
import streamlit as st
import streamlit.components.v1 as components


def ripple_animation(ripple, height=None):
    """ripple = [{step,node,label,building_id,kind,delta_pct}, ...]"""
    n = len(ripple)
    height = height or (120 + n * 74)
    nodes_html = ""
    for i, r in enumerate(ripple):
        kind = r.get("kind", "indirect")
        delta = r.get("delta_pct")
        badge = ""
        if delta is not None and abs(delta) >= 0.1:
            arrow = "▲" if delta > 0 else "▼"
            col = "#ff6f8b" if delta > 0 else "#37d99a"
            badge = f'<span class="rp-delta" style="color:{col}">{arrow} {abs(delta):.0f}%</span>'
        elif delta == 0:
            badge = '<span class="rp-delta" style="color:#93a3c4">no change</span>'
        dot = "#ff6f8b" if kind == "direct" else "#f6c14b"
        label_kind = "DIRECT" if kind == "direct" else "RIPPLE"
        nodes_html += f"""
        <div class="rp-node" style="animation-delay:{i*0.55:.2f}s">
          <div class="rp-dot" style="background:{dot}; box-shadow:0 0 16px {dot}">
            <span class="rp-ring" style="border-color:{dot}; animation-delay:{i*0.55:.2f}s"></span>
          </div>
          <div class="rp-body">
            <div class="rp-kind" style="color:{dot}">{label_kind}</div>
            <div class="rp-label">{html.escape(r['label'])}</div>
          </div>
          {badge}
        </div>
        {"<div class='rp-line' style='animation-delay:%.2fs'></div>" % (i*0.55+0.25) if i < n-1 else ""}
        """

    doc = f"""
    <style>
      .rp-wrap{{font-family:'Inter',system-ui,sans-serif;color:#eaf1ff;padding:6px 2px;}}
      .rp-node{{display:flex;align-items:center;gap:14px;opacity:0;transform:translateY(10px);
        animation:rpIn .5s ease forwards;}}
      .rp-dot{{position:relative;width:18px;height:18px;border-radius:50%;flex:0 0 18px;}}
      .rp-ring{{position:absolute;inset:-6px;border:2px solid;border-radius:50%;opacity:.8;
        animation:rpPulse 1.8s ease-out infinite;}}
      .rp-body{{flex:1;}}
      .rp-kind{{font-size:.62rem;letter-spacing:.14em;font-weight:800;}}
      .rp-label{{font-size:.98rem;font-weight:600;}}
      .rp-delta{{font-weight:800;font-size:.9rem;white-space:nowrap;}}
      .rp-line{{width:2px;height:26px;margin:4px 0 4px 8px;background:linear-gradient(#f6c14b,#4fe3ff);
        opacity:0;animation:rpIn .4s ease forwards;}}
      @keyframes rpIn{{to{{opacity:1;transform:translateY(0);}}}}
      @keyframes rpPulse{{0%{{transform:scale(.7);opacity:.9;}}100%{{transform:scale(2.4);opacity:0;}}}}
    </style>
    <div class="rp-wrap">{nodes_html}</div>
    """
    components.html(doc, height=height, scrolling=False)


def ripple_origin_caption(origin_label: str):
    st.markdown(f'<p class="small">Ripple origin → <b style="color:#4fe3ff">{html.escape(origin_label)}</b>. '
                f'Only affected areas are animated.</p>', unsafe_allow_html=True)
