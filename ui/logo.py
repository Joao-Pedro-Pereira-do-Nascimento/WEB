"""Logotipo animado "UNO FOLCLÓUNO" em SVG original (desenhado em código).

As letras são traçadas à mão (polígonos/arcos) e algumas viram criaturas:

- linha 1: o **O** de "UNO" é o olho em chamas do **Boitatá** (pisca de vez em
  quando), e o corpo de fogo da cobra serpenteia por baixo da linha 2;
- **O** (2ª letra): anel de água da **Iara**, com ondas por dentro e a cauda de peixe;
- **L** (3ª letra): a perna única do **Saci**, com o gorro vermelho balançando e o cachimbo;
- **C**: a bocarra de jacaré da **Cuca**, com dentes e olho brilhando;
- **L** (5ª letra): o **Curupira**, cabelo de fogo tremulando; suas pegadas
  ao contrário andam ao lado de "UNO";
- **Ó**: o acento é a labareda da **Mula sem Cabeça**, e o **U** seguinte é a
  ferradura dela soltando faíscas;
- o último **O** é a lua cheia.

Todas as animações são CSS (respeitam ``prefers-reduced-motion``) e um
``<animate>`` SMIL que faz a cobra ondular. O SVG escala pela largura (celular ok).
"""

from __future__ import annotations

import math
from functools import lru_cache

W, T = 92, 24          # largura da letra e espessura do traço (linha 2)
TOP, H = 188, 110      # topo e altura das letras da linha 2
OUT = 'stroke="#140b04" stroke-width="5" stroke-linejoin="round" paint-order="stroke"'


def _cell(i: int) -> int:
    return 34 + i * 104


# --------------------------------------------------------------------------- glifos

def _u(x, y, w=W, h=H, t=T):
    r_in, r_out = (w - 2 * t) / 2, w / 2
    v = h - r_out
    return (f"M{x} {y} h{t} v{v} a{r_in} {r_in} 0 0 0 {w - 2 * t} 0 v{-v} h{t} v{v} "
            f"a{r_out} {r_out} 0 0 1 {-w} 0 Z")


def _n(x, y, w=W, h=H, t=T):
    return (f"M{x} {y + h} V{y} h{t} L{x + w - t} {y + h - 40} V{y} h{t} V{y + h} h{-t} "
            f"L{x + t} {y + 40} V{y + h} Z")


def _f(x, y, w=W, h=H, t=T):
    return (f"M{x} {y} H{x + w} v{t} H{x + t} v{20} H{x + w - 16} v{t} H{x + t} V{y + h} H{x} Z")


def _l(x, y, w=W, h=H, t=T):
    return f"M{x} {y} h{t} V{y + h - t} H{x + w} V{y + h} H{x} Z"


def _ring(cx, cy, rx, ry, t=T):
    def ell(a, b):
        return f"M{cx - a} {cy} a{a} {b} 0 1 0 {2 * a} 0 a{a} {b} 0 1 0 {-2 * a} 0 Z"
    return ell(rx, ry) + " " + ell(rx - t, ry - t)


def _c(cx, cy, rx, ry, t=T, gap=40):
    a = math.radians(gap)
    ox, oy = rx * math.cos(a), ry * math.sin(a)
    ix, iy = (rx - t) * math.cos(a), (ry - t) * math.sin(a)
    return (f"M{cx + ox:.1f} {cy - oy:.1f} A{rx} {ry} 0 1 0 {cx + ox:.1f} {cy + oy:.1f} "
            f"L{cx + ix:.1f} {cy + iy:.1f} A{rx - t} {ry - t} 0 1 1 {cx + ix:.1f} {cy - iy:.1f} Z")


# --------------------------------------------------------------------------- peças

def _flame(x, y, s=1.0, fill="url(#lg-fire)", cls="lg-flick", delay=0.0):
    """Labareda com a base em (x, y)."""
    return (f'<path class="{cls}" style="animation-delay:{delay:.2f}s" fill="{fill}" '
            f'd="M{x} {y} c{-9 * s} {-4 * s} {-11 * s} {-14 * s} {-6 * s} {-24 * s} c{1 * s} {6 * s} {4 * s} {8 * s} {6 * s} {8 * s} '
            f'c{-2 * s} {-10 * s} {2 * s} {-18 * s} {8 * s} {-22 * s} c{-1 * s} {8 * s} {3 * s} {12 * s} {6 * s} {18 * s} '
            f'c{4 * s} {8 * s} {1 * s} {16 * s} {-8 * s} {20 * s} Z"/>')


