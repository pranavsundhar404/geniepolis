"""The Genie character — a glowing orb + speech bubble. No heavy animation."""
import html
import streamlit as st


def genie_say(text: str, thinking: bool = False, name: str = "GENIE"):
    cls = "genie-orb think" if thinking else "genie-orb"
    body = ('<span class="dots"><span></span><span></span><span></span></span> ' + html.escape(text)
            if thinking else html.escape(text).replace("\n", "<br>"))
    st.markdown(
        f"""
        <div class="genie-wrap">
          <div class="{cls}"></div>
          <div class="genie-bubble">
            <div class="genie-name">{name}</div>
            <div>{body}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def genie_appears():
    st.markdown(
        """
        <div class="gp-card" style="text-align:center; padding:1.6rem 1rem;">
          <div style="font-size:2.4rem">☁️✨</div>
          <div class="genie-orb" style="margin:.6rem auto;width:150px;height:150px;flex-basis:150px;"></div>
          <h3 style="margin:.2rem 0;">A Genie curls out of the campus wifi.</h3>
          <p class="gp-muted">"Aha... a campus wish? You get <b>three</b>. Choose your chaos wisely."</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def wish_progress(current: int, total: int = 3):
    dots = ""
    for i in range(1, total + 1):
        c = "done" if i < current else ("on" if i == current else "")
        dots += f'<i class="{c}"></i>'
    st.markdown(
        f'<div class="wish-dots">WISH {min(current,total)} / {total} &nbsp; {dots}</div>',
        unsafe_allow_html=True,
    )


def magic_transition(title: str):
    st.markdown(
        f"""
        <div class="gp-card" style="text-align:center; padding:2rem 1rem; overflow:hidden;">
          <div style="font-size:3rem; letter-spacing:.4rem;
               animation:bob 1.6s ease-in-out infinite;">☁️ 💨 ✨ 💨 ☁️</div>
          <h2 style="margin:.6rem 0 0;">{html.escape(title)}</h2>
          <p class="gp-muted">The Genie snaps their fingers. Reality re-renders...</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
