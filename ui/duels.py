"""Duelo de biomas: animação curta quando uma carta cai sobre o descarte.

Puramente visual (lê os eventos da partida, nunca altera o estado). O bioma de
antes vem do último evento que definiu a cor da mesa (``play``, ``color`` ou
``flip``) anterior à jogada; o de depois é a cor da carta jogada (ou a cor
escolhida no coringa).

Ciclo de vantagem: Rios apagam Fogo, Fogo queima Mata, Mata vence Cerrado,
Cerrado seca Rios. Os pares inversos mostram o mais fraco resistindo; o mesmo
bioma mostra uma aura de reforço; coringas fazem a cor escolhida invadir a tela.
"""

from __future__ import annotations

import html as _html
import random

from game.cards import BIOMES

COLORS = ["red", "green", "blue", "yellow"]
# quem vence quem (chave vence valor)
BEATS = {"blue": "red", "red": "green", "green": "yellow", "yellow": "blue"}

DUEL_SECONDS = 1.9

# (anterior, nova) -> (id da animação, texto curto, peças)
DUELS: dict[tuple[str, str], tuple[str, str, tuple[str, ...]]] = {
    # vantagem
    ("red", "blue"): ("douse", "Rios apagam o Fogo", ("flames_die", "wave_up", "steam", "embers_out")),
    ("green", "red"): ("burn", "Fogo queima a Mata", ("leaves_burn", "flames_up", "sparks", "smoke", "ash")),
    ("yellow", "green"): ("sprout", "Mata vence o Cerrado", ("grass", "vines", "flowers", "leaves_rise")),
    ("blue", "yellow"): ("dry", "Cerrado seca os Rios", ("wave_drain", "sun", "cracks", "dust")),
    # o mais fraco resiste
    ("blue", "red"): ("boil", "Fogo ferve os Rios", ("wave_low", "whirl", "bubbles_boil", "flames_ring")),
    ("red", "green"): ("smother", "Mata abafa o Fogo", ("flames_die", "leaves_wet", "drops")),
    ("green", "yellow"): ("wither", "Cerrado seca a Mata", ("sun_low", "leaves_gold", "dust", "grass")),
    ("yellow", "blue"): ("rain", "Rios molham o Cerrado", ("cracks_fade", "rain", "wave_up_low")),
    # mesmo bioma: reforço
    ("red", "red"): ("aura_fire", "Fogo mais forte", ("pillar", "sparks", "embers")),
    ("green", "green"): ("aura_forest", "Mata mais forte", ("leaf_spiral", "fireflies", "leaves_rise")),
    ("blue", "blue"): ("aura_water", "Rios mais fortes", ("water_ring", "bubbles")),
    ("yellow", "yellow"): ("aura_sun", "Cerrado mais forte", ("sun", "ribbons", "dust")),
}
# os outros pares (Fogo x Cerrado, Mata x Rios) não estão no ciclo: encontro neutro, um para cada sentido
DUELS.update({
    ("red", "yellow"): ("heat", "Cerrado ferve no calor", ("flames_low", "sun", "dust", "embers")),
    ("yellow", "red"): ("wildfire", "Fogo corre pelo Cerrado", ("grass", "flames_run", "sparks", "smoke")),
    ("green", "blue"): ("flood", "Rios cobrem a Mata", ("leaves_float", "wave_up", "bubbles")),
    ("blue", "green"): ("roots", "Mata bebe dos Rios", ("wave_drain", "vines", "leaves_rise")),
})

SOUND = {"red": "b_red", "green": "b_green", "blue": "b_blue", "yellow": "b_yellow"}


def previous_color(events: list[dict], seq: int) -> str | None:
    """Cor da mesa logo antes do evento ``seq`` (procura nos eventos anteriores)."""
    for ev in reversed(events):
        if ev.get("seq", 0) >= seq:
            continue
        t = ev.get("type")
        if t in ("play", "color") and ev.get("color") in COLORS:
            return ev["color"]
        if t == "flip":
            c = (ev.get("card") or {}).get("color")
            return c if c in COLORS else None
        if t == "deal":
            return None
    return None