def _snake_path(phase: float) -> str:
    """Corpo do Boitatá: desce do olho e serpenteia sob a linha 2 até a cauda."""
    pts = [(668, 112), (735, 150), (790, 214)]
    d = f"M{pts[0][0]} {pts[0][1]} Q{pts[1][0]} {pts[1][1]} {pts[2][0]} {pts[2][1]} "
    d += f"Q 840 290 {905} {306} "
    x = 905
    k = 0
    while x > 60:
        nx = x - 70
        amp = 16 if k % 2 == 0 else -16
        amp = amp * math.cos(phase) if k % 2 == 0 else amp * math.cos(phase + 1.2)
        d += f"Q {x - 35} {312 + amp:.1f} {nx} {306} "
        x = nx
        k += 1
    d += "Q 40 300 26 288"
    return d


def _footprint(x, y, rot, delay):
    toes = "".join(f'<circle cx="{-11:.1f}" cy="{(i - 2) * 2.6:.1f}" r="1.5"/>' for i in range(5))
    # pés virados: a trilha anda para a direita, mas os dedos apontam para a esquerda
    return (f'<g transform="translate({x} {y}) rotate({rot}) scale(1.5)"><g class="lg-step" style="animation-delay:{delay:.1f}s">'
            f'<ellipse cx="0" cy="0" rx="8" ry="4.6"/>{toes}</g></g>')


