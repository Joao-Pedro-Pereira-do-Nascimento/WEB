"""CSS do app — tema "mata assombrada à noite" (RPG sombrio) — e todas as animações.

Paleta: verdes quase pretos, brasa/âmbar, dourado envelhecido e pergaminho.
Fontes (Google Fonts): Cinzel Decorative / Cinzel (títulos e botões),
MedievalSharp (detalhes), Alegreya Sans (texto corrido) e Bungee (só dentro das cartas).
"""

from __future__ import annotations

import random
from urllib.parse import quote

from .duels import DUEL_CSS
from .icons import avatar_picker_css, icon_mask_css


def _corner(rot: int) -> str:
    """Ornamento de canto (arabesco dourado) como data URI, girado de ``rot`` graus."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><g transform="rotate({rot} 20 20)" fill="none" '
           f'stroke="#d9a441" stroke-width="1.6" stroke-linecap="round">'
           f'<path d="M3 37V12Q3 3 12 3h25"/><path d="M8 37V16q0-8 8-8h21" opacity=".55"/>'
           f'<path d="M3 3l7 7M12 10q4-6 9-2M10 12q-6 4-2 9"/><circle cx="12" cy="12" r="2.2" fill="#d9a441"/></g></svg>')
    return 'url("data:image/svg+xml;utf8,' + quote(svg) + '")'


CORNERS = (f"{_corner(0)} top left/34px no-repeat, {_corner(90)} top right/34px no-repeat, "
           f"{_corner(270)} bottom left/34px no-repeat, {_corner(180)} bottom right/34px no-repeat")


def _forest_svg() -> str:
    """Silhueta de mata (árvores e palmeiras) para o rodapé do fundo."""
    rng = random.Random(7)
    shapes = []
    x = -20
    while x < 1460:
        h = rng.randint(120, 260)
        w = rng.randint(50, 110)
        kind = rng.random()
        if kind < .45:  # copa arredondada
            shapes.append(f'<path d="M{x + w / 2 - 5} 400 v{-h * .45} h10 v{h * .45} Z"/>'
                          f'<ellipse cx="{x + w / 2}" cy="{400 - h * .6}" rx="{w * .6}" ry="{h * .32}"/>'
                          f'<ellipse cx="{x + w * .25}" cy="{400 - h * .5}" rx="{w * .4}" ry="{h * .22}"/>')
        elif kind < .75:  # palmeira
            top = 400 - h
            fronds = "".join(f'<path d="M{x + w / 2} {top} q{d * 30} {-18} {d * 60} {10}" stroke-width="9" fill="none"/>'
                             for d in (-1, -.6, .6, 1))
            shapes.append(f'<path d="M{x + w / 2 - 4} 400 Q{x + w / 2 + 10} {top + h / 2} {x + w / 2} {top} l6 0 '
                          f'Q{x + w / 2 + 16} {top + h / 2} {x + w / 2 + 5} 400 Z"/>{fronds}')
        else:  # pinheiro / araucária estilizada
            shapes.append(f'<path d="M{x + w / 2} {400 - h} l{w / 2} {h * .55} h{-w * .3} l{w * .35} {h * .45} h{-w * 1.1} '
                          f'l{w * .35} {-h * .45} h{-w * .3} Z"/>')
        x += rng.randint(40, 90)
    body = "".join(shapes)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 400" preserveAspectRatio="xMidYMax slice">'
           f'<g fill="#030705" stroke="#030705">{body}</g></svg>')
    return 'url("data:image/svg+xml;utf8,' + quote(svg) + '")'


def ambient_html(n: int = 18) -> str:
    """Camada fixa de fundo: névoa, luz de tocha e vaga-lumes (decorativa)."""
    rng = random.Random(42)
    flies = "".join(
        f'<i class="firefly" style="left:{rng.uniform(2, 98):.0f}vw;top:{rng.uniform(20, 95):.0f}vh;'
        f'--dx:{rng.uniform(-60, 60):.0f}px;--dy:{rng.uniform(-80, 20):.0f}px;'
        f'animation-duration:{rng.uniform(6, 12):.1f}s,{rng.uniform(1.6, 3.4):.1f}s;'
        f'animation-delay:{rng.uniform(0, 6):.1f}s,{rng.uniform(0, 2):.1f}s"></i>' for _ in range(n))
    return (f'<div class="ambient" aria-hidden="true"><div class="torch t1"></div><div class="torch t2"></div>'
            f'<div class="forest"></div><div class="fog f1"></div><div class="fog f2"></div>{flies}</div>')


CSS = r"""
<style id="uno-css">
@import url('https://fonts.googleapis.com/css2?family=Alegreya+Sans:ital,wght@0,400;0,500;0,700;0,800;1,400&family=Bungee&family=Cinzel+Decorative:wght@700;900&family=Cinzel:wght@500;700;900&family=MedievalSharp&display=swap');
:root {
  --bg0: #030705; --bg1: #08130d; --moss: #10241a; --ink: #efe3c4; --muted: #b3a88c; --gold: #e2b04e; --gold2: #f6d98a;
  --old-gold: #9c7630; --ember: #ff7a1a; --blood: #9b1d1d; --stone: #1a1712;
  --fogo: #e8392b; --mata: #1fa65a; --rios: #1f7be0; --cerrado: #f2b311;
  --title: 'Cinzel', 'Times New Roman', serif; --deco: 'Cinzel Decorative', 'Cinzel', serif;
  --body: 'Alegreya Sans', 'Segoe UI', sans-serif; --hand: 'MedievalSharp', 'Cinzel', serif;
}
html, body { background: var(--bg0); }
[data-testid="stAppViewContainer"] {
  isolation: isolate;
  background:
    radial-gradient(ellipse 60% 40% at 50% -5%, #2a3b1a55 0%, transparent 70%),
    radial-gradient(ellipse 80% 60% at 50% 110%, #0f2a1a 0%, transparent 70%),
    linear-gradient(180deg, #050b08 0%, #07120c 45%, #030705 100%);
  background-attachment: fixed; color: var(--ink); font-family: var(--body);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { max-width: 1200px; padding-top: 1.6rem; padding-bottom: 4rem; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0b1610, #040806); border-right: 1px solid #3a2e14; }
h1, h2, h3, h4 { color: var(--gold2) !important; font-family: var(--title) !important; letter-spacing: .04em; text-shadow: 0 2px 0 #000, 0 0 18px #ff7a1a22; }
h1 [data-testid="stHeadingLink"], h2 [data-testid="stHeadingLink"], h3 [data-testid="stHeadingLink"], h4 [data-testid="stHeadingLink"] { display: none; }
p, li, label, .stMarkdown, td, th { font-family: var(--body); }
.stMarkdown p, .stMarkdown li { color: var(--ink); font-size: 1.02rem; }
a { color: var(--gold2) !important; }
.sr-only { position:absolute !important; width:1px !important; height:1px !important; overflow:hidden !important; clip:rect(0 0 0 0) !important; white-space:nowrap !important; margin:-1px !important; padding:0 !important; border:0 !important; }
.ico { display:inline-block; vertical-align:-.18em; }

/* ---------- ambiente: tocha, névoa, mata e vaga-lumes ---------- */
.ambient { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; }
.ambient .forest { position:absolute; left:0; right:0; bottom:0; height: 42vh; background: __FOREST__ bottom center/cover no-repeat; opacity: .95; }
.ambient .torch { position:absolute; width: 60vmax; height: 60vmax; border-radius: 50%; filter: blur(10px);
  background: radial-gradient(circle, #ff8a2a2e 0%, #ff5a1a14 30%, transparent 62%); animation: torch 3.2s ease-in-out infinite alternate; }
.ambient .torch.t1 { left: -26vmax; top: -24vmax; }
.ambient .torch.t2 { right: -28vmax; top: 18vh; animation-delay: -1.4s; opacity: .7; }
@keyframes torch { 0% { transform: scale(1); opacity: .75; } 40% { transform: scale(1.04); opacity: 1; } 70% { transform: scale(.98); opacity: .8; } 100% { transform: scale(1.06); opacity: .95; } }
.ambient .fog { position:absolute; left:-50%; width: 200%; height: 40vh; bottom: -6vh; filter: blur(18px);
  background: radial-gradient(ellipse 30% 50% at 20% 60%, #9fb8a51a, transparent 70%), radial-gradient(ellipse 30% 45% at 60% 50%, #b9c9bd17, transparent 70%),
              radial-gradient(ellipse 25% 40% at 85% 65%, #9fb8a515, transparent 70%);
  animation: fog-drift 38s linear infinite alternate; }
.ambient .fog.f2 { bottom: 14vh; height: 30vh; opacity: .7; animation-duration: 52s; animation-direction: alternate-reverse; }
@keyframes fog-drift { from { transform: translateX(0); } to { transform: translateX(22%); } }
.firefly { position:absolute; width: 5px; height: 5px; border-radius: 50%; background: #eaff8f; box-shadow: 0 0 8px 3px #c8ff5a99, 0 0 18px 6px #b8ff3a33;
  animation-name: firefly-move, firefly-blink; animation-iteration-count: infinite, infinite; animation-direction: alternate, alternate; animation-timing-function: ease-in-out, ease-in-out; }
@keyframes firefly-move { to { transform: translate(var(--dx), var(--dy)); } }
@keyframes firefly-blink { 0%, 40% { opacity: .05; } 70%, 100% { opacity: 1; } }

/* ---------- logo ---------- */
.logo { text-align: center; margin: 0 auto .6rem; max-width: 980px; }
.logo .eyebrow { color: var(--gold); font: 1rem var(--hand); letter-spacing: .14em; opacity: .9; }
.logo-svg { width: 100%; height: auto; display: block; margin: .2rem auto 0; overflow: visible; }
.logo .tagline { color: var(--muted); font: italic 500 1.05rem var(--body); letter-spacing: .06em; margin-top: -.2rem; }
.logo .tagline::before, .logo .tagline::after { content: ''; display: inline-block; width: 3.2rem; height: 1px; margin: 0 .8rem; vertical-align: middle;
  background: linear-gradient(90deg, transparent, var(--gold)); }
.logo .tagline::after { background: linear-gradient(90deg, var(--gold), transparent); }
.room-eyebrow { text-align:center; color: var(--gold); font: 1rem var(--hand); letter-spacing: .12em; margin-top: .4rem; }

/* ---------- molduras / painéis de RPG ---------- */
.panel, [data-testid="stForm"], .menu-frame, .st-key-create_box, .st-key-auth_box {
  position: relative; background: __CORNERS__, linear-gradient(170deg, #17140ef2, #0b0a07f5) !important;
  border: 1px solid #6e5524 !important; border-radius: 6px !important;
  box-shadow: inset 0 0 0 4px #0b0a07, inset 0 0 0 5px #d9a44133, inset 0 0 40px #000c, 0 12px 30px #000c, 0 0 0 1px #000;
  padding: 1.2rem 1.4rem !important; margin-bottom: .9rem;
}
.panel h3, [data-testid="stForm"] h3, .st-key-create_box h3, .st-key-auth_box h3 { margin-top: 0 !important; font-size: 1.25rem !important; text-align: center; }
[data-testid="stForm"] h3::after, .panel h3::after, .st-key-create_box h3::after, .st-key-auth_box h3::after { content:''; display:block; height: 10px; margin: .35rem auto 0; width: 70%;
  background: radial-gradient(circle at 50% 50%, var(--gold) 0 3px, transparent 4px), linear-gradient(90deg, transparent, #d9a44199 30%, #d9a44199 70%, transparent) center/100% 1px no-repeat; }
.panel .how { font-size: 1rem; line-height: 1.5; }
.panel .how b { color: var(--gold2); }
.home-intro { text-align:center; color: var(--muted); font: italic 1.08rem var(--body); margin: -.2rem auto 1rem; max-width: 760px; }

/* ---------- widgets nativos ---------- */
div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {
  font-family: var(--title); font-weight: 700; letter-spacing: .06em; border-radius: 6px; min-height: 2.9rem;
  background: linear-gradient(180deg, #2c2416, #16110a); color: var(--gold2); border: 1px solid #7a5d2a;
  box-shadow: inset 0 1px 0 #f6d98a33, inset 0 0 0 2px #0b0a07, 0 4px 0 #000, 0 6px 14px #000a; transition: transform .12s, box-shadow .2s, filter .2s;
}
div.stButton > button:hover, div.stFormSubmitButton > button:hover { color: #fff3cf; border-color: var(--gold); box-shadow: inset 0 1px 0 #f6d98a55, 0 4px 0 #000, 0 0 18px #ff9d2e55; transform: translateY(-1px); }
div.stButton > button:active, div.stFormSubmitButton > button:active { transform: translateY(2px); box-shadow: inset 0 1px 0 #f6d98a33, 0 1px 0 #000; }
div.stButton > button:focus-visible, div.stFormSubmitButton > button:focus-visible { outline: 2px solid var(--gold2); outline-offset: 2px; }
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primaryFormSubmit"] {
  background: radial-gradient(ellipse at 50% 0%, #ff9d4a 0%, transparent 60%), linear-gradient(180deg, #c2421c, #6d1408);
  color: #fff3cf; border: 1px solid var(--gold); text-shadow: 0 1px 2px #000; box-shadow: inset 0 1px 0 #ffd9a0aa, 0 4px 0 #2a0703, 0 0 22px #ff5a1a44; }
div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button:hover { filter: brightness(1.12); }
div.stButton > button:disabled { opacity: .45; filter: grayscale(.6); }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stTextArea"] textarea {
  background: #07100b !important; color: var(--ink) !important; font: 500 1.05rem var(--body) !important; border-radius: 4px !important; }
[data-testid="stTextInput"] [data-baseweb="input"], [data-baseweb="select"] > div, [data-testid="stNumberInput"] [data-baseweb="input"] {
  background: #07100b !important; border: 1px solid #5c4720 !important; border-radius: 4px !important; box-shadow: inset 0 2px 8px #000; }
[data-testid="stTextInput"] [data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within { border-color: var(--gold) !important; box-shadow: 0 0 0 1px var(--gold), 0 0 16px #ff9d2e44 !important; }
[data-baseweb="select"] * { color: var(--ink) !important; font-family: var(--body) !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #0d1510 !important; border: 1px solid #5c4720 !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="menu"] li:hover { background: #2c2416 !important; }
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label { color: var(--gold) !important; font: 700 .82rem var(--title) !important; letter-spacing: .1em; text-transform: uppercase; }
[data-testid="stSlider"] [role="slider"] { background: var(--gold) !important; border: 2px solid #2a1804 !important; box-shadow: 0 0 10px #ff9d2e88 !important; }
[data-testid="stSlider"] [data-testid="stSliderThumbValue"], [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { color: var(--gold2) !important; font-family: var(--title) !important; }
[data-testid="stTabs"] [role="tablist"] { display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .6rem;
  border-bottom: 1px solid #5c4720; padding: 0 .2rem; margin-bottom: .6rem; overflow: visible; }
[data-testid="stTabs"] [role="tab"] { display:flex; justify-content:center; align-items:center; cursor:pointer; min-height: 52px; padding: .55rem .6rem;
  border-radius: 8px 8px 0 0; border: 1px solid transparent; border-bottom: none; background: transparent; transition: background .2s, border-color .2s; }
[data-testid="stTabs"] [role="tab"]:hover { background: #ffffff08; border-color: #5c472066; }
[data-testid="stTabs"] [role="tab"] p { font: 700 1rem var(--title); letter-spacing: .1em; color: var(--muted); display:flex; align-items:center; gap:.15rem; white-space: nowrap; }
[data-testid="stTabs"] [role="tab"] p::before { width: 1.45em !important; height: 1.45em !important; margin-right: .55em !important; vertical-align: middle !important; }
[data-testid="stTabs"] .react-aria-SelectionIndicator { background: linear-gradient(90deg, transparent, var(--ember), transparent) !important; height: 3px !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { background: linear-gradient(180deg, #2c2416cc, #0b0a0700); border-color: #7a5d2a; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] p { color: var(--gold2); text-shadow: 0 0 12px #ff9d2e88; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: linear-gradient(90deg, transparent, var(--ember), transparent) !important; height: 3px !important; }
[data-testid="stTabs"] [data-baseweb="tab-border"] { background: transparent !important; }
[data-testid="stExpander"] details { background: #0b0a07cc; border: 1px solid #5c4720 !important; border-radius: 6px; }
[data-testid="stExpander"] summary p { font: 700 .9rem var(--title); color: var(--gold2); letter-spacing: .05em; }
[data-testid="stExpander"] summary:hover p { color: #fff3cf; }
[data-testid="stCode"] pre, .stCode pre, [data-testid="stCodeBlock"] pre { background: #050906 !important; border: 1px dashed #5c4720; }
[data-testid="stCode"] code { color: var(--gold2) !important; white-space: pre-wrap !important; word-break: break-all; }
[data-testid="stAlert"] { background: #1b130acc !important; border: 1px solid #7a5d2a !important; border-left: 4px solid var(--ember) !important; color: var(--ink) !important; border-radius: 6px; }
[data-testid="stAlert"] p { color: var(--ink) !important; }
[data-testid="stToast"] { background: linear-gradient(180deg, #1d1810, #0b0a07) !important; border: 1px solid var(--gold) !important; color: var(--ink) !important; font-family: var(--body); box-shadow: 0 0 22px #ff9d2e44 !important; }
[data-testid="stCaptionContainer"], .stCaption { color: var(--muted) !important; }
[data-testid="stCheckbox"] label p, .st-key-muted label p { color: var(--ink) !important; font: 600 .95rem var(--title) !important; letter-spacing: .04em; text-transform: none; }
[data-testid="stMarkdownContainer"] table { border-collapse: collapse; width: 100%; }
[data-testid="stMarkdownContainer"] table th { color: var(--gold); font-family: var(--title); border-bottom: 1px solid #7a5d2a; background: #ffffff06; }
[data-testid="stMarkdownContainer"] table td { border-bottom: 1px solid #ffffff12; }
hr { border-color: #5c4720 !important; }
__ICONS__

/* elementos invisíveis (CSS, camadas fixas, áudio) não ocupam espaço nem "gap" no layout */
[data-testid="stElementContainer"]:has(#uno-css), [data-testid="stElementContainer"]:has(.ambient), [data-testid="stLayoutWrapper"]:has(> .st-key-sfx), [data-testid="stLayoutWrapper"]:has(> .st-key-musicslot), [data-testid="stLayoutWrapper"]:has(> .st-key-musictension),
[data-testid="stLayoutWrapper"]:has(> .st-key-portalslot), [data-testid="stLayoutWrapper"]:has(> .st-key-fxslot),
[data-testid="stLayoutWrapper"]:has(> .st-key-heraldslot), .st-key-portalslot, .st-key-heraldslot { position: absolute !important; }
.st-key-portalslot, .st-key-heraldslot { position: fixed !important; left: 0; bottom: 0; width: 1px !important; height: 1px !important; overflow: visible; pointer-events: none; z-index: 999991; }
/* ---------- barra do topo ---------- */
[data-testid="stHeaderActionElements"], [data-testid="stHeadingLink"] { display: none !important; }
.st-key-topbar { flex-wrap: wrap; row-gap: .3rem; padding-bottom: .2rem; }
.st-key-topbar > div:first-child { flex: 1 1 260px; min-width: 0; }
.topline { display:flex; align-items:center; gap:.5rem; font: 600 .82rem var(--title); color: var(--muted); letter-spacing: .06em; }
.topline .ico { color: var(--ember); }

/* ---------- código da sala ---------- */
.code-tiles { display: flex; gap: .45rem; justify-content: center; margin: .4rem 0 1rem; flex-wrap: wrap; }
.code-tiles span {
  font: 900 2.3rem var(--deco); width: 3.3rem; height: 4rem; display: grid; place-items: center;
  background: linear-gradient(180deg, #3a3326, #16130d); color: var(--gold2); border-radius: 6px; border: 1px solid var(--gold);
  box-shadow: inset 0 0 0 3px #0b0a07, inset 0 0 0 4px #d9a44144, 0 6px 0 #000, 0 0 22px #ff9d2e33; text-shadow: 0 0 12px #ff9d2e;
  animation: tile-in .6s cubic-bezier(.2,1.6,.4,1) both;
}
.code-tiles span:nth-child(2){animation-delay:.07s}.code-tiles span:nth-child(3){animation-delay:.14s}
.code-tiles span:nth-child(4){animation-delay:.21s}.code-tiles span:nth-child(5){animation-delay:.28s}
@keyframes tile-in { from { transform: translateY(-30px) rotateX(80deg); opacity: 0; } }
.room-head { text-align:center; margin-bottom: .6rem; }
.room-name { font: 900 clamp(1.8rem, 6vw, 3rem) var(--deco); color: var(--gold2); line-height: 1.1; text-shadow: 0 3px 0 #000, 0 0 24px #ff9d2e66;
  overflow-wrap: anywhere; animation: tile-in .7s cubic-bezier(.2,1.4,.4,1) both; }
.room-head .room-eyebrow { font-size: .9rem; margin-top: .3rem; color: var(--muted); }
.room-head .code-tiles { margin: .35rem 0 .5rem; }
.room-head .code-tiles span { width: 2.6rem; height: 3.1rem; font-size: 1.7rem; }
.share-row { display:flex; gap:.5rem; justify-content:center; flex-wrap: wrap; }
.share-btn { display:inline-flex; align-items:center; justify-content:center; gap:.4rem; min-height: 44px; padding: 0 .9rem; cursor: pointer;
  font: 700 .85rem var(--title); letter-spacing: .05em; color: var(--gold2); background: linear-gradient(180deg, #2c2416, #16110a);
  border: 1px solid #7a5d2a; border-radius: 6px; box-shadow: inset 0 1px 0 #f6d98a33, 0 3px 0 #000; transition: transform .12s, box-shadow .2s; }
.share-btn:hover { border-color: var(--gold); box-shadow: 0 3px 0 #000, 0 0 14px #ff9d2e55; }
.share-btn:active { transform: translateY(2px); }
.share-btn .ok { display: none; color: #a7f0b9; }
.share-btn.done { border-color: #3f8a55; } .share-btn.done .lbl { display: none; } .share-btn.done .ok { display: inline; }
.paste-btn { width: 100%; white-space: nowrap; padding: 0 .6rem; }
.st-key-room_chips button { min-height: 32px; padding: .1rem .7rem; border-radius: 999px; background: #0b0a07; border: 1px solid #5c4720; }
.st-key-room_chips button p { font: 600 .82rem var(--body); color: var(--muted); }
.st-key-room_chips button:hover { border-color: var(--gold); } .st-key-room_chips button:hover p { color: var(--gold2); }
.st-key-create_box [data-testid="stHorizontalBlock"], [class*="st-key-join_box"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .5rem !important; }
.st-key-create_box [data-testid="stColumn"], [class*="st-key-join_box"] [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; }
.st-key-create_box [data-testid="stColumn"]:first-child, [class*="st-key-join_box"] [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; }
.st-key-create_box [data-testid="stColumn"]:last-child, [class*="st-key-join_box"] [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; }
.paste-hint { display: none; font: 500 .78rem var(--body); color: var(--muted); line-height: 1.2; }
.no-clip-read .paste-btn { display: none; } .no-clip-read .paste-hint { display: block; padding-bottom: .5rem; }
.st-key-join_box_invited [data-testid="stForm"] { border-color: var(--gold) !important; box-shadow: inset 0 0 0 4px #0b0a07, inset 0 0 0 5px #d9a44166, 0 0 30px #ff9d2e44, 0 12px 30px #000c; }
.chip { display:inline-block; padding:.15rem .6rem; border-radius:999px; background:#ffffff10; border:1px solid #d9a44155;
  font: 600 .8rem var(--title); color: var(--ink); margin: .1rem .2rem .1rem 0; }
.swatch { display:inline-block; border-radius:50%; border:2px solid #fff; vertical-align:middle; box-shadow:0 0 12px currentColor; }

/* ---------- jogadores ---------- */
.avatar { position: relative; width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; flex: none;
  box-shadow: 0 0 0 2px #0b0a07, 0 0 0 3px #9c7630, 0 4px 10px #000; }
.avatar .av-svg { width: 100%; height: 100%; display:block; border-radius: 50%; }
/* contas */
.st-key-cookiejar { position: absolute !important; width: 1px; height: 1px; overflow: hidden; opacity: 0; pointer-events: none; }
[data-testid="stLayoutWrapper"]:has(> .st-key-cookiejar), [data-testid="stElementContainer"]:has(.st-key-cookiejar) { position: absolute !important; }
.acct { display: flex; align-items: center; gap: .45rem; font: 600 .9rem var(--title); color: var(--gold2); white-space: nowrap; }
.acct .avatar { width: 30px; height: 30px; }
.acct span { max-width: 140px; overflow: hidden; text-overflow: ellipsis; }
.playing-as { font: 500 .95rem var(--body); color: var(--muted); margin: .1rem 0 .2rem; }
.playing-as b { color: var(--gold2); font-family: var(--title); }
.auth-or { display: flex; align-items: center; gap: .6rem; color: var(--muted); font: 500 .85rem var(--body); margin: .2rem 0; }
.auth-or::before, .auth-or::after { content: ''; flex: 1; height: 1px; background: #5c472088; }
.st-key-auth_box [data-testid="stForm"] { border: none !important; box-shadow: none !important; background: none !important; padding: 0 !important; }
.st-key-auth_box [data-testid="stForm"]::before, .st-key-auth_box [data-testid="stForm"]::after { display: none !important; }
.st-key-guest_btn button p { color: var(--muted) !important; text-decoration: underline; text-underline-offset: 3px; }
.auto-badge { display: inline-flex; align-items: center; gap: .35rem; padding: .2rem .7rem; border-radius: 999px;
  border: 1px solid var(--gold); color: var(--gold2); background: #2a1d0bcc; font: 600 .85rem var(--title); letter-spacing: .04em; }
.auto-badge .ico { color: var(--ember); }
.st-key-auto_on_box { justify-content: center; }
.st-key-auto_warn { border-color: var(--ember) !important; }
.st-key-back_box { border-color: var(--gold) !important; }
/* retratos: animação sutil (no lobby, na minha barra e no hover) */
.av-svg .av-sway, .av-svg .av-bob, .av-svg .av-flick, .av-svg .av-glow, .av-svg .av-float { transform-box: fill-box; transform-origin: center; }
.av-svg .av-flick { transform-origin: 50% 100%; } .av-svg .av-sway { transform-origin: 20% 100%; }
:is(.lobby-player, .mybar, .avatar:hover) .av-sway { animation: av-sway 2.6s ease-in-out infinite; }
:is(.lobby-player, .mybar, .avatar:hover) .av-bob { animation: av-bob 2.2s ease-in-out infinite; }
:is(.lobby-player, .mybar, .avatar:hover) .av-flick { animation: av-flick .45s ease-in-out infinite alternate; }
:is(.lobby-player, .mybar, .avatar:hover) .av-glow { animation: av-glow 1.8s ease-in-out infinite; }
:is(.lobby-player, .mybar, .avatar:hover) .av-float { animation: av-float 1.6s ease-in-out infinite; }
@keyframes av-sway { 0%,100% { transform: rotate(-4deg); } 50% { transform: rotate(4deg); } }
@keyframes av-bob { 50% { transform: translateY(-1.2px); } }
@keyframes av-flick { from { transform: scaleY(.9) skewX(-3deg); } to { transform: scaleY(1.08) skewX(3deg); } }
@keyframes av-glow { 50% { opacity: .55; } }
@keyframes av-float { 50% { transform: translateY(-1.5px); opacity: .5; } }

/* seletor de personagem (st.radio com retratos) */
[class*="st-key-avpick_"] [role="radiogroup"] { display: grid !important; grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
  gap: .3rem .15rem; padding: .15rem .1rem .3rem; }
[class*="st-key-avpick_"] [role="radiogroup"] [data-testid="stRadioOption"] { display: flex; flex-direction: column; align-items: center; gap: .2rem; margin: 0 !important;
  padding: .3rem 0 .15rem; border-radius: 10px; cursor: pointer; min-width: 0; position: relative; }
[class*="st-key-avpick_"] [role="radiogroup"] [data-testid="stRadioOption"]::before { content: ''; width: 44px; height: 44px; flex: none; border-radius: 50%;
  background: center / contain no-repeat; box-shadow: 0 0 0 2px #0b0a07, 0 0 0 3px #5c4720, 0 3px 8px #000a; transition: transform .15s, box-shadow .15s; }
[class*="st-key-avpick_"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) { position: absolute !important; opacity: 0; width: 1px; height: 1px; overflow: hidden; }
[class*="st-key-avpick_"] [role="radiogroup"] [data-testid="stRadioOption"] p { font: 600 .7rem/1.1 var(--body) !important; color: var(--muted) !important; white-space: nowrap;
  max-width: 64px; overflow: hidden; text-overflow: ellipsis; text-align: center; margin: 0; }
[class*="st-key-avpick_"] [role="radiogroup"] [data-testid="stRadioOption"]:hover::before { box-shadow: 0 0 0 2px #0b0a07, 0 0 0 3px var(--gold), 0 3px 10px #000a; transform: translateY(-2px); }
[class*="st-key-avpick_"] [role="radiogroup"] [data-testid="stRadioOption"][data-selected="true"]::before { box-shadow: 0 0 0 2px #0b0a07, 0 0 0 4px #e9c46a, 0 0 16px #ff9d2eaa; transform: scale(1.08); }
[class*="st-key-avpick_"] [role="radiogroup"] [data-testid="stRadioOption"][data-selected="true"] p { color: var(--gold2) !important; }
[class*="st-key-avpick_"] [role="radiogroup"] [data-testid="stRadioOption"]:has(input:focus-visible)::before { outline: 2px solid #fff3cf; outline-offset: 3px; }
[class*="st-key-avpick_"] [data-testid="stRadioOption"][data-disabled="true"] { opacity: .3; filter: grayscale(.9); pointer-events: none; }
__AVATARS__
.dot { position: absolute; right: -3px; bottom: -3px; width: 13px; height: 13px; border-radius: 50%; border: 2px solid #0b0a07; }
.dot.on { background: #6ee07a; box-shadow: 0 0 8px #6ee07a; }
.dot.off { background: #6b6b6b; }
.dot.bot { background: #b98cff; box-shadow: 0 0 8px #b98cff88; }
.seats { display: flex; flex-wrap: wrap; gap: .7rem; justify-content: center; margin-bottom: .6rem; }
.seat {
  position: relative; min-width: 150px; flex: 1 1 150px; max-width: 230px; padding: .55rem .7rem .6rem;
  background: linear-gradient(180deg, #120f0ae6, #070605e6); border: 1px solid #5c4720; border-radius: 8px; transition: transform .3s;
  box-shadow: inset 0 0 0 3px #0b0a07, 0 6px 14px #000a;
}
.seat.turn { border-color: var(--gold); animation: turn-pulse 1.4s ease-in-out infinite; transform: translateY(-3px); }
@keyframes turn-pulse { 0%,100% { box-shadow: 0 0 0 0 #ff9d2e66, inset 0 0 0 3px #0b0a07; } 50% { box-shadow: 0 0 0 8px #ff9d2e00, 0 0 24px #ff9d2eaa, inset 0 0 0 3px #0b0a07; } }
.seat .top { display:flex; align-items:center; gap:.55rem; }
.seat .nm { font: 700 .98rem var(--title); color: var(--gold2); line-height: 1.15; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 150px; }
.seat .sub { font: 500 .78rem var(--body); color: var(--muted); }
.badge-host { color: var(--gold); }
.fan { display: flex; margin-top: .45rem; height: 44px; padding-left: 10px; }
.fan .mini { width: 30px; height: 45px; margin-left: -14px; transform-origin: 50% 120%; filter: drop-shadow(1px 2px 1px #0008);
  border-radius: 4px; border: 2px solid #d9b56a; position: relative; overflow: hidden;
  background: radial-gradient(ellipse 55% 50% at 50% 55%, #ffd23f 0 22%, #ff5a1a 23% 45%, transparent 46%), linear-gradient(135deg, #1d3a24, #050c07); }
.fan .more { align-self: center; margin-left: 6px; font: 700 .9rem var(--title); color: var(--gold2); }
.badge-uno { position:absolute; top:-12px; right:-8px; background: linear-gradient(180deg, #e0401f, #7a1408); color:#fff3cf; font: 900 .8rem var(--title);
  padding: .14rem .5rem; border-radius: 4px; border: 1px solid var(--gold); transform: rotate(8deg); animation: wobble 1s ease-in-out infinite; box-shadow:0 3px 0 #000, 0 0 14px #ff5a1a; }
@keyframes wobble { 0%,100% { transform: rotate(8deg) scale(1); } 50% { transform: rotate(-6deg) scale(1.12); } }
.lobby-player { display:flex; align-items:center; gap:.7rem; padding:.5rem .7rem; border-radius: 6px; background: linear-gradient(90deg, #1a150ccc, #0b0a07aa);
  border:1px solid #5c4720; margin-bottom:.45rem; animation: log-in .5s ease both; }
.lobby-player b { font-family: var(--title); color: var(--gold2); font-size: 1.02rem; }
.lobby-player .tag { font: 500 .78rem var(--body); color: var(--muted); }
.lobby-player .ico-crown { color: var(--gold); margin-left: .25rem; }

/* ---------- mesa central (clareira com pedra e musgo) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > .st-key-table) { border: none !important; }
.st-key-table {
  background: radial-gradient(ellipse at 50% 45%, #1c3a26 0%, #0f2418 45%, #07110b 80%), #07110b;
  border: 1px solid #7a5d2a; border-radius: 14px; padding: 1rem 1rem 1.2rem;
  box-shadow: inset 0 0 0 5px #120d06, inset 0 0 0 6px #d9a44144, inset 0 0 70px #000d, 0 14px 40px #000c;
}
.center { display:flex; align-items:center; justify-content:center; gap: clamp(.8rem, 4vw, 2.6rem); flex-wrap: wrap; padding: .4rem 0 1.8rem; }
.pile { position: relative; width: 120px; height: 180px; }
.pile .stack { position:absolute; inset:0; }
.pile .stack:nth-child(1) { transform: translate(5px, 5px) rotate(3deg); opacity: .7; }
.pile .stack:nth-child(2) { transform: translate(2px, 2px) rotate(-2deg); opacity: .85; }
.pile svg { width: 120px; height: 180px; display:block; filter: drop-shadow(0 6px 6px #0009); }
.pile .count { position:absolute; bottom:-24px; width:100%; text-align:center; font: 600 .78rem var(--title); color: var(--muted); letter-spacing: .05em; }
.discard .ring { position:absolute; inset:-12px; border-radius: 16px; border: 3px solid var(--cur); box-shadow: 0 0 26px var(--cur), inset 0 0 18px var(--cur);
  animation: ring-glow 2s ease-in-out infinite; }
@keyframes ring-glow { 50% { box-shadow: 0 0 6px var(--cur), inset 0 0 4px var(--cur); } }
.discard .under { position:absolute; inset:0; transform: rotate(var(--r2, -8deg)); opacity:.75; }
.discard .topc { position:absolute; inset:0; transform: rotate(var(--r, 4deg)); }
.discard .topc .uno-card { width: 120px; }
.discard .topc.fly-in { animation: fly-in .55s cubic-bezier(.2,.9,.3,1.15) both; }
.discard .topc.fly-in.from-me { --fy: 260px; }
@keyframes fly-in {
  0% { transform: translate(var(--fx, 0px), var(--fy, -240px)) rotate(-200deg) scale(.6); opacity: 0; }
  60% { opacity: 1; }
  100% { transform: rotate(var(--r, 4deg)) scale(1); }
}
.direction { color: var(--gold); display:inline-block; filter: drop-shadow(0 0 8px #ff9d2e88); animation: spin-cw 4s linear infinite; }
.direction.ccw { animation-name: spin-ccw; }
@keyframes spin-cw { to { transform: rotate(360deg); } }
@keyframes spin-ccw { to { transform: rotate(-360deg); } }
.status { text-align:center; max-width: 280px; }
.status .big { font: 900 1.2rem var(--title); color: var(--gold2); letter-spacing: .05em; }
.status .big.me { color: #fff3cf; animation: my-turn 1.1s ease-in-out infinite; }
@keyframes my-turn { 50% { text-shadow: 0 0 16px #ff9d2e, 0 0 2px #fff; transform: scale(1.05); } }
.status .small { font: 500 .88rem var(--body); color: var(--muted); }

/* ---------- cartas ---------- */
.uno-card, [class*="st-key-hc_"], .pile { -webkit-touch-callout: none; -webkit-user-select: none; user-select: none; }
.uno-card { position: relative; width: 100%; transition: transform .22s cubic-bezier(.2,1.4,.4,1), filter .2s; transform-origin: 50% 100%; }
.uno-card svg { width: 100%; height: auto; display: block; filter: drop-shadow(0 4px 4px #000a); border-radius: 10px; -webkit-user-drag: none; }
.uno-card.dim { filter: saturate(.5) brightness(.62); }
.uno-card.playable svg { animation: playable-glow 1.6s ease-in-out infinite; }
@keyframes playable-glow { 0%,100% { filter: drop-shadow(0 0 4px #ffb02e) drop-shadow(0 4px 4px #000a); }
  50% { filter: drop-shadow(0 0 14px #ffb02e) drop-shadow(0 0 4px #fff3cf); } }
.uno-card .pill { position:absolute; left:50%; bottom:-8px; transform: translateX(-50%); background: var(--gold); color:#1b1206;
  font: 900 .66rem var(--title); padding: .12rem .5rem; border-radius: 999px; box-shadow: 0 2px 0 #5a3c08; white-space: nowrap; }
.uno-card.drawn .pill { background: #6ee07a; box-shadow: 0 2px 0 #1a7a45; }
.uno-card.deal { animation: deal-in .5s cubic-bezier(.2,1.3,.4,1) both; animation-delay: var(--d, 0s); }
@keyframes deal-in { from { transform: translate(-60px, -160px) rotate(-30deg) scale(.4); opacity: 0; } }

/* SVG internos: cartas especiais (Saci, Curupira, Cuca, Iara, Mula) vivem sempre;
   as numéricas animam no hover e no topo do descarte */
.fx-spin, .fx-spin-slow, .fx-flicker, .fx-float, .fx-sway, .fx-hop, .fx-twinkle, .fx-glow, .fx-bloom, .fx-gallop, .fx-leap, .fx-look,
.fx-cap, .fx-eyeglow, .fx-ripple, .fx-shimmer, .fx-steps { transform-box: fill-box; transform-origin: center; }
:is(.uno-card:hover, .discard, .live) .fx-spin { animation: spin-cw 2.2s linear infinite; }
:is(.uno-card:hover, .discard, .live) .fx-spin-slow { animation: spin-cw 6s linear infinite; }
:is(.uno-card:hover, .discard, .live) .fx-flicker { animation: flicker .35s ease-in-out infinite alternate; transform-origin: 50% 100%; }
:is(.uno-card:hover, .discard, .live) .fx-float { animation: floaty 1.4s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-sway { animation: sway 1.6s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-hop { animation: hop .7s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-gallop { animation: hop .45s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-leap { animation: leap 1.6s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-twinkle { animation: twinkle 1s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-glow { animation: glow-pulse 1.4s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-bloom { animation: bloom 2s ease-in-out infinite; transform-origin: 50% 100%; }
:is(.uno-card:hover, .discard, .live) .fx-look { animation: look 2s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-cap { animation: cap-sway 1.3s ease-in-out infinite; transform-origin: 0% 100%; }
:is(.uno-card:hover, .discard, .live) .fx-eyeglow { animation: eye-glow 1.5s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-ripple { animation: ripple 2.2s linear infinite; transform-box: view-box; }
:is(.uno-card:hover, .discard, .live) .fx-ripple.r2 { animation-duration: 1.6s; animation-direction: reverse; }
:is(.uno-card:hover, .discard, .live) .fx-shimmer { animation: shimmer 1.2s ease-in-out infinite; }
:is(.uno-card:hover, .discard, .live) .fx-steps { animation: steps 1.5s ease-in-out infinite; }
@keyframes flicker { from { transform: scaleY(.88) skewX(-4deg); } to { transform: scaleY(1.12) skewX(4deg); } }
@keyframes floaty { 50% { transform: translateY(-5px); opacity: .55; } }
@keyframes sway { 0%,100% { transform: rotate(-3deg); } 50% { transform: rotate(3deg); } }
@keyframes hop { 50% { transform: translateY(-4px); } }
@keyframes leap { 50% { transform: translate(3px, -6px) rotate(-6deg); } }
@keyframes twinkle { 50% { opacity: .2; transform: scale(.6); } }
@keyframes glow-pulse { 50% { opacity: .55; transform: scale(1.08); } }
@keyframes bloom { 50% { transform: scale(1.08); } }
@keyframes look { 0%,100% { transform: translateX(0); } 30% { transform: translateX(-2px); } 70% { transform: translateX(2px); } }
@keyframes cap-sway { 0%,100% { transform: rotate(-6deg); } 50% { transform: rotate(7deg); } }
@keyframes eye-glow { 0%,100% { fill: #ffeb3b; } 50% { fill: #ff8a00; filter: drop-shadow(0 0 3px #ffeb3b); } }
@keyframes ripple { to { transform: translateX(-34px); } }
@keyframes shimmer { 50% { stroke: #ffffff; opacity: .4; } }
@keyframes steps { 0%,100% { opacity: .25; } 50% { opacity: 1; } }

/* ---------- visualização ampliada (hover no PC, segurar no celular) ---------- */
#uno-pv-bg { position: fixed; inset: 0; background: #000000c4; z-index: 1000000; display: none; backdrop-filter: blur(2px); }
#uno-pv-bg.show { display: block; }
#uno-pv { position: fixed; z-index: 1000001; display: none; gap: .9rem; width: 470px; max-width: calc(100vw - 20px); pointer-events: none;
  padding: .9rem; background: __CORNERS__, linear-gradient(170deg, #1a1610f7, #0b0a07fa); border: 1px solid var(--gold); border-radius: 8px;
  box-shadow: inset 0 0 0 4px #0b0a07, inset 0 0 0 5px #d9a44144, 0 18px 50px #000, 0 0 30px #ff9d2e33; animation: pv-in .16s ease-out both; }
#uno-pv.show { display: flex; }
#uno-pv .pv-card { flex: 0 0 210px; width: 210px; }
#uno-pv .pv-card svg { width: 100%; height: auto; filter: drop-shadow(0 8px 10px #000); }
#uno-pv .pv-info { flex: 1; min-width: 0; color: var(--ink); font-family: var(--body); }
#uno-pv .pv-name { font: 900 1.3rem var(--title); color: var(--gold2); line-height: 1.15; }
#uno-pv .pv-sub { font: 700 1rem var(--title); color: var(--ember); letter-spacing: .06em; margin: .2rem 0 .5rem; }
#uno-pv .pv-effect { font-size: 1.05rem; font-weight: 700; line-height: 1.35; color: #fff3cf; padding: .45rem .55rem; border-left: 3px solid var(--ember); background: #ffffff08; }
#uno-pv .pv-blurb { font-size: 1rem; line-height: 1.4; margin-top: .55rem; color: #e3d6b5; font-style: italic; }
#uno-pv.mobile { left: 50% !important; top: 50% !important; transform: translate(-50%, -50%); flex-direction: column; align-items: center;
  width: min(92vw, 400px); max-height: 92vh; overflow-y: auto; animation: pv-pop .18s ease-out both; }
#uno-pv.mobile .pv-card { flex: none; width: min(60vw, 250px); }
#uno-pv.mobile .pv-info { text-align: center; }
#uno-pv.mobile .pv-effect { border-left: none; border-top: 3px solid var(--ember); text-align: left; }
@keyframes pv-in { from { opacity: 0; transform: scale(.94); } }
@keyframes pv-pop { from { opacity: 0; transform: translate(-50%, -46%) scale(.9); } }

/* ---------- mão do jogador (cada carta = container com botão invisível por cima) ---------- */
.st-key-hand { max-height: 480px; overflow-y: auto; overflow-x: hidden; padding: 1.5rem .5rem 1rem; justify-content: center;
  background: linear-gradient(180deg, #0000, #00000055); border-radius: 12px; border-top: 1px solid #5c472055; transition: box-shadow .4s; }
.st-key-hand.turn-glow, .hand-turn ~ div .st-key-hand { box-shadow: inset 0 0 40px #ff9d2e33, 0 0 0 1px #e2b04e88; }
.st-key-hand > div { flex: 0 0 auto; }
[class*="st-key-hc_"] { position: relative; width: 104px !important; flex: 0 0 104px !important; gap: 0 !important; }
[class*="st-key-hc_"]:hover .uno-card.playable, [class*="st-key-hc_"]:hover .uno-card.drawn { transform: translateY(-16px) rotate(-3deg) scale(1.06); z-index: 5; }
[class*="st-key-hc_"]:hover .uno-card { transform: translateY(-6px); }
[class*="st-key-play_"] { position: absolute !important; inset: 0; z-index: 6; }
[class*="st-key-play_"] button, [class*="st-key-play_"] .stButton, [class*="st-key-play_"] div { width: 100% !important; height: 100% !important; }
[class*="st-key-play_"] button { opacity: 0 !important; cursor: pointer; min-height: 0; -webkit-touch-callout: none; user-select: none; }
[class*="st-key-play_"] button:disabled { cursor: not-allowed; }
.st-key-hand > [data-testid="stLayoutWrapper"], .st-key-hand > [data-testid="stElementContainer"] { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }
.mybar { display:flex; align-items:center; gap:.65rem; flex-wrap: wrap; margin: .7rem 0 .2rem; }
.mybar .avatar { width: 46px; height: 46px; }
.mybar .nm { font: 900 1.05rem var(--title); color: var(--gold2); }
.mybar .sub { font: 500 .88rem var(--body); color: var(--muted); }
.mybar.turn .avatar { animation: turn-pulse 1.4s ease-in-out infinite; }
.hint { font: 600 .98rem var(--body); color: var(--gold2); text-align: center; margin: .3rem 0; }
.hint .ico { color: var(--ember); }

/* ---------- botões especiais ---------- */
.st-key-btn_uno button { background: radial-gradient(circle, #ffe25a, #ff7a1a 55%, #9b1d1d) !important; color: #1b1206 !important;
  font: 900 1.6rem var(--deco) !important; border: 2px solid #fff3cf !important; animation: uno-btn 0.9s ease-in-out infinite; box-shadow: 0 5px 0 #3a0703 !important; }
@keyframes uno-btn { 50% { transform: scale(1.05) rotate(-1.5deg); box-shadow: 0 0 26px #ffb02e, 0 5px 0 #3a0703; } }
[class*="st-key-den_"] button { background: linear-gradient(180deg, #d42a4a, #6d0a1c) !important; color:#fff !important; border-color: #ffb3c0 !important; animation: uno-btn .7s ease-in-out infinite; }
.st-key-pick_red button { background: linear-gradient(180deg, #ff5a3d, #8e1508) !important; color:#fff !important; }
.st-key-pick_green button { background: linear-gradient(180deg, #3fcf72, #0c5a2c) !important; color:#fff !important; }
.st-key-pick_blue button { background: linear-gradient(180deg, #4aa3ff, #0b3a85) !important; color:#fff !important; }
.st-key-pick_yellow button { background: linear-gradient(180deg, #ffd23f, #a86a00) !important; color:#1b1206 !important; }
[class*="st-key-pick_"] button { border: 2px solid #fff3cf !important; box-shadow: 0 4px 0 #000, 0 0 16px #0008; height: 3.3rem; }
[class*="st-key-pick_"] button:hover { transform: scale(1.04); }

/* ---------- registro / placar ---------- */
.log { max-height: 280px; overflow-y: auto; font: 500 .9rem var(--body); padding-right: .3rem; }
.log div { padding: .32rem .2rem; border-bottom: 1px dashed #d9a44122; animation: log-in .4s ease both; }
.log div:first-child { color: var(--gold2); }
@keyframes log-in { from { opacity: 0; transform: translateX(-12px); } }
.scores { width:100%; border-collapse: collapse; } .scores td { padding:.4rem .45rem; border-bottom:1px solid #d9a44122; vertical-align: middle; }
.scores .avatar { width: 26px; height: 26px; display:inline-grid; vertical-align: middle; margin-right: .35rem; box-shadow: 0 0 0 1px #9c7630; }
.small-muted { font: 500 .9rem var(--body); color: var(--muted); }
.result-row { display:flex; justify-content: space-between; gap: .5rem; padding: .4rem .5rem; border-bottom: 1px solid #d9a44122; flex-wrap: wrap; }
.result-row.win { background: linear-gradient(90deg, #e2b04e33, transparent); font-weight: 800; color: var(--gold2); }

/* ---------- bestiário / ranking ---------- */
.bestiary { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; }
.beast { display:flex; gap:.8rem; background: linear-gradient(170deg, #17140ee6, #0b0a07ee); border:1px solid #5c4720; border-radius:8px; padding:.75rem;
  box-shadow: inset 0 0 0 3px #0b0a07, 0 8px 18px #0009; }
.beast .art { flex: 0 0 96px; }
.beast h4 { margin: 0 0 .2rem !important; font-size: 1.05rem !important; padding: 0 !important; }
.beast .role { font: 700 .72rem var(--title); color: var(--ember); text-transform: uppercase; letter-spacing: .08em; }
.beast p { font-size: .92rem; margin: .25rem 0; line-height: 1.35; color: #e3d6b5; }
.beast .power { color: #a7f0b9; font-weight: 700; }
.biomes { display:grid; grid-template-columns: repeat(auto-fit, minmax(210px,1fr)); gap:.7rem; margin-bottom:1rem; }
.biome { border-radius: 8px; padding: .75rem .9rem; color: #fff; font-size: .95rem; border: 1px solid #ffffff33; box-shadow: inset 0 0 30px #0007, 0 6px 14px #0009; }
.biome b { font: 900 1.05rem var(--title); letter-spacing: .05em; }
.rank-badge { display:inline-flex; align-items:center; gap:.35rem; font: 700 .76rem var(--title); letter-spacing: .1em; text-transform: uppercase;
  padding: .2rem .6rem; border-radius: 999px; border: 1px solid #5c4720; color: var(--muted); }
.rank-badge.on { color: #a7f0b9; border-color: #3f8a55; box-shadow: 0 0 12px #3f8a5544; }
.podium { display:flex; justify-content:center; align-items:flex-end; gap: clamp(.4rem, 2vw, 1.4rem); margin: 1rem 0 1.2rem; flex-wrap: nowrap; }
.podium-step { display:flex; flex-direction:column; align-items:center; gap:.25rem; width: clamp(92px, 26vw, 170px); text-align:center; }
.podium-name { font: 900 1rem var(--title); color: var(--gold2); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.podium-wins { font: 500 .85rem var(--body); color: var(--muted); }
.podium-base { width: 100%; display:grid; place-items:center; font: 900 1.6rem var(--deco); color: #1b1206;
  background: linear-gradient(180deg, #e9c46a, #8a5a12); border: 1px solid #2a1804; border-radius: 4px 4px 0 0; box-shadow: inset 0 2px 0 #fff3bf88, 0 8px 18px #000a; }
.podium-step.p1 .podium-base { height: 92px; } .podium-step.p2 .podium-base { height: 66px; background: linear-gradient(180deg, #e5e7eb, #6b7280); }
.podium-step.p3 .podium-base { height: 48px; background: linear-gradient(180deg, #e8a868, #6b3a12); }
.podium-step.me .podium-name { color: #a7f0b9; text-shadow: 0 0 10px #3f8a55; }
.podium-crown { color: var(--gold2); filter: drop-shadow(0 0 10px #ff9d2e); animation: hop 1.6s ease-in-out infinite; }
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
table.rank { width:100%; border-collapse: collapse; font-size: .95rem; min-width: 560px; }
table.rank th { font: 700 .74rem var(--title); color: var(--gold); text-align:left; padding:.45rem; border-bottom: 1px solid #7a5d2a; letter-spacing: .06em; }
table.rank td { padding:.5rem .45rem; border-bottom: 1px solid #d9a4441a; }
table.rank tr.me td { background: #3f8a5522; }
table.rank tr.me td:first-child { box-shadow: inset 3px 0 0 #6ee07a; }
.you-tag { font: 700 .66rem var(--title); color: #0b1a10; background: #6ee07a; border-radius: 999px; padding: .05rem .4rem; margin-left: .3rem; vertical-align: middle; }

/* ---------- efeitos de evento (sobreposição de tela) ---------- */
.st-key-sfx, .st-key-fxslot, .st-key-heraldslot { position: fixed !important; left: 0; bottom: 0; width: 1px !important; height: 1px !important; overflow: visible; pointer-events: none; z-index: 999990; }
.st-key-sfx { opacity: 0; overflow: hidden; }
.st-key-musicslot, .st-key-musictension { position: fixed !important; left: 0; bottom: 0; width: 1px !important; height: 1px !important; opacity: 0; overflow: hidden; pointer-events: none; }
.st-key-musicslot iframe, .st-key-musictension iframe { width: 1px !important; height: 1px !important; }
.st-key-sfx iframe { width: 1px !important; height: 1px !important; }
.fx-layer { position: fixed; inset: 0; pointer-events: none; z-index: 999990; display:grid; place-items:center; overflow:hidden; }
.fx-layer > * { grid-area: 1 / 1; }
.fx-layer .fx-text { position: relative; z-index: 5; font: 900 clamp(2.6rem, 10vw, 6rem) var(--deco); color: #fff6dc; -webkit-text-stroke: 2px #1b0f04;
  text-shadow: 0 6px 0 #000, 0 0 30px var(--c, #ffd23f), 0 0 60px var(--c, #ffd23f); animation: fx-pop 1.9s cubic-bezier(.2,1.5,.4,1) both; text-align:center; padding: 0 4vw; }
.fx-layer .fx-sub { display:block; font: 700 clamp(.95rem, 3.4vw, 1.5rem) var(--title); -webkit-text-stroke: 0; letter-spacing: .04em; color: #fff3cf; text-shadow: 0 2px 4px #000, 0 0 12px #000; margin-top: .3rem; }
@keyframes fx-pop { 0% { transform: scale(.2) rotate(-10deg); opacity: 0; } 22% { transform: scale(1.1) rotate(2deg); opacity: 1; }
  78% { transform: scale(1) rotate(0); opacity: 1; } 100% { transform: scale(1.3); opacity: 0; } }
.fx-flash { position:absolute; inset:0; background: var(--c); animation: flash 1s ease-out both; }
@keyframes flash { from { opacity: .45; } to { opacity: 0; } }
/* Saci: redemoinho + gorro voando */
.fx-whirlwind { position:absolute; width: min(70vmin, 520px); height: min(70vmin, 520px); animation: ww-move 2.2s ease-in-out both; }
.fx-whirlwind .ww-spin { transform-origin: 100px 120px; animation: ww-spin .5s linear infinite; }
@keyframes ww-spin { to { transform: rotateY(360deg); } }
@keyframes ww-move { 0% { transform: translateX(-60vw) scale(.4); opacity: 0; } 25% { opacity: 1; } 60% { transform: translateX(0) scale(1); opacity: 1; } 100% { transform: translateX(60vw) scale(.6); opacity: 0; } }
.fx-cap-fly { position:absolute; width: 90px; animation: cap-fly 2.2s ease-in-out both; }
@keyframes cap-fly { 0% { transform: translate(-50vw, 20vh) rotate(0); opacity: 0; } 20% { opacity: 1; } 100% { transform: translate(50vw, -40vh) rotate(1080deg); opacity: 0; } }
.fx-dust { position:absolute; left:0; right:0; bottom:0; height: 30vh; background: radial-gradient(ellipse at 50% 100%, #b99a6a55, transparent 70%); animation: flash 2s ease-out both; }
/* Curupira: setas, pegadas ao contrário e cabelo de fogo */
.fx-turn-arrows { position:absolute; color: #6ee07a; filter: drop-shadow(0 0 20px #3ddc84); animation: arrows 1.8s ease-in-out both; }
.fx-turn-arrows svg { width: 50vmin; height: 50vmin; }
@keyframes arrows { 0% { transform: rotate(0) scale(.3); opacity:0 } 30% { opacity:.9 } 100% { transform: rotate(-540deg) scale(1.1); opacity:0 } }
.fx-footprints { position:absolute; bottom: 8vh; width: 90vw; max-width: 900px; animation: feet 2.2s linear both; }
@keyframes feet { 0% { transform: translateX(-30vw); opacity: 0; } 15%,80% { opacity: 1; } 100% { transform: translateX(30vw); opacity: 0; } }
.fx-hairfire { position:absolute; bottom:-10vh; width: 60vmin; height: 50vh; background: radial-gradient(ellipse at 50% 100%, #fff07a 0%, #ff7a1a 30%, #c0162a88 55%, transparent 72%);
  filter: blur(6px); animation: fire-rise 1.6s ease-out both; }
/* Cuca: fumaça verde, olhos e caldeirão */
.fx-smoke { position:absolute; inset:0; background: radial-gradient(ellipse 50% 40% at 50% 80%, #5dff3a55, transparent 70%), radial-gradient(ellipse 40% 30% at 40% 40%, #2f7d1244, transparent 70%);
  animation: smoke-rise 2.4s ease-out both; }
@keyframes smoke-rise { 0% { transform: translateY(30vh) scale(.6); opacity: 0; } 30% { opacity: 1; } 100% { transform: translateY(-10vh) scale(1.3); opacity: 0; } }
.fx-eyes { position:absolute; top: 14vh; width: min(50vw, 360px); filter: drop-shadow(0 0 18px #ffe14d); animation: eyes 2.4s ease-in-out both; }
@keyframes eyes { 0%,15% { opacity: 0; transform: scaleY(0); } 25%,45% { opacity: 1; transform: scaleY(1); } 50% { transform: scaleY(.1); } 55%,85% { transform: scaleY(1); opacity: 1; } 100% { opacity: 0; } }
.fx-cauldron { position:absolute; bottom: 2vh; width: min(52vw, 380px); animation: cauldron 2.6s ease-out both; }
.fx-cauldron .cb { transform-box: fill-box; animation: bubble 1s ease-out infinite; }
@keyframes cauldron { 0% { transform: translateY(40vh); } 20%,80% { transform: translateY(0); } 100% { transform: translateY(40vh); } }
@keyframes bubble { 0% { transform: translate(0, 0) scale(.6); opacity: 1; } 100% { transform: translate(var(--bx), -60px) scale(1.3); opacity: 0; } }
/* Mula sem Cabeça: parede de labaredas */
.fx-flamewall { position:absolute; left:0; bottom:0; width: 100vw; height: 70vh; animation: fire-rise 2s ease-out both; }
.fx-flamewall .fw { transform-box: fill-box; transform-origin: 50% 100%; animation: flicker .3s ease-in-out infinite alternate; }
@keyframes fire-rise { 0% { transform: translateY(60%); opacity: 0; } 30% { opacity: 1; } 100% { transform: translateY(-5%); opacity: 0; } }
.fx-ember { position:absolute; bottom: 0; width: 9px; height: 9px; border-radius: 50%; background: #ffd23f; box-shadow: 0 0 12px #ff8c1a; animation: ember 1.9s ease-out both; }
@keyframes ember { to { transform: translate(var(--dx), -85vh) scale(.2); opacity: 0; } }
/* cartas voando para quem compra */
.fx-flycard { position:absolute; width: 70px; animation: flycard 1.4s cubic-bezier(.3,.7,.3,1) both; animation-delay: calc(var(--i) * .12s + .2s); }
.fx-flycard svg { width: 100%; height: auto; filter: drop-shadow(0 6px 8px #000); }
.fx-flycard.down { --ty: 46vh; } .fx-flycard.up { --ty: -46vh; }
@keyframes flycard { 0% { transform: translate(0, 0) rotate(0) scale(.6); opacity: 0; } 20% { opacity: 1; } 100% { transform: translate(var(--x), var(--ty)) rotate(540deg) scale(1); opacity: 0; } }
/* Iara: onda da cor escolhida + brilho de escamas */
.fx-waterwave { position:absolute; left:0; bottom:0; width: 200vw; height: 100vh; animation: wave-sweep 2.4s ease-in-out both; }
@keyframes wave-sweep { 0% { transform: translate(-100vw, 70vh); } 40% { transform: translate(-50vw, 10vh); } 100% { transform: translate(0, 100vh); } }
.fx-colorwave { position:absolute; width: 20vmin; height: 20vmin; border-radius: 50%; border: 10px solid var(--c); box-shadow: 0 0 40px var(--c), inset 0 0 40px var(--c); animation: colorwave 1.8s ease-out both; }
@keyframes colorwave { from { transform: scale(.2); opacity: 1; } to { transform: scale(9); opacity: 0; } }
.fx-glint { position:absolute; width: 10px; height: 10px; background: #e9ffff; clip-path: polygon(50% 0, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0 50%, 38% 38%); animation: glint 1.2s ease-in-out both; }
@keyframes glint { 0%,100% { transform: scale(0) rotate(0); opacity: 0; } 50% { transform: scale(2.4) rotate(90deg); opacity: 1; } }
/* UNO / denúncia / desafio */
.fx-shout { position:absolute; width: 30vmin; height: 30vmin; border-radius: 50%; border: 8px solid #ffb02e; animation: shout 1.4s ease-out both; }
.fx-shout.s2 { animation-delay: .2s; border-color: #ff5a1a; } .fx-shout.s3 { animation-delay: .4s; border-color: #fff3cf; }
@keyframes shout { from { transform: scale(.2); opacity: 1; } to { transform: scale(5); opacity: 0; } }
.fx-horn { position:absolute; top: 12vh; color: #fff3cf; filter: drop-shadow(0 0 16px #ff2d55); animation: horn 1.6s ease-in-out both; }
@keyframes horn { 0% { transform: scale(.3) rotate(-30deg); opacity: 0; } 30% { transform: scale(1.1) rotate(10deg); opacity: 1; } 60% { transform: rotate(-8deg); } 100% { transform: scale(1) rotate(0); opacity: 0; } }
.fx-rays { position:absolute; width: 140vmax; height: 140vmax; background: repeating-conic-gradient(#ffd23f40 0 8deg, transparent 8deg 20deg); animation: rays 1.8s ease-out both; }
.fx-rays.gold { animation: rays-long 5s ease-out both; }
@keyframes rays { from { transform: rotate(0) scale(.2); opacity: 1; } to { transform: rotate(60deg) scale(1); opacity: 0; } }
@keyframes rays-long { 0% { transform: rotate(0) scale(.2); opacity: 0; } 15% { opacity: 1; } 85% { opacity: .8; } 100% { transform: rotate(90deg) scale(1.1); opacity: 0; } }
/* vitória e derrota */
.victory-bg { position:absolute; inset:0; background: radial-gradient(circle at 50% 45%, #ffb02e55, #1b0f0499 60%, #000c); animation: scene 5.2s ease both; }
.fx-crown { position:absolute; top: 12vh; width: min(34vw, 220px); filter: drop-shadow(0 0 24px #ffd23f); animation: crown 5s cubic-bezier(.2,1.2,.4,1) both; }
@keyframes crown { 0% { transform: translateY(40vh) scale(.3) rotate(-20deg); opacity: 0; } 25% { transform: translateY(0) scale(1.1) rotate(4deg); opacity: 1; } 35%,85% { transform: scale(1) rotate(0); opacity: 1; } 100% { opacity: 0; } }
.fx-text.epic { animation: epic 5s ease both; }
@keyframes epic { 0% { transform: scale(.2); opacity: 0; letter-spacing: .6em; } 20% { transform: scale(1.12); opacity: 1; letter-spacing: .06em; } 30%,85% { transform: scale(1); opacity: 1; } 100% { opacity: 0; transform: scale(1.1); } }
.defeat-bg { position:absolute; inset:0; background: radial-gradient(circle at 50% 50%, #1a1a2a88, #000e 75%); animation: scene 4.4s ease both; }
.defeat-fog { position:absolute; inset: 30vh -20vw 0; background: radial-gradient(ellipse at 50% 70%, #8a8aa04d, transparent 65%); filter: blur(14px); animation: fog-in 4.4s ease both; }
@keyframes fog-in { 0% { opacity: 0; transform: translateY(10vh); } 30%,80% { opacity: 1; transform: none; } 100% { opacity: 0; } }
.fx-text.grim { color: #d6cfe0; -webkit-text-stroke: 1px #000; animation: grim 4.4s ease both; text-shadow: 0 4px 0 #000, 0 0 30px #4a3a6a; }
@keyframes grim { 0% { opacity: 0; transform: translateY(-30px); filter: blur(6px); } 25%,80% { opacity: 1; transform: none; filter: none; } 100% { opacity: 0; filter: blur(4px); } }
.fx-ash { position:absolute; top: -4vh; width: 4px; height: 4px; border-radius: 50%; background: #9a94a8; opacity: .8; animation: ash var(--t, 4s) linear both; }
@keyframes ash { to { transform: translate(var(--dx), 108vh); opacity: 0; } }
@keyframes scene { 0% { opacity: 0; } 12%,85% { opacity: 1; } 100% { opacity: 0; } }
.confetti { position:absolute; top: -5vh; width: 10px; height: 14px; animation: confetti-fall var(--t, 3s) linear both; animation-delay: var(--d, 0s); }
@keyframes confetti-fall { to { transform: translate(var(--dx), 110vh) rotate(var(--rot)); } }
.fx-banner { position:absolute; top: 14vh; display:flex; align-items:center; gap:.5rem; background: linear-gradient(180deg, #2c2416, #16110a); color: var(--gold2);
  font: 900 clamp(1.05rem, 4vw, 1.5rem) var(--title); letter-spacing: .06em; padding: .55rem 1.6rem; border-radius: 6px; border: 1px solid var(--gold);
  box-shadow: inset 0 0 0 3px #0b0a07, 0 8px 0 #000, 0 0 30px #ff9d2e55; animation: banner 2.2s ease both; }
.fx-banner.turn { color: #fff3cf; box-shadow: inset 0 0 0 3px #0b0a07, 0 8px 0 #000, 0 0 40px #ff9d2e; }
.fx-banner .ico { color: var(--ember); }
@keyframes banner { 0% { transform: translateY(-40vh); } 20%,80% { transform: translateY(0); } 100% { transform: translateY(-40vh); } }

/* ---------- portal (entrar na sala) ---------- */
.portal { background: transparent; }
.portal-veil { position:absolute; inset:0; background: radial-gradient(circle at 50% 50%, #0b0a07aa, #000000e6 70%); animation: scene 3.4s ease both; }
.portal-door { position:absolute; top:0; bottom:0; width: 51vw; animation: door-open 2.4s cubic-bezier(.6,0,.3,1) both;
  background: radial-gradient(ellipse at 100% 50%, #3a4a3f 0%, #121c16 40%, #030705 80%); box-shadow: inset 0 0 80px #000; }
.portal-door.left { left: 0; --out: -100%; }
.portal-door.right { right: 0; --out: 100%; background: radial-gradient(ellipse at 0% 50%, #3a4a3f 0%, #121c16 40%, #030705 80%); }
@keyframes door-open { 0%, 25% { transform: translateX(0); } 100% { transform: translateX(var(--out)); opacity: .2; } }
.portal-ring { position:absolute; width: 30vmin; height: 30vmin; border-radius: 50%; border: 6px solid #ffb02e;
  box-shadow: 0 0 40px #ff7a1a, inset 0 0 40px #ff7a1a, 0 0 120px #ffb02e88; animation: portal-ring 3s ease-out both; }
@keyframes portal-ring { 0% { transform: scale(0) rotate(0); opacity: 0; } 30% { transform: scale(1) rotate(90deg); opacity: 1; } 100% { transform: scale(6) rotate(240deg); opacity: 0; } }
.portal-cards { position:absolute; width: 0; height: 0; }
.portal-card { position:absolute; left: -35px; top: -52px; width: 70px; animation: orbit 2.8s cubic-bezier(.3,.1,.3,1) both; animation-delay: var(--d); }
.portal-card svg { width: 100%; height: auto; filter: drop-shadow(0 8px 10px #000); }
@keyframes orbit {
  0% { transform: rotate(var(--a)) translateY(0) rotate(var(--r)) scale(.2); opacity: 0; }
  25% { opacity: 1; }
  60% { transform: rotate(calc(var(--a) + 200deg)) translateY(-26vmin) rotate(calc(var(--r) + 180deg)) scale(1); opacity: 1; }
  100% { transform: rotate(calc(var(--a) + 360deg)) translateY(-70vmin) rotate(calc(var(--r) + 360deg)) scale(.7); opacity: 0; } }
.portal-title { position: relative; z-index: 3; text-align:center; animation: scene 3.4s ease both; }
.portal-eyebrow { font: 1.1rem var(--hand); color: var(--gold); letter-spacing: .3em; }
.portal-code span { display:inline-block; font: 900 clamp(3rem, 14vw, 7rem) var(--deco); color: #fff3cf; text-shadow: 0 0 30px #ff9d2e, 0 6px 0 #000;
  animation: letter-rise .9s cubic-bezier(.2,1.5,.4,1) both; animation-delay: calc(.6s + var(--i) * .1s); }
@keyframes letter-rise { from { transform: translateY(60px) scale(.3); opacity: 0; filter: blur(8px); } }
.portal-code.long span { font-size: clamp(1.8rem, 7vw, 4rem); }
.portal-sub { font: 700 1.1rem var(--title); color: var(--gold2); letter-spacing: .2em; text-transform: uppercase; }

/* ---------- arauto: alguém entrou / saiu ---------- */
.herald { position: fixed; left: 50%; z-index: 999995; pointer-events: none; text-align:center; transform: translateX(-50%); }
.herald.arrive { top: 9vh; width: min(92vw, 520px); animation: herald 4.4s ease both; }
@keyframes herald { 0% { opacity: 0; } 10%,82% { opacity: 1; } 100% { opacity: 0; } }
.herald-fire { width: 120px; height: 120px; display:block; margin: 0 auto -12px; }
.herald-fire .hf-flame { transform-box: fill-box; transform-origin: 50% 100%; animation: flicker .32s ease-in-out infinite alternate; }
.herald-fire .hf-glow { animation: glow-pulse 1.2s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
.herald-fire .hf-spark { transform-box: fill-box; animation: spark-up 1.4s ease-out infinite; }
@keyframes spark-up { 0% { transform: translate(0,0); opacity: 1; } 100% { transform: translate(var(--sx), -60px); opacity: 0; } }
.herald-smoke { position:absolute; left: 50%; top: -10px; width: 160px; height: 160px; margin-left: -80px; border-radius: 50%;
  background: radial-gradient(circle, #cfd8d03a, transparent 65%); filter: blur(8px); animation: smoke-up 4.4s ease-out both; }
@keyframes smoke-up { from { transform: translateY(60px) scale(.5); opacity: 0; } 40% { opacity: 1; } to { transform: translateY(-80px) scale(1.8); opacity: 0; } }
.herald-text { background: __CORNERS__, linear-gradient(180deg, #1d1810f2, #0b0a07f5); border: 1px solid var(--gold); border-radius: 6px; padding: .7rem 1rem .8rem;
  box-shadow: inset 0 0 0 4px #0b0a07, inset 0 0 0 5px #d9a44144, 0 10px 30px #000, 0 0 40px #ff7a1a55; }
.herald-name { font: 900 clamp(1.5rem, 6vw, 2.4rem) var(--deco); color: #fff3cf; text-shadow: 0 0 18px #ff9d2e, 0 3px 0 #000;
  animation: name-rise 1.4s cubic-bezier(.2,1.4,.4,1) .3s both; overflow-wrap: anywhere; }
@keyframes name-rise { from { transform: translateY(40px) scale(.5); opacity: 0; filter: blur(6px); } }
.herald-sub { font: 1.1rem var(--hand); color: var(--gold); letter-spacing: .14em; }
.herald.depart { bottom: 12vh; width: min(90vw, 420px); animation: herald 3.4s ease both; }
.herald.depart .herald-sub { color: #c9c2d6; font-size: 1.05rem; padding: .5rem 1rem; text-shadow: 0 2px 4px #000; }
.depart-fog { position:absolute; inset: -30px -60px; background: radial-gradient(ellipse, #8a93a066, transparent 65%); filter: blur(10px); animation: fog-in 3.4s ease both; }

/* ---------- celular ---------- */
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: .8rem .55rem 3rem; }
  .logo .eyebrow { font-size: .78rem; letter-spacing: .06em; }
  .st-key-topbar > div:first-child { display: none; }
  h3 { font-size: 1.3rem !important; } h4 { font-size: 1.1rem !important; }
  .st-key-topbar { flex-wrap: wrap; justify-content: flex-end; row-gap: .4rem; }
  .acct span { max-width: 110px; }
  .st-key-topbar > div:first-child { flex: 1 1 auto; }
  .st-key-topbar div.stButton > button { min-height: 2.6rem; padding: 0 .7rem; font-size: .8rem; }
  .st-key-muted label p { font-size: .82rem !important; }
  .logo .tagline { font-size: .9rem; } .logo .tagline::before, .logo .tagline::after { width: 1.2rem; margin: 0 .4rem; }
  .panel, [data-testid="stForm"] { padding: 1rem .9rem !important; }
  .seat { min-width: 0; flex: 1 1 44%; max-width: 49%; padding: .4rem .45rem; }
  .seat .nm { max-width: 92px; font-size: .86rem; }
  .seat .sub { font-size: .7rem; }
  .avatar { width: 32px; height: 32px; }
  .fan { height: 34px; } .fan .mini { width: 22px; height: 33px; margin-left: -12px; }
  .pile, .pile svg, .discard .topc .uno-card { width: 84px !important; height: 126px !important; }
  .direction svg { width: 32px; height: 32px; }
  .center { gap: .9rem 1.4rem; }
  .status { flex: 1 1 100%; order: 3; max-width: none; }
  /* mão: uma faixa com rolagem horizontal (cartas inteiras, sem corte) */
  .st-key-hand { flex-wrap: nowrap !important; overflow-x: auto !important; overflow-y: hidden !important; justify-content: flex-start !important;
    max-height: none; padding: 1.4rem .4rem .9rem; scroll-snap-type: x proximity; -webkit-overflow-scrolling: touch; }
  .st-key-hand > div { scroll-snap-align: start; }
  [class*="st-key-hc_"] { width: 82px !important; flex: 0 0 82px !important; }
  .st-key-hand > [data-testid="stLayoutWrapper"] { width: 82px !important; flex: 0 0 82px !important; }
  .code-tiles span { width: 2.7rem; height: 3.3rem; font-size: 1.8rem; }
  .st-key-table { padding: .6rem .4rem; }
  [data-testid="stTabs"] [role="tablist"] { gap: .25rem; padding: 0; }
  [data-testid="stTabs"] [role="tab"] { padding: .45rem .1rem; min-height: 60px; }
  [data-testid="stTabs"] [role="tab"] p { flex-direction: column; font-size: .74rem; letter-spacing: .04em; gap: .2rem; }
  [data-testid="stTabs"] [role="tab"] p::before { margin-right: 0 !important; width: 1.7em !important; height: 1.7em !important; }
  .beast .art { flex-basis: 80px; }
  /* lobby: botão Trocar/Remover na mesma linha do jogador */
  [class*="st-key-lprow_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .4rem !important; }
  [class*="st-key-lprow_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; min-width: 0 !important; width: auto !important; }
  [class*="st-key-lprow_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; min-width: 0 !important; width: auto !important; }
  [class*="st-key-lprow_"] [data-testid="stHorizontalBlock"] button { min-height: 44px; padding: 0 .7rem; }
  /* seletor de personagem: uma faixa com rolagem horizontal */
  [class*="st-key-avpick_"] [role="radiogroup"] { display: flex !important; flex-wrap: nowrap !important; overflow-x: auto; overflow-y: hidden;
    scroll-snap-type: x proximity; -webkit-overflow-scrolling: touch; padding: .35rem .2rem .45rem; }
  [class*="st-key-avpick_"] [role="radiogroup"] > div { flex: 0 0 62px; scroll-snap-align: start; }
}

/* ---------- menos movimento ---------- */
@media (prefers-reduced-motion: reduce) {
  .ambient *, .uno-card *, .uno-card, .seat, .badge-uno, .direction, .status .big, .st-key-btn_uno button, [class*="st-key-den_"] button,
  .code-tiles span, .log div, .lobby-player, .podium-crown, .av-svg *, [class*="st-key-avpick_"] label::before, .herald *, .discard .ring { animation: none !important; transition: none !important; }
  .fx-layer > :not(.fx-text):not(.fx-banner):not(.portal-title):not(.duel-text):not(.duel-bg) { display: none !important; }
  .fx-layer .fx-text, .fx-banner, .portal-title, .portal-code span, .herald { animation-duration: .01ms !important; animation-delay: 0s !important; }
  .fx-layer .fx-text, .fx-banner, .portal-title, .portal-code span, .herald, .herald-name { animation: none !important; }
}
</style>
"""

CSS = (CSS.replace("__CORNERS__", CORNERS).replace("__FOREST__", _forest_svg())
       .replace("__ICONS__", icon_mask_css()).replace("__AVATARS__", avatar_picker_css())
       .replace("</style>", DUEL_CSS + "</style>", 1))