def duel_for(events: list[dict], play_ev: dict) -> dict | None:
    """Descrição do duelo para um evento ``play`` (ou None se não der para saber o bioma anterior)."""
    if not play_ev or play_ev.get("type") != "play":
        return None
    new = play_ev.get("color")
    old = previous_color(events, play_ev["seq"])
    if new not in COLORS or old not in COLORS:
        return None
    wild = (play_ev.get("card") or {}).get("kind") in ("wild", "wild4")
    kind, text, parts = DUELS[(old, new)]
    if wild:
        kind, parts = "invade", ("invade",) + parts[:2]
        text = f"{BIOMES[new]['name']} {'tomam' if new == 'blue' else 'toma'} a mesa"
    return {"from": old, "to": new, "kind": kind, "text": text, "parts": parts, "seq": play_ev["seq"],
            "sound": SOUND[new], "wild": wild}


# =========================================================================== peças

def _p(cls: str, n: int, rng: random.Random, x=(0, 100), y=(0, 100), dx=(-6, 6), dy=(-30, -10),
       delay=(0, .6), size=(.7, 1.3)) -> str:
    """Partículas (``<i>``) posicionadas em vw/vh, com deslocamento e atraso próprios."""
    return "".join(
        f'<i class="dp {cls}" style="left:{rng.uniform(*x):.1f}vw;top:{rng.uniform(*y):.1f}vh;'
        f'--dx:{rng.uniform(*dx):.1f}vw;--dy:{rng.uniform(*dy):.1f}vh;--d:{rng.uniform(*delay):.2f}s;'
        f'--s:{rng.uniform(*size):.2f};--r:{rng.uniform(-200, 200):.0f}deg"></i>' for _ in range(n))