@lru_cache(maxsize=1)
def logo_svg() -> str:
    x = [_cell(i) for i in range(9)]
    gold = f'fill="url(#lg-gold)" {OUT}'

    # ---------------- linha 1: U N + olho do Boitatá
    s1 = 1.15
    l1 = (f'<g transform="translate(316 12) scale({s1})"><path d="{_u(0, 0)}" {gold}/></g>'
          f'<g transform="translate(441 12) scale({s1})"><path d="{_n(0, 0)}" {gold}/></g>')
    ecx, ecy, erx, ery = 626, 75, 56, 63
    tongues = "".join(
        _flame(ecx + (erx + 2) * math.cos(math.radians(a)), ecy + (ery + 2) * math.sin(math.radians(a)) + 6,
               .62, delay=i * .13) for i, a in enumerate(range(200, 345, 24)))
    eye = f"""
<g class="lg-eye">
 <ellipse cx="{ecx}" cy="{ecy}" rx="{erx + 22}" ry="{ery + 20}" fill="url(#lg-halo)" class="lg-glow"/>
 {tongues}
 <path d="{_ring(ecx, ecy, erx, ery, 22)}" fill="url(#lg-fire)" fill-rule="evenodd" {OUT}/>
 <ellipse cx="{ecx}" cy="{ecy}" rx="{erx - 22}" ry="{ery - 22}" fill="url(#lg-iris)"/>
 <ellipse class="lg-pupil" cx="{ecx}" cy="{ecy}" rx="6" ry="{ery - 27}" fill="#120400"/>
 <circle cx="{ecx - 11}" cy="{ecy - 15}" r="5" fill="#fffbe0" opacity=".9"/>
 <ellipse class="lg-lid" cx="{ecx}" cy="{ecy}" rx="{erx - 21}" ry="{ery - 21}" fill="#2a0c02"/>
</g>"""

    # ---------------- cobra (atrás da linha 2)
    p0, p1, p2 = _snake_path(0), _snake_path(2.1), _snake_path(4.2)
    snake = f"""
<g class="lg-snake">
 <path d="{p0}" fill="none" stroke="#3a0800" stroke-width="22" stroke-linecap="round">
  <animate attributeName="d" dur="3.2s" repeatCount="indefinite" values="{p0};{p1};{p2};{p0}"/></path>
 <path d="{p0}" fill="none" stroke="url(#lg-fire-h)" stroke-width="15" stroke-linecap="round">
  <animate attributeName="d" dur="3.2s" repeatCount="indefinite" values="{p0};{p1};{p2};{p0}"/></path>
 <path class="lg-scales" d="{p0}" fill="none" stroke="#fff1a8" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="4 11">
  <animate attributeName="d" dur="3.2s" repeatCount="indefinite" values="{p0};{p1};{p2};{p0}"/></path>
 <path d="M26 288 l-12 -10 l4 12 Z" fill="#ff7a1a"/>
</g>"""

    # ---------------- linha 2
    # F
    f_ = f'<path d="{_f(x[0], TOP)}" {gold}/>'
    # O — Iara
    icx, icy = x[1] + 47, TOP + H / 2
    waves = "".join(
        f'<path d="M{icx - 60} {icy - 12 + k * 13} q8 -6 16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0" '
        f'fill="none" stroke="#bff6ff" stroke-width="2.4" opacity="{.85 - k * .2:.2f}"/>' for k in range(4))
    iara = f"""
<g class="lg-iara">
 <clipPath id="lg-iara-in"><ellipse cx="{icx}" cy="{icy}" rx="{47 - T}" ry="{55 - T}"/></clipPath>
 <ellipse cx="{icx}" cy="{icy}" rx="{47 - T}" ry="{55 - T}" fill="#06243d"/>
 <g clip-path="url(#lg-iara-in)"><g class="lg-wave">{waves}</g></g>
 <path d="{_ring(icx, icy, 47, 55)}" fill="url(#lg-water)" fill-rule="evenodd" {OUT}/>
 <g transform="translate({icx - 34} {icy - 40}) rotate(205) scale(1.25)"><g class="lg-tail">
  <path d="M0 0 q10 -4 16 -16 q2 10 -4 18 q12 -2 20 8 q-12 2 -20 -2 q2 8 -6 14 q0 -10 -6 -14 Z" fill="url(#lg-scale)" stroke="#06243d" stroke-width="2.2"/>
 </g></g>
 <circle class="lg-twinkle" cx="{icx - 30}" cy="{icy - 40}" r="2.6" fill="#e9ffff"/>
 <circle class="lg-twinkle" style="animation-delay:.7s" cx="{icx + 38}" cy="{icy - 10}" r="2" fill="#e9ffff"/>
 <circle class="lg-twinkle" style="animation-delay:1.3s" cx="{icx - 40}" cy="{icy + 26}" r="2.2" fill="#e9ffff"/>
</g>"""
    # L — Saci
    sx = x[2] + T / 2
    saci = f"""
<g class="lg-saci">
 <path d="{_l(x[2], TOP)}" {gold}/>
 <rect x="{x[2] - 2}" y="{TOP + 2}" width="{T + 4}" height="20" rx="3" fill="#b3121f" stroke="#140b04" stroke-width="3"/>
 <circle cx="{sx}" cy="{TOP - 14}" r="15" fill="#5a321d" stroke="#140b04" stroke-width="3"/>
 <circle cx="{sx - 5}" cy="{TOP - 16}" r="3.4" fill="#fff"/><circle cx="{sx + 6}" cy="{TOP - 16}" r="3.4" fill="#fff"/>
 <circle cx="{sx - 4}" cy="{TOP - 16}" r="1.6" fill="#140b04"/><circle cx="{sx + 7}" cy="{TOP - 16}" r="1.6" fill="#140b04"/>
 <path d="M{sx - 6} {TOP - 8} q6 5 12 0" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round"/>
 <g class="lg-cap"><path d="M{sx - 15} {TOP - 22} C{sx - 14} {TOP - 42} {sx + 6} {TOP - 50} {sx + 30} {TOP - 58} C{sx + 22} {TOP - 44} {sx + 18} {TOP - 34} {sx + 16} {TOP - 24} Q{sx} {TOP - 30} {sx - 15} {TOP - 22} Z" fill="#e01e37" stroke="#140b04" stroke-width="3"/>
  <circle cx="{sx + 30}" cy="{TOP - 58}" r="4.4" fill="#ff7088" stroke="#140b04" stroke-width="2"/></g>
 <path d="M{sx + 8} {TOP - 9} h16" stroke="#6b4423" stroke-width="3.4" stroke-linecap="round"/>
 <rect x="{sx + 21}" y="{TOP - 18}" width="8" height="10" rx="2" fill="#8b5a2b" stroke="#140b04" stroke-width="2"/>
 <circle class="lg-smoke" cx="{sx + 26}" cy="{TOP - 26}" r="4" fill="#d8d0c0"/>
 <circle class="lg-smoke" style="animation-delay:1s" cx="{sx + 26}" cy="{TOP - 26}" r="3" fill="#d8d0c0"/>
</g>"""
    # C — Cuca (bocarra de jacaré)
    ccx, ccy = x[3] + 48, TOP + H / 2
    a = math.radians(40)
    tip_top = (ccx + 48 * math.cos(a), ccy - 55 * math.sin(a))
    tip_bot = (ccx + 48 * math.cos(a), ccy + 55 * math.sin(a))
    teeth_top = "".join(f'<path d="M{tip_top[0] - 6 - k * 9:.1f} {tip_top[1] + 14 + k * 2:.1f} l4 9 l4 -9 Z" fill="#fffbe8" stroke="#140b04" stroke-width="1.4"/>' for k in range(3))
    teeth_bot = "".join(f'<path d="M{tip_bot[0] - 6 - k * 9:.1f} {tip_bot[1] - 14 - k * 2:.1f} l4 -9 l4 9 Z" fill="#fffbe8" stroke="#140b04" stroke-width="1.4"/>' for k in range(3))
    cuca = f"""
<g class="lg-cuca">
 {teeth_top}{teeth_bot}
 <path d="{_c(ccx, ccy, 48, 55)}" fill="url(#lg-green)" {OUT}/>
 {"".join(f'<circle cx="{ccx - 30 + k * 13}" cy="{ccy - 42 + abs(k - 2) * 5}" r="3" fill="#1d5e22"/>' for k in range(4))}
 <circle cx="{tip_top[0] - 3:.1f}" cy="{tip_top[1] + 5:.1f}" r="2.2" fill="#0c3010"/>
 <ellipse cx="{ccx - 4}" cy="{TOP - 4}" rx="14" ry="11" fill="url(#lg-green)" stroke="#140b04" stroke-width="3"/>
 <circle class="lg-cuca-eye" cx="{ccx - 4}" cy="{TOP - 5}" r="7" fill="#ffe14d"/>
 <ellipse class="lg-pupil" cx="{ccx - 4}" cy="{TOP - 5}" rx="1.8" ry="5.6" fill="#140b04"/>
</g>"""
    # L — Curupira
    kx = x[4] + T / 2
    hair = "".join(_flame(kx + dx, TOP - 22 + dy, sc, delay=d) for dx, dy, sc, d in
                   [(-12, 4, .8, 0), (-3, -2, 1.05, .15), (8, 0, .9, .3), (15, 6, .7, .45)])
    curupira = f"""
<g class="lg-curupira">
 <path d="{_l(x[4], TOP)}" {gold}/>
 <path d="M{x[4] - 2} {TOP + 4} h{T + 4} l-3 18 l-4 -6 l-5 7 l-4 -7 l-5 7 l-3 -7 Z" fill="#2d8f3c" stroke="#140b04" stroke-width="2.6"/>
 {hair}
 <circle cx="{kx}" cy="{TOP - 12}" r="13" fill="#c07a3f" stroke="#140b04" stroke-width="3"/>
 <circle cx="{kx - 4}" cy="{TOP - 13}" r="2.6" fill="#fff"/><circle cx="{kx + 6}" cy="{TOP - 13}" r="2.6" fill="#fff"/>
 <circle cx="{kx - 3}" cy="{TOP - 13}" r="1.3" fill="#140b04"/><circle cx="{kx + 7}" cy="{TOP - 13}" r="1.3" fill="#140b04"/>
 <path d="M{kx - 4} {TOP - 6} q5 3 10 0" stroke="#5d2a12" stroke-width="2" fill="none"/>
</g>"""
    # Ó — acento de fogo (Mula sem Cabeça)
    ocx, ocy = x[5] + 46, TOP + H / 2
    mula_o = f"""
<g class="lg-mula">
 <path d="{_ring(ocx, ocy, 46, 55)}" fill="url(#lg-gold)" fill-rule="evenodd" {OUT}/>
 <ellipse cx="{ocx + 12}" cy="{TOP - 16}" rx="18" ry="16" fill="url(#lg-halo)" class="lg-glow"/>
 <g transform="rotate(28 {ocx + 10} {TOP - 2})">{_flame(ocx + 10, TOP - 2, 1.6, delay=0)}{_flame(ocx + 11, TOP - 4, .9, fill="#fff1a8", delay=.2)}</g>
 <circle class="lg-ember" cx="{ocx + 20}" cy="{TOP - 30}" r="2.2" fill="#ffd23f"/>
 <circle class="lg-ember" style="animation-delay:.8s" cx="{ocx + 2}" cy="{TOP - 26}" r="1.8" fill="#ffb02e"/>
</g>"""
    # U — ferradura
    holes = "".join(f'<rect x="{x[6] + 9}" y="{TOP + 12 + k * 20}" width="6" height="9" rx="1.5" fill="#1b1b1b"/>'
                    f'<rect x="{x[6] + W - 15}" y="{TOP + 12 + k * 20}" width="6" height="9" rx="1.5" fill="#1b1b1b"/>'
                    for k in range(3))
    sparks = "".join(f'<circle class="lg-spark" style="animation-delay:{d:.1f}s;--sx:{sx_}px" cx="{x[6] + 46 + o}" cy="{TOP + H + 2}" r="2.2" fill="#ffd23f"/>'
                     for o, d, sx_ in [(-20, 0, -14), (-6, .5, -4), (8, 1, 6), (20, 1.5, 16)])
    horseshoe = f"""
<g class="lg-horseshoe">
 <path d="{_u(x[6], TOP)}" fill="url(#lg-iron)" {OUT}/>
 {holes}{sparks}
</g>"""
    n2 = f'<path d="{_n(x[7], TOP)}" {gold}/>'
    mcx, mcy = x[8] + 46, TOP + H / 2
    moon = f"""
<g class="lg-moon">
 <ellipse cx="{mcx}" cy="{mcy}" rx="64" ry="72" fill="url(#lg-moonhalo)" class="lg-glow"/>
 <path d="{_ring(mcx, mcy, 46, 55)}" fill="url(#lg-moon)" fill-rule="evenodd" {OUT}/>
 <circle cx="{mcx - 30}" cy="{mcy - 22}" r="4" fill="#cdbb83"/><circle cx="{mcx + 32}" cy="{mcy + 18}" r="5" fill="#cdbb83"/>
 <circle cx="{mcx + 10}" cy="{mcy - 44}" r="3" fill="#cdbb83"/>
</g>"""

    steps = "".join(_footprint(752 + i * 50, 104 - (i % 2) * 18 - i * 8, -8 if i % 2 else 8, i * .45)
                    for i in range(5))
    fireflies = "".join(
        f'<circle class="lg-firefly" style="animation-delay:{d:.1f}s" cx="{cx}" cy="{cy}" r="{r}" fill="#e8ff8a"/>'
        for cx, cy, r, d in [(90, 60, 3, 0), (160, 110, 2.4, .8), (230, 40, 2, 1.6), (60, 140, 2.2, 2.2),
                             (270, 120, 2.6, 1.1), (960, 160, 2.2, 1.9), (880, 30, 2, .4)])

    return f"""<svg class="logo-svg" viewBox="0 0 1000 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="lg-title">
<title id="lg-title">UNO FOLCLÓUNO</title>
<defs>
 <linearGradient id="lg-gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff3bf"/><stop offset=".35" stop-color="#e9c46a"/><stop offset=".72" stop-color="#b07d26"/><stop offset="1" stop-color="#6a4410"/></linearGradient>
 <linearGradient id="lg-fire" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#9e1400"/><stop offset=".5" stop-color="#ff7a1a"/><stop offset="1" stop-color="#ffe680"/></linearGradient>
 <linearGradient id="lg-fire-h" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffd23f"/><stop offset=".5" stop-color="#ff5a1a"/><stop offset="1" stop-color="#ff9d2e"/></linearGradient>
 <linearGradient id="lg-water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b9f6ff"/><stop offset=".45" stop-color="#2f9be8"/><stop offset="1" stop-color="#0b3a7a"/></linearGradient>
 <linearGradient id="lg-scale" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5ff2d6"/><stop offset="1" stop-color="#0f8a7a"/></linearGradient>
 <linearGradient id="lg-green" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a6ec7e"/><stop offset=".5" stop-color="#3f9a3a"/><stop offset="1" stop-color="#174d1b"/></linearGradient>
 <linearGradient id="lg-iron" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f2f2f2"/><stop offset=".45" stop-color="#9c9c9c"/><stop offset="1" stop-color="#3c3c3c"/></linearGradient>
 <linearGradient id="lg-moon" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffbe6"/><stop offset="1" stop-color="#d9c58a"/></linearGradient>
 <radialGradient id="lg-iris"><stop offset="0" stop-color="#fff3a0"/><stop offset=".55" stop-color="#ffb02e"/><stop offset="1" stop-color="#c2410c"/></radialGradient>
 <radialGradient id="lg-halo"><stop offset="0" stop-color="#ffb02e" stop-opacity=".55"/><stop offset="1" stop-color="#ff5a1a" stop-opacity="0"/></radialGradient>
 <radialGradient id="lg-moonhalo"><stop offset=".55" stop-color="#fff6c8" stop-opacity=".35"/><stop offset="1" stop-color="#fff6c8" stop-opacity="0"/></radialGradient>
 <filter id="lg-shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="5" stdDeviation="3" flood-color="#000" flood-opacity=".75"/></filter>
</defs>
<style>
.logo-svg .lg-flick{{transform-box:fill-box;transform-origin:50% 100%;animation:lg-flick .5s ease-in-out infinite alternate}}
.logo-svg .lg-glow{{animation:lg-glow 2.4s ease-in-out infinite}}
.logo-svg .lg-lid{{transform-box:fill-box;transform-origin:50% 0;transform:scaleY(0);animation:lg-blink 5s infinite}}
.logo-svg .lg-pupil{{transform-box:fill-box;transform-origin:center;animation:lg-pupil 4s ease-in-out infinite}}
.logo-svg .lg-cap{{transform-box:fill-box;transform-origin:10% 90%;animation:lg-sway 1.8s ease-in-out infinite}}
.logo-svg .lg-smoke{{animation:lg-smoke 2s ease-out infinite;transform-box:fill-box;transform-origin:center}}
.logo-svg .lg-wave{{animation:lg-wave 2.4s linear infinite}}
.logo-svg .lg-tail{{animation:lg-tail 1.6s ease-in-out infinite}}
.logo-svg .lg-twinkle,.logo-svg .lg-firefly{{animation:lg-twinkle 1.8s ease-in-out infinite}}
.logo-svg .lg-firefly{{animation-duration:3.2s}}
.logo-svg .lg-cuca-eye{{animation:lg-eye 1.6s ease-in-out infinite}}
.logo-svg .lg-ember{{animation:lg-ember 1.8s ease-out infinite;transform-box:fill-box}}
.logo-svg .lg-spark{{animation:lg-spark 2s ease-out infinite;transform-box:fill-box}}
.logo-svg .lg-step{{fill:#f0cf7a;opacity:0;animation:lg-step 3.6s ease-in-out infinite}}
.logo-svg .lg-scales{{animation:lg-dash 1.2s linear infinite}}
@keyframes lg-flick{{from{{transform:scaleY(.86) skewX(-4deg)}}to{{transform:scaleY(1.1) skewX(4deg)}}}}
@keyframes lg-glow{{50%{{opacity:.45}}}}
@keyframes lg-blink{{0%,90%,100%{{transform:scaleY(0)}}94%{{transform:scaleY(1)}}}}
@keyframes lg-pupil{{0%,100%{{transform:translateX(0) scaleX(1)}}30%{{transform:translateX(-5px) scaleX(.8)}}65%{{transform:translateX(5px) scaleX(1.25)}}}}
@keyframes lg-sway{{0%,100%{{transform:rotate(-7deg)}}50%{{transform:rotate(8deg)}}}}
@keyframes lg-smoke{{0%{{transform:translate(0,0) scale(.5);opacity:.8}}100%{{transform:translate(8px,-26px) scale(1.6);opacity:0}}}}
@keyframes lg-wave{{to{{transform:translateX(32px)}}}}
@keyframes lg-tail{{50%{{transform:translate(2px,-3px)}}}}
@keyframes lg-twinkle{{50%{{opacity:.15}}}}
@keyframes lg-eye{{50%{{fill:#ff7a1a;filter:drop-shadow(0 0 6px #ffe14d)}}}}
@keyframes lg-ember{{0%{{transform:translate(0,0);opacity:1}}100%{{transform:translate(10px,-34px);opacity:0}}}}
@keyframes lg-spark{{0%{{transform:translate(0,0);opacity:1}}100%{{transform:translate(var(--sx),-30px);opacity:0}}}}
@keyframes lg-step{{0%,8%{{opacity:0}}18%,60%{{opacity:.85}}80%,100%{{opacity:0}}}}
@keyframes lg-dash{{to{{stroke-dashoffset:-30}}}}
@media (prefers-reduced-motion: reduce){{.logo-svg *{{animation:none !important}}.logo-svg .lg-step{{opacity:.6}}.logo-svg .lg-lid{{transform:scaleY(0)}}}}
</style>
{fireflies}
<g class="lg-steps">{steps}</g>
{snake}
<g filter="url(#lg-shadow)">
{l1}
{f_}{iara}{saci}{cuca}{curupira}{mula_o}{horseshoe}{n2}{moon}
</g>
{eye}
</svg>"""


def logo_html() -> str:
    return f'<div class="logo"><h1 class="sr-only">UNO FOLCLÓUNO</h1>{logo_svg()}</div>'
