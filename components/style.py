"""Custom CSS + small UI helpers to make Streamlit not look like Streamlit."""
import streamlit as st

CSS = """
<style>
:root{
  --bg:#070b16; --bg2:#0d1426; --card:#111a30; --line:#20304f;
  --cyan:#4fe3ff; --cyan-dim:#2aa7c7; --gold:#f6c14b; --violet:#b58bff;
  --text:#eaf1ff; --muted:#93a3c4; --good:#37d99a; --warn:#ffcf5c; --bad:#ff6f8b;
}
.stApp{background:radial-gradient(1200px 700px at 20% -10%, #16224a 0%, var(--bg) 55%) fixed;
  color:var(--text); font-family:'Inter','Segoe UI',system-ui,sans-serif;}
#MainMenu, header[data-testid="stHeader"], footer, .stDeployButton{display:none!important;}
.block-container{padding-top:1.1rem; padding-bottom:3rem; max-width:1250px;}
h1,h2,h3,h4{color:var(--text); letter-spacing:.2px;}
a{color:var(--cyan);}

/* ---- brand header ---- */
.gp-header{display:flex; align-items:center; justify-content:space-between; gap:1rem;
  padding:.5rem .2rem 1rem;}
.gp-title{font-size:1.9rem; font-weight:800; margin:0;
  background:linear-gradient(90deg,#fff, var(--cyan) 60%, var(--gold));
  -webkit-background-clip:text; background-clip:text; color:transparent;}
.gp-tag{color:var(--muted); font-size:.9rem; margin-top:-2px;}
.gp-badge{font-size:.72rem; padding:.35rem .7rem; border-radius:999px; font-weight:700;
  border:1px solid var(--line); white-space:nowrap;}
.gp-badge.ok{color:#0a1a12; background:linear-gradient(90deg,var(--good),#9df5cf);}
.gp-badge.demo{color:#1a1206; background:linear-gradient(90deg,var(--gold),#ffe6a8);}

/* ---- cards ---- */
.gp-card{background:linear-gradient(180deg,var(--card),#0d1730);
  border:1px solid var(--line); border-radius:18px; padding:1.1rem 1.2rem;
  box-shadow:0 10px 40px -20px #000, inset 0 1px 0 #ffffff10;}
.gp-card h3{margin:.1rem 0 .6rem;}
.gp-muted{color:var(--muted); font-size:.86rem;}
.gp-synthetic{display:inline-block; margin-top:.4rem; font-size:.7rem; letter-spacing:.14em;
  text-transform:uppercase; color:#ffd98a; border:1px dashed #7a6323; padding:.2rem .5rem;
  border-radius:8px; background:#1c150633;}

/* ---- genie ---- */
.genie-wrap{display:flex; gap:.9rem; align-items:flex-start;}
.genie-orb{width:104px;height:104px;flex:0 0 104px;border-radius:50%;
  background:radial-gradient(circle at 35% 30%, #bff6ff, var(--cyan) 40%, #1c72a8 75%, #0a3350);
  box-shadow:0 0 0 5px #4fe3ff22, 0 0 60px #4fe3ff66; animation:bob 3.4s ease-in-out infinite;}
.genie-orb.think{animation:bob 1.1s ease-in-out infinite, hue 3s linear infinite;}
@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes hue{0%{filter:hue-rotate(0)}100%{filter:hue-rotate(360deg)}}
.genie-bubble{position:relative; background:#0e1a33; border:1px solid var(--line);
  border-radius:14px; padding:.8rem 1rem; color:var(--text); flex:1; line-height:1.5;}
.genie-bubble:before{content:""; position:absolute; left:-8px; top:18px; width:14px;height:14px;
  background:#0e1a33; border-left:1px solid var(--line); border-bottom:1px solid var(--line);
  transform:rotate(45deg);}
.genie-name{color:var(--gold); font-weight:700; font-size:.8rem; letter-spacing:.05em;}
.dots span{display:inline-block;width:7px;height:7px;margin:0 2px;border-radius:50%;
  background:var(--cyan);animation:blink 1.2s infinite both;}
.dots span:nth-child(2){animation-delay:.2s}.dots span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}

/* ---- wish progress ---- */
.wish-dots{display:flex; gap:.5rem; align-items:center; font-weight:700; color:var(--muted);}
.wish-dots i{width:12px;height:12px;border-radius:50%;background:#2a3a5e;display:inline-block;}
.wish-dots i.on{background:var(--cyan); box-shadow:0 0 12px var(--cyan);}
.wish-dots i.done{background:var(--gold);}

/* ---- pills / impacts ---- */
.pill{display:inline-block; padding:.28rem .6rem; border-radius:999px; font-size:.78rem;
  font-weight:700; margin:.15rem .25rem .15rem 0;}
.pill.direct{background:#3a0f1b; color:#ff9bb0; border:1px solid #7c2740;}
.pill.indirect{background:#3a300f; color:#ffdf9b; border:1px solid #7c6327;}
.pill.good{background:#0f3a2a; color:#8ff5cf; border:1px solid #276c53;}
.impact-row{display:flex; justify-content:space-between; gap:1rem; padding:.5rem .2rem;
  border-bottom:1px dashed #ffffff12;}
.delta.up{color:var(--bad);} .delta.down{color:var(--good);} .delta.flat{color:var(--muted);}

/* ---- before/after ---- */
.ba{display:grid; grid-template-columns:1.2fr .7fr .7fr .8fr; gap:.2rem; align-items:center;
  padding:.55rem .3rem; border-bottom:1px solid #ffffff10;}
.ba .b{color:var(--muted);} .ba .a{font-weight:800;}
.bar{height:8px;border-radius:6px;background:#22314f;overflow:hidden;}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--violet));}

/* ---- buttons ---- */
.stButton>button{background:linear-gradient(180deg,#162138,#0f1830);
  border:1px solid var(--line); color:var(--text); border-radius:12px; font-weight:650;
  padding:.5rem .9rem; transition:.15s;}
.stButton>button:hover{border-color:var(--cyan); box-shadow:0 0 18px -4px var(--cyan);}
div[data-testid="stButton"] button[kind="primary"], .stButton>button[kind="primary"]{
  background:linear-gradient(90deg,var(--cyan),var(--violet)); color:#04121e; border:0;}
.make-it-happen button{font-size:1.05rem!important; padding:.8rem 1.2rem!important;}

/* misc */
hr{border-color:#ffffff14;}
.small{font-size:.8rem;color:var(--muted);}
.kpi{font-size:1.6rem;font-weight:800;color:var(--cyan);}
.signal{border-left:4px solid var(--bad); background:#2a0f18; padding:.8rem 1rem; border-radius:10px;}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(mode_badge_html: str):
    st.markdown(
        f"""
        <div class="gp-header">
          <div>
            <p class="gp-title">✨ GENIEPOLIS</p>
            <div class="gp-tag">Three Wishes. One Campus. Infinite Ripples.</div>
          </div>
          <div style="text-align:right">
            {mode_badge_html}
            <div class="gp-tag" style="margin-top:.4rem">HackCulture · Track B · Creative Campus Intelligence</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def synthetic_tag():
    st.markdown('<span class="gp-synthetic">Synthetic demonstration data</span>',
                unsafe_allow_html=True)