def _flames(cls: str, rng: random.Random, n: int = 11) -> str:
    tongues = "".join(
        f'<path style="--d:{rng.uniform(0, .25):.2f}s" d="M{x} 300 c-30 -30 -34 -90 -6 -150 c6 30 18 40 26 42 '
        f'c-6 -50 10 -100 40 -126 c-6 46 14 74 28 104 c18 40 8 100 -40 130 Z" '
        f'transform="translate(0 {rng.uniform(0, 40):.0f})"/>' for x in range(-40, 1100, 1100 // n))
    return (f'<svg class="dz {cls}" viewBox="0 0 1000 300" preserveAspectRatio="none" aria-hidden="true">'
            f'<g fill="#ff6a1a" opacity=".85">{tongues}</g>'
            f'<g fill="#ffd23f" opacity=".7" transform="translate(30 90) scale(.94 .7)">{tongues}</g></svg>')


def _wave(cls: str, color: str = "#1f7be0") -> str:
    return (f'<svg class="dz {cls}" viewBox="0 0 1200 600" preserveAspectRatio="none" aria-hidden="true">'
            f'<path d="M0 120 Q150 40 300 120 T600 120 T900 120 T1200 120 V600 H0 Z" fill="{color}" opacity=".7"/>'
            f'<path d="M0 170 Q150 100 300 170 T600 170 T900 170 T1200 170 V600 H0 Z" fill="#0b47a8" opacity=".75"/>'
            f'<path d="M0 120 Q150 40 300 120 T600 120 T900 120 T1200 120" fill="none" stroke="#dff5ff" stroke-width="7"/></svg>')


def _vines(rng: random.Random) -> str:
    paths = []
    for i in range(7):
        x = 60 + i * 150 + rng.uniform(-30, 30)
        h = rng.uniform(220, 380)
        bend = rng.choice([-1, 1]) * rng.uniform(40, 90)
        paths.append(f'<path style="--d:{i * .05:.2f}s" d="M{x:.0f} 420 C{x + bend:.0f} {420 - h * .35:.0f} '
                     f'{x - bend:.0f} {420 - h * .7:.0f} {x + bend * .4:.0f} {420 - h:.0f}"/>')
        for k in range(3):
            ly = 420 - h * (.3 + k * .22)
            paths.append(f'<ellipse class="vl" style="--d:{.35 + i * .05 + k * .1:.2f}s" cx="{x + (bend if k % 2 else -bend) * .5:.0f}" '
                         f'cy="{ly:.0f}" rx="16" ry="7" transform="rotate({rng.choice([-35, 35])} {x:.0f} {ly:.0f})"/>')
    return (f'<svg class="dz vines" viewBox="0 0 1100 420" preserveAspectRatio="none" aria-hidden="true">'
            f'<g fill="none" stroke="#2e7d32" stroke-width="12" stroke-linecap="round">{"".join(p for p in paths if p.startswith("<path"))}</g>'
            f'<g fill="#63e08f" stroke="#0f6e3c" stroke-width="2">{"".join(p for p in paths if p.startswith("<ellipse"))}</g></svg>')


def _cracks(cls: str, rng: random.Random) -> str:
    out = []
    for i in range(8):
        x, y = rng.uniform(40, 1160), rng.uniform(40, 160)
        d = f"M{x:.0f} {y:.0f}"
        for _ in range(4):
            x += rng.uniform(-60, 60)
            y += rng.uniform(-30, 30)
            d += f" L{x:.0f} {y:.0f}"
        out.append(f'<path style="--d:{i * .06:.2f}s" d="{d}"/>')
    return (f'<svg class="dz {cls}" viewBox="0 0 1200 200" preserveAspectRatio="none" aria-hidden="true">'
            f'<rect width="1200" height="200" fill="#8a5a1a" opacity=".55"/>'
            f'<g fill="none" stroke="#2a1804" stroke-width="5" stroke-linecap="round">{"".join(out)}</g></svg>')


def _grass() -> str:
    blades = "".join(f'<path d="M{x} 120 q{(x % 7) - 3} -50 {((x * 7) % 13) - 6} -{60 + (x * 13) % 50}"/>' for x in range(0, 1200, 9))
    return (f'<svg class="dz grass" viewBox="0 0 1200 120" preserveAspectRatio="none" aria-hidden="true">'
            f'<g fill="none" stroke="#e5b23a" stroke-width="4" stroke-linecap="round">{blades}</g></svg>')


def _sun(cls: str) -> str:
    rays = "".join(f'<path d="M100 100 L{100 + 95 * c:.0f} {100 + 95 * s:.0f}"/>'
                   for c, s in [(1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (-.7, .7), (.7, -.7), (-.7, -.7),
                                (.92, .38), (-.92, .38), (.92, -.38), (-.92, -.38), (.38, .92), (-.38, .92), (.38, -.92), (-.38, -.92)])
    return (f'<svg class="dz {cls}" viewBox="0 0 200 200" aria-hidden="true">'
            f'<g class="sun-rays" stroke="#ffd23f" stroke-width="7" stroke-linecap="round" opacity=".8">{rays}</g>'
            f'<circle cx="100" cy="100" r="46" fill="#ffe45e" stroke="#ff9d2e" stroke-width="6"/></svg>')


def _whirl() -> str:
    rings = "".join(f'<ellipse cx="100" cy="100" rx="{20 + i * 12}" ry="{8 + i * 5}" fill="none" stroke="#e6f6ff" '
                    f'stroke-width="5" stroke-dasharray="{24 + i * 8} 14" opacity="{.9 - i * .1:.1f}"/>' for i in range(7))
    return f'<svg class="dz whirl" viewBox="0 0 200 200" aria-hidden="true"><g>{rings}</g></svg>'


def _ring(cls: str) -> str:
    return f'<div class="dz {cls}"></div>'


def _parts(name: str, rng: random.Random, to: str) -> str:
    b = {
        "flames_die": lambda: _flames("flames die", rng),
        "flames_up": lambda: _flames("flames up", rng),
        "flames_low": lambda: _flames("flames low", rng),
        "flames_run": lambda: _flames("flames run", rng),
        "flames_ring": lambda: _ring("fire-ring"),
        "pillar": lambda: _ring("pillar") + _flames("flames up", rng, 7),
        "wave_up": lambda: _wave("wave up"),
        "wave_up_low": lambda: _wave("wave uplow"),
        "wave_low": lambda: _wave("wave low"),
        "wave_drain": lambda: _wave("wave drain"),
        "water_ring": lambda: _ring("water-ring") + _ring("water-ring r2"),
        "whirl": _whirl,
        "vines": lambda: _vines(rng),
        "cracks": lambda: _cracks("cracks", rng),
        "cracks_fade": lambda: _cracks("cracks fade", rng),
        "grass": _grass,
        "sun": lambda: _sun("sun"),
        "sun_low": lambda: _sun("sun low"),
        "steam": lambda: _p("p-steam", 16, rng, x=(5, 95), y=(55, 85), dy=(-45, -25), size=(1, 2.2)),
        "smoke": lambda: _p("p-smoke", 12, rng, x=(5, 95), y=(55, 80), dy=(-50, -30), size=(1.2, 2.4)),
        "embers": lambda: _p("p-ember", 26, rng, y=(70, 100), dy=(-70, -40)),
        "embers_out": lambda: _p("p-ember-out", 22, rng, y=(30, 70), dy=(15, 35)),
        "sparks": lambda: _p("p-spark", 28, rng, x=(20, 80), y=(60, 90), dx=(-25, 25), dy=(-60, -30), delay=(0, .4)),
        "ash": lambda: _p("p-ash", 26, rng, y=(-5, 30), dy=(50, 90), delay=(.3, 1)),
        "leaves_burn": lambda: _p("p-leaf burn", 20, rng, y=(-5, 25), dy=(50, 80), delay=(0, .5)),
        "leaves_wet": lambda: _p("p-leaf wet", 22, rng, y=(-8, 15), dy=(60, 90), delay=(0, .4)),
        "leaves_gold": lambda: _p("p-leaf gold", 22, rng, x=(-5, 60), y=(20, 80), dx=(40, 70), dy=(-15, 10)),
        "leaves_rise": lambda: _p("p-leaf", 18, rng, y=(75, 100), dy=(-60, -35)),
        "leaves_float": lambda: _p("p-leaf", 16, rng, y=(30, 60), dx=(-10, 10), dy=(-8, 8)),
        "leaf_spiral": lambda: f'<div class="dz spiral">{_p("p-leaf orbit", 30, rng, x=(49, 51), y=(49, 51), delay=(0, .7), size=(1.3, 2.3))}</div>',
        "fireflies": lambda: _p("p-firefly", 34, rng, x=(10, 90), y=(15, 85), dx=(-8, 8), dy=(-10, 10), delay=(0, .8)),
        "flowers": lambda: _p("p-flower", 16, rng, x=(5, 95), y=(70, 92), dx=(0, 0), dy=(0, 0), delay=(.5, 1)),
        "bubbles": lambda: _p("p-bubble", 22, rng, x=(10, 90), y=(60, 100), dy=(-60, -35)),
        "bubbles_boil": lambda: _p("p-bubble boil", 26, rng, x=(15, 85), y=(70, 100), dx=(-3, 3), dy=(-25, -12), delay=(0, 1)),
        "drops": lambda: _p("p-drop", 26, rng, y=(-15, 10), dx=(0, 0), dy=(80, 110), delay=(0, .8)),
        "rain": lambda: _p("p-drop", 80, rng, y=(-20, 5), dx=(-4, -2), dy=(100, 120), delay=(0, 1)),
        "dust": lambda: _p("p-dust", 30, rng, x=(-5, 70), y=(30, 95), dx=(30, 60), dy=(-10, 5)),
        "ribbons": lambda: _p("p-ribbon", 20, rng, y=(-10, 10), dx=(-8, 8), dy=(70, 100)),
        "invade": lambda: _ring("invade"),
    }
    return b[name]()


def duel_html(duel: dict) -> str:
    """Sobreposição em tela cheia (sem bloquear cliques) para o duelo."""
    rng = random.Random(duel["seq"] * 31 + COLORS.index(duel["to"]))
    a, b = BIOMES[duel["from"]], BIOMES[duel["to"]]
    parts = "".join(_parts(p, rng, duel["to"]) for p in duel["parts"])
    text = _html.escape(duel["text"])
    return (f'<div class="fx-layer duel duel-{duel["kind"]} from-{duel["from"]} to-{duel["to"]}" '
            f'style="--ca:{a["hex"]};--cb:{b["hex"]}" data-seq="{duel["seq"]}" aria-hidden="true">'
            f'<div class="duel-bg"></div>{parts}<div class="duel-text">{text}</div></div>')


DUEL_CSS = r"""
/* ---------- duelo de biomas ---------- */
.duel { --t: 1.8s; }
.duel .dz, .duel .dp { position: absolute; pointer-events: none; }
.duel-bg { position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 60%, color-mix(in srgb, var(--cb) 30%, transparent), transparent 70%),
  linear-gradient(0deg, color-mix(in srgb, var(--ca) 22%, transparent), transparent 55%); animation: duel-bg var(--t) ease both; }
@keyframes duel-bg { 0% { opacity: 0; } 15%, 75% { opacity: 1; } 100% { opacity: 0; } }
.duel-text { position: relative; z-index: 5; font: 900 clamp(1.4rem, 5.5vw, 2.8rem) var(--title); color: #fff6dc; letter-spacing: .03em;
  text-shadow: 0 3px 0 #000, 0 0 18px var(--cb), 0 0 36px var(--cb); text-align: center; padding: 0 5vw;
  animation: duel-text var(--t) cubic-bezier(.2,1.3,.4,1) both; }
@keyframes duel-text { 0% { transform: translateY(12px) scale(.7); opacity: 0; } 20% { transform: none; opacity: 1; } 80% { opacity: 1; } 100% { transform: translateY(-10px); opacity: 0; } }
/* chamas */
.duel .flames { left: -2vw; right: -2vw; bottom: -2vh; width: 104vw; height: 42vh; transform-origin: 50% 100%; }
.duel .flames path { transform-box: fill-box; transform-origin: 50% 100%; animation: duel-lick .32s ease-in-out infinite alternate; animation-delay: var(--d); }
@keyframes duel-lick { from { transform: scaleY(.85) skewX(-4deg); } to { transform: scaleY(1.12) skewX(4deg); } }
.duel .flames.die { animation: flames-die var(--t) ease-in both; }
@keyframes flames-die { 0%, 25% { transform: scaleY(1); opacity: 1; } 60% { transform: scaleY(.45); opacity: .8; filter: saturate(.4); } 100% { transform: scaleY(0); opacity: 0; filter: grayscale(1); } }
.duel .flames.up { animation: flames-up var(--t) ease-out both; }
@keyframes flames-up { 0% { transform: scaleY(0); } 35% { transform: scaleY(1.2); } 80% { transform: scaleY(1); opacity: 1; } 100% { transform: scaleY(.6); opacity: 0; } }
.duel .flames.low { height: 22vh; animation: flames-up var(--t) ease-out both; }
.duel .flames.run { height: 30vh; animation: flames-run var(--t) linear both; }
@keyframes flames-run { 0% { transform: translateX(-100%); } 70% { opacity: 1; } 100% { transform: translateX(10%); opacity: 0; } }
.duel .fire-ring { width: 60vmin; height: 60vmin; border-radius: 50%; border: 10px solid #ff6a1a; box-shadow: 0 0 40px #ff9d2e, inset 0 0 40px #ff9d2e;
  animation: ring-out var(--t) ease-out both; }
.duel .pillar { width: 22vmin; height: 100vh; bottom: 0; background: linear-gradient(0deg, #ff6a1a, #ffd23fcc 40%, transparent);
  filter: blur(6px); transform-origin: 50% 100%; animation: pillar var(--t) ease-out both; }
@keyframes pillar { 0% { transform: scaleY(0) scaleX(.4); } 40% { transform: scaleY(1) scaleX(1.2); } 80% { opacity: .9; } 100% { transform: scaleY(1.1) scaleX(.3); opacity: 0; } }
/* água */
.duel .wave { left: 0; bottom: 0; width: 100vw; height: 70vh; }
.duel .wave.up { animation: wave-up var(--t) cubic-bezier(.3,.8,.4,1) both; }
@keyframes wave-up { 0%, 15% { transform: translateY(100%); } 55% { transform: translateY(42%); } 80% { opacity: 1; } 100% { transform: translateY(50%); opacity: 0; } }
.duel .wave.uplow { animation: wave-uplow var(--t) ease both; }
@keyframes wave-uplow { 0% { transform: translateY(100%); } 50% { transform: translateY(55%); } 100% { transform: translateY(60%); opacity: 0; } }
.duel .wave.low { animation: wave-low var(--t) ease both; }
@keyframes wave-low { 0% { transform: translateY(70%); } 50% { transform: translateY(55%) skewX(4deg); } 100% { transform: translateY(65%); opacity: 0; } }
.duel .wave.drain { animation: wave-drain var(--t) ease-in both; }
@keyframes wave-drain { 0%, 15% { transform: translateY(55%); opacity: 1; } 100% { transform: translateY(105%); opacity: 0; } }
.duel .water-ring { width: 30vmin; height: 30vmin; border-radius: 50%; border: 8px solid #7ff0ff; box-shadow: 0 0 30px #55c8ff, inset 0 0 30px #55c8ff;
  animation: ring-out var(--t) ease-out both; }
.duel .water-ring.r2 { animation-delay: .35s; }
@keyframes ring-out { 0% { transform: scale(.2); opacity: 0; } 25% { opacity: 1; } 100% { transform: scale(2.6); opacity: 0; } }
.duel .whirl { width: 70vmin; height: 70vmin; bottom: 5vh; animation: whirl var(--t) linear both; }
@keyframes whirl { 0% { transform: rotate(0) scale(.3); opacity: 0; } 30% { opacity: 1; } 100% { transform: rotate(540deg) scale(1.2); opacity: 0; } }
/* mata */
.duel .vines { left: 0; bottom: 0; width: 100vw; height: 75vh; }
.duel .vines path { stroke-dasharray: 600; stroke-dashoffset: 600; animation: vine-grow 1s ease-out forwards; animation-delay: var(--d); }
.duel .vines .vl { transform-box: fill-box; transform-origin: center; transform: scale(0); animation: pop-in .5s cubic-bezier(.2,1.6,.4,1) forwards; animation-delay: var(--d); }
.duel .vines { animation: fade-end var(--t) ease both; }
@keyframes vine-grow { to { stroke-dashoffset: 0; } }
@keyframes pop-in { to { transform: scale(1); } }
@keyframes fade-end { 0%, 80% { opacity: 1; } 100% { opacity: 0; } }
.duel .spiral { left: 0; top: 0; width: 100vw; height: 100vh; animation: spiral var(--t) ease-out both; }
@keyframes spiral { from { transform: rotate(0); } to { transform: rotate(300deg); opacity: .2; } }
/* cerrado */
.duel .grass { left: 0; bottom: 0; width: 100vw; height: 20vh; animation: fade-end var(--t) ease both; }
.duel-wither .grass, .duel-wildfire .grass { filter: sepia(.4); }
.duel-sprout .grass { animation: grass-green var(--t) ease both; }
@keyframes grass-green { 0% { filter: none; } 60% { filter: hue-rotate(60deg) saturate(1.2); } 100% { filter: hue-rotate(70deg); opacity: 0; } }
.duel .sun { width: 34vmin; height: 34vmin; top: 3vh; animation: sun-rise var(--t) ease-out both; }
.duel .sun.low { width: 24vmin; height: 24vmin; }
.duel .sun .sun-rays { transform-origin: 100px 100px; animation: spin-cw 4s linear infinite; }
@keyframes sun-rise { 0% { transform: translateY(-40vh) scale(.4); opacity: 0; } 40% { transform: none; opacity: 1; filter: drop-shadow(0 0 30px #ffd23f); } 85% { opacity: 1; } 100% { transform: scale(1.15); opacity: 0; } }
.duel .cracks { left: 0; bottom: 0; width: 100vw; height: 26vh; animation: fade-end var(--t) ease both; }
.duel .cracks path { stroke-dasharray: 300; stroke-dashoffset: 300; animation: vine-grow .8s ease-out forwards; animation-delay: calc(.5s + var(--d)); }
.duel .cracks.fade path { stroke-dashoffset: 0; animation: cracks-fill var(--t) ease forwards; }
.duel .cracks.fade rect { animation: ground-wet var(--t) ease forwards; }
@keyframes cracks-fill { to { stroke-dashoffset: 300; } }
@keyframes ground-wet { to { fill: #3b2a14; opacity: .3; } }
.duel .invade { width: 30vmin; height: 30vmin; border-radius: 50%; background: radial-gradient(circle, var(--cb) 0 40%, transparent 70%);
  animation: invade var(--t) cubic-bezier(.4,0,.2,1) both; }
@keyframes invade { 0% { transform: translateX(-60vw) scale(.3); opacity: .9; } 45% { transform: scale(2); opacity: .8; } 100% { transform: scale(7); opacity: 0; } }
.duel-invade .duel-bg { background: radial-gradient(circle at 50% 50%, color-mix(in srgb, var(--cb) 38%, transparent), transparent 70%),
  linear-gradient(90deg, color-mix(in srgb, var(--ca) 40%, transparent), transparent 60%); }
/* partículas */
.duel .dp { display: block; width: 10px; height: 10px; transform: scale(var(--s)); animation: dp-move var(--t) ease-out both; animation-delay: var(--d); opacity: 0; }
@keyframes dp-move { 0% { opacity: 0; transform: translate(0, 0) rotate(0) scale(var(--s)); } 15% { opacity: 1; }
  80% { opacity: 1; } 100% { opacity: 0; transform: translate(var(--dx), var(--dy)) rotate(var(--r)) scale(var(--s)); } }
.duel .p-ember, .duel .p-spark { border-radius: 50%; background: #ffd23f; box-shadow: 0 0 10px #ff9d2e, 0 0 3px #fff; width: 6px; height: 6px; }
.duel .p-spark { width: 4px; height: 4px; background: #fff3bf; }
.duel .p-ember-out { border-radius: 50%; width: 7px; height: 7px; animation-name: ember-out; }
@keyframes ember-out { 0% { opacity: 0; background: #ffb02e; box-shadow: 0 0 10px #ff6a1a; } 20% { opacity: 1; }
  100% { opacity: 0; transform: translate(var(--dx), var(--dy)) scale(.4); background: #555; box-shadow: none; } }
.duel .p-steam, .duel .p-smoke { width: 9vmin; height: 9vmin; border-radius: 50%; background: radial-gradient(circle, #f2f7ffcc, transparent 70%); filter: blur(4px); }
.duel .p-smoke { background: radial-gradient(circle, #3a3434cc, transparent 70%); }
.duel .p-ash { width: 5px; height: 5px; background: #8a8a8a; border-radius: 1px; }
.duel .p-leaf { width: 18px; height: 10px; border-radius: 0 80% 0 80%; background: #3fbf6a; box-shadow: inset -2px -2px 0 #0f6e3c; }
.duel .p-leaf.burn { animation-name: leaf-burn; }
@keyframes leaf-burn { 0% { opacity: 0; } 15% { opacity: 1; background: #3fbf6a; } 50% { background: #ff8a3d; box-shadow: 0 0 12px #ff6a1a; }
  100% { opacity: 0; background: #1b1b1b; transform: translate(var(--dx), var(--dy)) rotate(var(--r)) scale(var(--s)); } }
.duel .p-leaf.wet { background: #2e8b57; box-shadow: inset -2px -2px 0 #0f4e2c, 0 0 6px #7ff0ff; }
.duel .p-leaf.gold { background: #e5b23a; box-shadow: inset -2px -2px 0 #8a5a12; }
.duel .p-leaf.orbit { left: 50vw !important; top: 50vh !important; animation-name: orbit; }
@keyframes orbit { 0% { opacity: 0; transform: rotate(var(--r)) translateX(4vmin) scale(var(--s)); } 20% { opacity: 1; }
  100% { opacity: 0; transform: rotate(calc(var(--r) + 360deg)) translateX(38vmin) scale(var(--s)); } }
.duel .p-firefly { width: 6px; height: 6px; border-radius: 50%; background: #e6ff7a; box-shadow: 0 0 12px #c4ff5c, 0 0 24px #c4ff5c; animation-name: firefly; }
@keyframes firefly { 0% { opacity: 0; } 25%, 45%, 65% { opacity: 1; } 35%, 55% { opacity: .3; } 100% { opacity: 0; transform: translate(var(--dx), var(--dy)); } }
.duel .p-flower { width: 16px; height: 16px; border-radius: 50%; background: radial-gradient(circle, #ffd23f 0 28%, #ff8fab 30% 100%);
  box-shadow: 0 0 6px #ff6fa3; animation-name: flower; }
@keyframes flower { 0% { opacity: 0; transform: scale(0); } 30% { opacity: 1; transform: scale(calc(var(--s) * 1.3)); } 80% { opacity: 1; transform: scale(var(--s)); } 100% { opacity: 0; } }
.duel .p-bubble { width: 14px; height: 14px; border-radius: 50%; border: 2px solid #bff6ff; background: #7ff0ff22; }
.duel .p-bubble.boil { border-color: #fff; animation-duration: .7s; animation-iteration-count: 2; }
.duel .p-drop { width: 4px; height: 24px; border-radius: 3px; background: linear-gradient(#dff5ff00, #bff6ff); box-shadow: 0 0 6px #55c8ff; animation-timing-function: linear; animation-duration: .8s; animation-iteration-count: 2; }
.duel .p-dust { width: 6px; height: 6px; border-radius: 50%; background: #ffd27a; box-shadow: 0 0 8px #e5b23a; }
.duel .p-ribbon { width: 8px; height: 26px; border-radius: 2px; background: linear-gradient(#e8392b 0 25%, #1fa65a 25% 50%, #1f7be0 50% 75%, #f2b311 75%); }
@media (prefers-reduced-motion: reduce) {
  .duel > :not(.duel-text):not(.duel-bg) { display: none !important; }
  .duel-bg, .duel-text { animation: none !important; }
}
"""
