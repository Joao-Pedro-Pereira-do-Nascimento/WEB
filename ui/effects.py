"""Efeitos visuais (sobreposições animadas), sons (Web Audio API) e a
visualização ampliada das cartas.

Como cada animação toca **uma única vez** mesmo com o Streamlit redesenhando
a página a cada ~1 s:

- todo efeito tem uma **chave de evento** (ex.: ``ev:SALA:partida:seq``,
  ``arrive:SALA:jogador``); ``fx_push`` guarda as chaves já tocadas em
  ``st.session_state`` e ignora repetidas;
- o HTML do efeito fica no mesmo "slot" sem mudar até expirar — como o
  conteúdo não muda, o navegador não remonta o elemento e a animação não
  reinicia; depois some;
- os sons usam um ``id`` sempre crescente (o motor de áudio ignora ids velhos).
"""

from __future__ import annotations

import html as _html
import json

import random
from typing import MutableMapping

from game.cards import BIOMES, back_svg

from .icons import icon

esc = _html.escape

# Tipos de evento que geram efeito de tela (ordem = prioridade)
FX_PRIORITY = ["game_over", "round_over", "denounce", "challenge_ok", "challenge_fail", "wild4",
               "draw2", "skip", "reverse", "wild", "color", "uno", "shuffle", "deal", "turn"]

SOUND_FOR = {
    "play": "play", "draw": "draw", "skip": "skip", "reverse": "reverse", "draw2": "draw2",
    "wild4": "wild4", "wild4_wait": "alarm", "wild": "wild", "uno": "uno", "denounce": "denounce",
    "shuffle": "shuffle", "deal": "deal", "round_over": "win", "game_over": "fanfare",
    "challenge_ok": "ding", "challenge_fail": "denounce", "color": "wild", "turn": "turn",
    "pass": "pass", "skip_host": "pass", "left": "depart",
}

FX_SECONDS = {"default": 3.2, "portal": 3.6, "arrive": 4.4, "depart": 3.4, "victory": 5.5, "defeat": 4.5}
SEEN_LIMIT = 400


# =========================================================================== fila "toca uma vez"

QUEUE_LIMIT = 3


def _protected(cur: dict | None, now: float) -> bool:
    """Um duelo de biomas em andamento nunca é cortado por outro efeito."""
    return bool(cur and now < cur["until"] and str(cur.get("key", "")).startswith("duel:"))


def fx_push(store: MutableMapping, key: str, html: str, now: float, seconds: float | None = None,
            slot: str = "fx", sounds: list[str] | tuple = (), after: bool = False) -> bool:
    """Agenda um efeito no ``slot``. Retorna False (e não faz nada) se ``key`` já tocou.

    Com ``after=True`` o efeito entra na fila: começa quando o atual do slot acabar
    (ex.: o duelo de biomas primeiro, o efeito da carta especial em seguida). Um duelo
    em andamento nunca é cortado: o que chegar depois (ex.: "sua vez", no rerun
    seguinte) vai para a fila. A fila guarda no máximo ``QUEUE_LIMIT`` itens e só o
    duelo mais recente (os bots jogam rápido: duelos antigos ficariam atrasados)."""
    seen = store.setdefault("_fx_seen", [])
    if key in seen:
        return False
    seen.append(key)
    if len(seen) > SEEN_LIMIT:
        del seen[: len(seen) - SEEN_LIMIT]
    if html:
        dur = seconds or FX_SECONDS["default"]
        name = f"_slot_{slot}"
        _advance(store, slot, now)
        cur = store.get(name)
        if cur and now < cur["until"] and (after or _protected(cur, now)):
            queue = cur.setdefault("queue", [])
            if key.startswith("duel:"):
                queue[:] = [q for q in queue if not q["key"].startswith("duel:")]
            queue.append({"html": html, "seconds": dur, "key": key})
            del queue[:-QUEUE_LIMIT]
        else:
            store[name] = {"html": html, "until": now + dur, "key": key}
    if sounds:
        sfx_queue(store, list(sounds), now)
    return True


def _advance(store: MutableMapping, slot: str, now: float) -> None:
    """Passa para o próximo item da fila quando o atual termina (cada um com seu tempo cheio)."""
    name = f"_slot_{slot}"
    data = store.get(name)
    while data and now >= data["until"] and data.get("queue"):
        nxt = data["queue"].pop(0)
        start = data["until"]
        if now - start > nxt["seconds"]:  # ninguém redesenhou a tempo: começa agora
            start = now
        data = {"html": nxt["html"], "until": start + nxt["seconds"], "key": nxt["key"], "queue": data["queue"]}
        store[name] = data


def fx_seen(store: MutableMapping, key: str) -> bool:
    return key in store.get("_fx_seen", [])


def fx_forget(store: MutableMapping, prefix: str) -> None:
    store["_fx_seen"] = [k for k in store.get("_fx_seen", []) if not k.startswith(prefix)]


def fx_current(store: MutableMapping, slot: str, now: float) -> str:
    _advance(store, slot, now)
    data = store.get(f"_slot_{slot}")
    if data and now < data["until"]:
        return data["html"]
    return ""


def sfx_queue(store: MutableMapping, names: list[str], now: float) -> None:
    """Sons para o próximo desenho do slot de áudio (id sempre crescente)."""
    if not names:
        return
    cur = store.get("sfx")
    new_id = max(int(now * 1000), (cur or {}).get("id", 0) + 1)
    if cur and not cur.get("played"):
        names = list(cur.get("names", [])) + list(names)  # mesmo redesenho: junta os sons
    store["sfx"] = {"names": names[-5:], "id": new_id}


# =========================================================================== chegada / saída de jogadores

def roster(room: dict) -> dict[str, str]:
    """Jogadores presentes (quem saiu e virou bot no meio da partida não conta)."""
    return {p["id"]: p["name"] for p in room.get("players", []) if not p.get("left")}


def roster_diff(prev: dict[str, str] | None, cur: dict[str, str], me: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(entraram, saíram) comparando a lista anterior com a atual. Primeira visão: nada."""
    if prev is None:
        return [], []
    joined = [(pid, name) for pid, name in cur.items() if pid not in prev and pid != me]
    left = [(pid, name) for pid, name in prev.items() if pid not in cur and pid != me]
    return joined, left


def _campfire() -> str:
    flames = "".join(
        f'<path class="hf-flame" style="animation-delay:{d:.2f}s" d="M{x} 92 c-10 -6 -12 -20 -4 -34 c2 8 6 10 8 10 '
        f'c-2 -14 4 -26 12 -32 c-2 12 4 18 8 26 c5 10 2 24 -12 30 Z" fill="url(#hf-fire)" transform="translate({dx} 0) scale({sc})"/>'
        for x, dx, sc, d in [(44, -8, 1.0, 0), (52, 2, 1.15, .12), (60, 6, .9, .25)])
    return f"""<svg class="herald-fire" viewBox="0 0 120 120" aria-hidden="true">
<defs><linearGradient id="hf-fire" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#b31b00"/>
<stop offset=".5" stop-color="#ff7a1a"/><stop offset="1" stop-color="#ffe680"/></linearGradient>
<radialGradient id="hf-glow"><stop offset="0" stop-color="#ffb02e" stop-opacity=".7"/><stop offset="1" stop-color="#ff5a1a" stop-opacity="0"/></radialGradient></defs>
<ellipse cx="60" cy="86" rx="58" ry="34" fill="url(#hf-glow)" class="hf-glow"/>
{flames}
<path d="M26 104 L94 90" stroke="#5a3218" stroke-width="10" stroke-linecap="round"/>
<path d="M28 90 L92 104" stroke="#6b3e20" stroke-width="10" stroke-linecap="round"/>
{"".join(f'<circle class="hf-spark" style="animation-delay:{i * .3:.1f}s;--sx:{(i - 2) * 9}px" cx="60" cy="70" r="2.4" fill="#ffd23f"/>' for i in range(5))}
</svg>"""


def arrival_html(name: str, key: str) -> str:
    return (f'<div class="herald arrive" data-key="{esc(key, quote=True)}">'
            f'<div class="herald-smoke"></div>{_campfire()}'
            f'<div class="herald-text"><div class="herald-name">{esc(name)}</div>'
            f'<div class="herald-sub">entrou na sala</div></div></div>')


def departure_html(name: str, key: str) -> str:
    return (f'<div class="herald depart" data-key="{esc(key, quote=True)}"><div class="depart-fog"></div>'
            f'<div class="herald-sub">{esc(name)} saiu da sala</div></div>')


# =========================================================================== entrada na sala (portal)

def portal_html(code: str, key: str, title: str | None = None) -> str:
    rng = random.Random(code)
    cards = "".join(
        f'<div class="portal-card" style="--a:{i * 45 + rng.uniform(-8, 8):.0f}deg;--d:{i * .06:.2f}s;--r:{rng.uniform(-40, 40):.0f}deg">'
        f'{back_svg()}</div>' for i in range(8))
    title = title or code
    letters = "".join(f'<span style="--i:{i}">{esc(ch) if ch != " " else "&nbsp;"}</span>' for i, ch in enumerate(title))
    size = " long" if len(title) > 10 else ""
    return (f'<div class="fx-layer portal" data-key="{esc(key, quote=True)}">'
            f'<div class="portal-veil"></div><div class="portal-door left"></div><div class="portal-door right"></div>'
            f'<div class="portal-ring"></div><div class="portal-cards">{cards}</div>'
            f'<div class="portal-title"><div class="portal-eyebrow">entrando na sala</div>'
            f'<div class="portal-code{size}">{letters}</div><div class="portal-sub">código {esc(code)}</div></div></div>')


# =========================================================================== efeitos de jogo

def pick_fx(events: list[dict]) -> dict | None:
    for etype in FX_PRIORITY:
        for ev in reversed(events):
            if ev["type"] == etype:
                return ev
    return None


def _confetti(n: int = 70, rng: random.Random | None = None) -> str:
    """Brasas douradas e folhas caindo (vitória)."""
    rng = rng or random.Random()
    colors = ["#ffd23f", "#e9c46a", "#ff9d2e", "#fff3bf", "#7fdc8a", "#ff6a3d"]
    out = []
    for _ in range(n):
        out.append(
            f'<i class="confetti" style="left:{rng.uniform(0, 100):.1f}vw;background:{rng.choice(colors)};'
            f'--dx:{rng.uniform(-25, 25):.0f}vw;--rot:{rng.uniform(-900, 900):.0f}deg;'
            f'--t:{rng.uniform(2.6, 4.8):.2f}s;--d:{rng.uniform(0, 1.6):.2f}s;'
            f'border-radius:{rng.choice(["0 60% 0 60%", "50%", "2px"])}"></i>')
    return "".join(out)


def _embers(n: int = 26, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return "".join(
        f'<i class="fx-ember" style="left:{rng.uniform(5, 95):.0f}vw;--dx:{rng.uniform(-15, 15):.0f}vw;'
        f'animation-delay:{rng.uniform(0, .6):.2f}s"></i>' for _ in range(n))


def _ash(n: int = 40, rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    return "".join(
        f'<i class="fx-ash" style="left:{rng.uniform(0, 100):.0f}vw;--dx:{rng.uniform(-8, 8):.0f}vw;'
        f'--t:{rng.uniform(3, 5):.1f}s;animation-delay:{rng.uniform(0, 1.5):.2f}s"></i>' for _ in range(n))


def _fly_cards(n: int, to_me: bool) -> str:
    """Cartas voando do monte para quem compra (para baixo se for você)."""
    return "".join(
        f'<div class="fx-flycard {"down" if to_me else "up"}" style="--i:{i};--x:{(i - (n - 1) / 2) * 9:.0f}vw">{back_svg()}</div>'
        for i in range(min(n, 6)))


def _whirl_svg() -> str:
    rings = "".join(
        f'<ellipse cx="100" cy="{170 - i * 22}" rx="{18 + i * 13}" ry="{6 + i * 2.4:.1f}" fill="none" stroke="#e9dcc0" '
        f'stroke-width="5" stroke-dasharray="{30 + i * 8} 14" opacity="{.9 - i * .1:.1f}"/>' for i in range(7))
    return f'<svg class="fx-whirlwind" viewBox="0 0 200 200" aria-hidden="true"><g class="ww-spin">{rings}</g></svg>'


def _saci_cap() -> str:
    return ('<svg class="fx-cap-fly" viewBox="0 0 60 50" aria-hidden="true"><path d="M4 44 C4 26 22 18 56 4 '
            'C46 18 42 30 42 44 Q22 36 4 44 Z" fill="#e01e37" stroke="#4a0610" stroke-width="2"/>'
            '<circle cx="56" cy="4" r="4" fill="#ff7088"/></svg>')


def _footprints_svg() -> str:
    def foot(x, y, rot):
        toes = "".join(f'<circle cx="-13" cy="{(i - 2) * 3.2:.1f}" r="2"/>' for i in range(5))
        return (f'<g transform="translate({x} {y}) rotate({rot})"><ellipse rx="10" ry="5.6"/>{toes}</g>')
    steps = "".join(foot(40 + i * 70, 40 + (i % 2) * 26, 180 + (8 if i % 2 else -8)) for i in range(7))
    return f'<svg class="fx-footprints" viewBox="0 0 520 100" aria-hidden="true"><g fill="#f0cf7a">{steps}</g></svg>'


def _cauldron_svg() -> str:
    bubbles = "".join(f'<circle class="cb" style="animation-delay:{i * .25:.2f}s;--bx:{(i - 3) * 6}px" cx="{70 + i * 10}" cy="58" r="{5 + (i % 3) * 2}" fill="#9dff6a" stroke="#2f7d12" stroke-width="1.5"/>'
                      for i in range(7))
    return f"""<svg class="fx-cauldron" viewBox="0 0 200 140" aria-hidden="true">
{bubbles}
<path d="M30 60 Q30 130 100 130 Q170 130 170 60 Z" fill="#1e1e2e" stroke="#000" stroke-width="3"/>
<ellipse cx="100" cy="60" rx="72" ry="13" fill="#6dff3a" stroke="#38384e" stroke-width="7"/>
<path d="M40 128 l-10 12 M160 128 l10 12" stroke="#1e1e2e" stroke-width="7"/></svg>"""


def _eyes_svg() -> str:
    return ('<svg class="fx-eyes" viewBox="0 0 200 60" aria-hidden="true">'
            '<ellipse cx="60" cy="30" rx="26" ry="18" fill="#ffe14d"/><ellipse cx="60" cy="30" rx="5" ry="16" fill="#140b04"/>'
            '<ellipse cx="140" cy="30" rx="26" ry="18" fill="#ffe14d"/><ellipse cx="140" cy="30" rx="5" ry="16" fill="#140b04"/></svg>')


def _flame_wall() -> str:
    tongues = "".join(
        f'<path class="fw" style="animation-delay:{(i % 5) * .08:.2f}s" d="M{x} 300 c-30 -30 -34 -90 -6 -150 '
        f'c6 30 18 40 26 42 c-6 -50 10 -100 40 -126 c-6 46 14 74 28 104 c18 40 8 100 -40 130 Z" '
        f'fill="url(#fw-fire)" transform="translate(0 {(i % 3) * 18})"/>' for i, x in enumerate(range(-40, 1100, 90)))
    return f"""<svg class="fx-flamewall" viewBox="0 0 1000 300" preserveAspectRatio="none" aria-hidden="true">
<defs><linearGradient id="fw-fire" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#7a0a00"/>
<stop offset=".45" stop-color="#ff5a1a"/><stop offset="1" stop-color="#ffe680" stop-opacity=".9"/></linearGradient></defs>{tongues}</svg>"""


def _water_wave(hexcolor: str) -> str:
    return f"""<svg class="fx-waterwave" viewBox="0 0 1200 600" preserveAspectRatio="none" aria-hidden="true">
<path d="M0 300 Q150 220 300 300 T600 300 T900 300 T1200 300 V600 H0 Z" fill="{hexcolor}" opacity=".55"/>
<path d="M0 340 Q150 270 300 340 T600 340 T900 340 T1200 340 V600 H0 Z" fill="{hexcolor}" opacity=".7"/>
<path d="M0 300 Q150 220 300 300 T600 300 T900 300 T1200 300" fill="none" stroke="#e9ffff" stroke-width="6" opacity=".8"/></svg>"""


def _shimmer(rng: random.Random, n: int = 18) -> str:
    return "".join(
        f'<i class="fx-glint" style="left:{rng.uniform(5, 95):.0f}vw;top:{rng.uniform(25, 85):.0f}vh;'
        f'animation-delay:{rng.uniform(0, 1.2):.2f}s"></i>' for _ in range(n))


def _crown_svg() -> str:
    return ('<svg class="fx-crown" viewBox="0 0 120 90" aria-hidden="true"><defs><linearGradient id="cr-g" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#fff3bf"/><stop offset=".5" stop-color="#e9c46a"/><stop offset="1" stop-color="#8a5a12"/></linearGradient></defs>'
            '<path d="M10 76 L4 22 L32 46 L60 8 L88 46 L116 22 L110 76 Z" fill="url(#cr-g)" stroke="#2a1804" stroke-width="4" stroke-linejoin="round"/>'
            '<rect x="8" y="74" width="104" height="12" rx="3" fill="url(#cr-g)" stroke="#2a1804" stroke-width="4"/>'
            '<circle cx="60" cy="56" r="8" fill="#e01e37" stroke="#2a1804" stroke-width="3"/>'
            '<circle cx="30" cy="62" r="5" fill="#1fa65a" stroke="#2a1804" stroke-width="2.5"/><circle cx="90" cy="62" r="5" fill="#1f7be0" stroke="#2a1804" stroke-width="2.5"/></svg>')


def fx_html(ev: dict, names: dict[str, str], me: str) -> str:
    """HTML da sobreposição animada para um evento de jogo."""
    t = ev["type"]
    seq = ev["seq"]
    rng = random.Random(seq)
    target = esc(names.get(ev.get("target") or ev.get("player") or "", ""))
    player = esc(names.get(ev.get("player") or "", ""))
    to_me = (ev.get("target") or ev.get("player")) == me
    inner = ""
    shake = False
    cls = t
    if t == "skip":
        inner = (f'{_whirl_svg()}{_saci_cap()}<div class="fx-dust"></div>'
                 f'<div class="fx-text" style="--c:#ffd23f">PULOU!<span class="fx-sub">{target} perdeu a vez</span></div>')
    elif t == "reverse":
        inner = (f'<div class="fx-turn-arrows">{icon("ccw", 240)}</div>{_footprints_svg()}<div class="fx-hairfire"></div>'
                 '<div class="fx-text" style="--c:#3ddc84">INVERTEU!<span class="fx-sub">o sentido do jogo mudou</span></div>')
    elif t == "draw2":
        inner = (f'<div class="fx-flash" style="--c:#4caf50"></div><div class="fx-smoke"></div>{_eyes_svg()}{_cauldron_svg()}'
                 f'{_fly_cards(2, to_me)}'
                 f'<div class="fx-text" style="--c:#9dff6a">+2<span class="fx-sub">{target} compra 2 cartas</span></div>')
        shake = True
    elif t in ("wild4", "challenge_fail"):
        n = 4 if t == "wild4" else 6
        sub = (f"{target} compra 4 cartas" if t == "wild4"
               else f"desafio errado: {target} compra 6 cartas")
        inner = (f'<div class="fx-flash" style="--c:#ff4d1a"></div>{_flame_wall()}{_embers(rng=rng)}{_fly_cards(n, to_me)}'
                 f'<div class="fx-text" style="--c:#ff8c1a">+{n}<span class="fx-sub">{sub}</span></div>')
        shake = True
        cls = "wild4"
    elif t in ("wild", "color"):
        col = BIOMES.get(ev.get("color", ""), {"hex": "#ffffff", "name": ""})
        sub = "nova cor da mesa" if t == "wild" else f"{player} escolheu a cor"
        inner = (f'{_water_wave(col["hex"])}<div class="fx-colorwave" style="--c:{col["hex"]}"></div>{_shimmer(rng)}'
                 f'<div class="fx-text" style="--c:{col["hex"]}">{esc(col["name"].upper())}!<span class="fx-sub">{sub}</span></div>')
        cls = "wild"
    elif t == "uno":
        inner = ('<div class="fx-shout"></div><div class="fx-shout s2"></div><div class="fx-shout s3"></div>'
                 f'<div class="fx-text" style="--c:#ff3d00">UNO!<span class="fx-sub">{player} tem 1 carta</span></div>')
    elif t == "denounce":
        inner = (f'<div class="fx-flash" style="--c:#ff2d55"></div><div class="fx-horn">{icon("horn", 160)}</div>'
                 f'{_fly_cards(2, to_me)}'
                 f'<div class="fx-text" style="--c:#ff2d55">PEGO!<span class="fx-sub">{target} esqueceu o UNO: +2</span></div>')
        shake = True
    elif t == "challenge_ok":
        inner = (f'<div class="fx-rays"></div><div class="fx-horn">{icon("swords", 170)}</div>'
                 f'<div class="fx-text" style="--c:#3ddc84">DESAFIO!<span class="fx-sub">{target} blefou e compra 4 cartas</span></div>')
    elif t in ("round_over", "game_over"):
        won = ev.get("player") == me
        pts = ev.get("points", 0)
        if won:
            title = "VITÓRIA!"
            sub = ("você venceu a partida" if t == "game_over" else "você venceu a rodada") + f" · +{pts} pontos"
            inner = (f'<div class="victory-bg"></div><div class="fx-rays gold"></div>{_confetti(rng=rng)}{_embers(30, rng)}'
                     f'{_crown_svg()}<div class="fx-text epic" style="--c:#ffd23f">{title}<span class="fx-sub">{sub}</span></div>')
            cls = "victory"
        else:
            title = "DERROTA" if t == "game_over" else "FIM DA RODADA"
            sub = f"{player} venceu" + (" a partida" if t == "game_over" else " a rodada") + f" · +{pts} pontos"
            inner = (f'<div class="defeat-bg"></div><div class="defeat-fog"></div>{_ash(rng=rng)}'
                     f'<div class="fx-text grim" style="--c:#8a7a9a">{title}<span class="fx-sub">{sub}</span></div>')
            cls = "defeat"
    elif t == "shuffle":
        inner = f'<div class="fx-banner">{icon("loop", 22)} Embaralhando o descarte...</div>'
    elif t == "deal":
        inner = f'<div class="fx-banner">{icon("cards", 22)} Rodada {ev.get("round", "")}: cartas distribuídas</div>'
    elif t == "turn":
        inner = f'<div class="fx-banner turn">{icon("torch", 22)} Sua vez! {icon("torch", 22)}</div>'
    else:
        return ""
    style = ""
    if shake:
        style = (f"<style>@keyframes shake{seq}{{0%,100%{{transform:none}}10%,50%,90%{{transform:translate(-7px,3px) rotate(-.6deg)}}"
                 f"30%,70%{{transform:translate(7px,-3px) rotate(.6deg)}}}}"
                 f"@media (prefers-reduced-motion: no-preference){{.st-key-table{{animation:shake{seq} .6s ease both}}}}</style>")
    return f'{style}<div class="fx-layer fx-{cls}" data-seq="{seq}">{inner}</div>'


def fx_seconds_for(ev: dict, me: str) -> float:
    if ev["type"] in ("round_over", "game_over"):
        return FX_SECONDS["victory"] if ev.get("player") == me else FX_SECONDS["defeat"]
    return FX_SECONDS["default"]


# =========================================================================== som

SOUND_ENGINE = r"""
(function(){
  const W = window;
  if (!W.__unoSfx) {
    const S = W.__unoSfx = { ctx: null, last: 0 };
    S.ensure = function(){
      if (!S.ctx) { try { S.ctx = new (W.AudioContext || W.webkitAudioContext)(); } catch(e) { return null; } }
      if (S.ctx.state === 'suspended') { S.ctx.resume().catch(()=>{}); }
      return S.ctx;
    };
    const unlock = () => S.ensure();
    W.document.addEventListener('pointerdown', unlock, {capture:true});
    W.document.addEventListener('keydown', unlock, {capture:true});
    S.tone = function(f, d, type, vol, at, f2){
      const c = S.ctx, t = c.currentTime + (at||0);
      const o = c.createOscillator(), g = c.createGain();
      o.type = type || 'sine'; o.frequency.setValueAtTime(f, t);
      if (f2) o.frequency.exponentialRampToValueAtTime(f2, t + d);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol||0.2, t + 0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, t + d);
      o.connect(g).connect(c.destination); o.start(t); o.stop(t + d + 0.05);
    };
    S.noise = function(d, vol, freq, at, freq2, q){
      const c = S.ctx, t = c.currentTime + (at||0);
      const len = Math.max(1, Math.floor(c.sampleRate * d)); const b = c.createBuffer(1, len, c.sampleRate);
      const data = b.getChannelData(0); for (let i=0;i<len;i++) data[i] = Math.random()*2-1;
      const s = c.createBufferSource(); s.buffer = b;
      const fl = c.createBiquadFilter(); fl.type = 'bandpass'; fl.Q.value = q || 1.2;
      fl.frequency.setValueAtTime(freq||1200, t); if (freq2) fl.frequency.exponentialRampToValueAtTime(freq2, t + d);
      const g = c.createGain(); g.gain.setValueAtTime(vol||0.2, t); g.gain.exponentialRampToValueAtTime(0.0001, t + d);
      s.connect(fl).connect(g).connect(c.destination); s.start(t); s.stop(t + d);
    };
    const notes = (arr, type, vol, step) => arr.forEach((f,i)=>S.tone(f, step*1.6, type, vol, i*step));
    S.lib = {
      play:    () => { S.noise(0.14, 0.25, 2400, 0, 500); S.tone(520, 0.09, 'triangle', 0.18, 0.08); },
      draw:    () => { S.noise(0.18, 0.18, 900, 0, 2200); S.tone(320, 0.12, 'sine', 0.12, 0.06, 440); },
      pass:    () => { S.tone(420, 0.12, 'sine', 0.1, 0, 300); },
      skip:    () => { S.noise(0.7, 0.3, 300, 0, 3500, 4); S.tone(700, 0.5, 'sine', 0.06, 0.05, 180); },
      reverse: () => { S.tone(380, 0.16, 'square', 0.08, 0, 820); S.tone(820, 0.16, 'square', 0.08, 0.17, 380); S.noise(0.08,0.15,3000,0.34); },
      draw2:   () => { S.tone(140, 0.22, 'sine', 0.45, 0, 55); S.tone(140, 0.22, 'sine', 0.45, 0.22, 55); S.noise(0.25,0.2,500,0.02,200); },
      wild4:   () => { S.noise(0.9, 0.35, 220, 0, 90, 0.7); [0,0.16,0.32,0.48].forEach(a=>S.tone(110, 0.2, 'sine', 0.4, a, 50)); for(let i=0;i<8;i++) S.noise(0.03,0.2,4000,0.1+Math.random()*0.7); },
      alarm:   () => { S.tone(660, 0.14, 'square', 0.07, 0); S.tone(660, 0.14, 'square', 0.07, 0.2); },
      wild:    () => { notes([523,659,784,1047,1319], 'triangle', 0.14, 0.07); S.noise(0.5, 0.06, 6000, 0.1); },
      uno:     () => { notes([659,784,1047], 'square', 0.09, 0.09); S.tone(1319, 0.45, 'triangle', 0.15, 0.27); },
      denounce:() => { S.tone(150, 0.28, 'sawtooth', 0.16, 0); S.tone(150, 0.28, 'sawtooth', 0.16, 0.34); },
      ding:    () => { S.tone(988, 0.3, 'sine', 0.2, 0); S.tone(1480, 0.4, 'sine', 0.14, 0.12); },
      turn:    () => { S.tone(880, 0.22, 'sine', 0.16, 0); S.tone(1320, 0.3, 'sine', 0.12, 0.1); },
      shuffle: () => { for (let i=0;i<10;i++) S.noise(0.04, 0.18, 2500, i*0.045); },
      deal:    () => { for (let i=0;i<7;i++) S.noise(0.05, 0.16, 1800+i*120, i*0.07); },
      win:     () => { notes([523,659,784,1047,784,1047], 'triangle', 0.15, 0.11); },
      fanfare: () => { notes([392,523,659,784,659,784,1047], 'square', 0.08, 0.12); S.tone(1047, 0.9, 'triangle', 0.15, 0.85); },
      defeat:  () => { notes([392,370,349,311], 'triangle', 0.12, 0.22); S.tone(196, 1.2, 'sine', 0.14, 0.9, 147); },
      portal:  () => { S.noise(1.6, 0.16, 200, 0, 2400, 3); S.tone(220, 1.4, 'sine', 0.1, 0, 440); notes([440,554,659,880], 'triangle', 0.07, 0.18); },
      arrive:  () => { S.tone(196, 0.6, 'sawtooth', 0.05, 0, 294); S.tone(294, 0.7, 'triangle', 0.1, 0.25); S.noise(0.6, 0.08, 700, 0, 300); S.tone(1175, 0.5, 'sine', 0.08, 0.5); },
      depart:  () => { S.noise(0.9, 0.08, 1400, 0, 250, 2); S.tone(523, 0.5, 'sine', 0.05, 0, 262); },
      // duelo de biomas: um som por bioma que chega à mesa
      b_red:    () => { S.noise(0.9, 0.22, 400, 0, 1800, 0.8); for (let i=0;i<6;i++) S.noise(0.03, 0.14, 3500, 0.1+Math.random()*0.6); S.tone(98, 0.6, 'sawtooth', 0.05, 0, 147); },
      b_green:  () => { S.noise(0.8, 0.12, 2600, 0, 900, 1.5); notes([392, 494, 587, 784], 'triangle', 0.07, 0.1); },
      b_blue:   () => { S.noise(1.0, 0.2, 700, 0, 250, 0.9); S.tone(330, 0.5, 'sine', 0.08, 0.05, 220); for (let i=0;i<4;i++) S.tone(900+i*150, 0.06, 'sine', 0.06, 0.2+i*0.12, 1400); },
      b_yellow: () => { S.tone(523, 0.7, 'triangle', 0.08, 0); S.tone(659, 0.7, 'triangle', 0.07, 0.08); S.tone(784, 0.8, 'triangle', 0.07, 0.16); S.noise(0.7, 0.06, 5000, 0.1, 3000, 2); },
    };
    S.muted = false;
    S.play = function(list, seq){
      if (seq <= S.last) return; S.last = seq;
      if (S.muted || !list || !list.length) return;
      const c = S.ensure(); if (!c) return;
      list.slice(0, 5).forEach((name, i) => W.setTimeout(() => { try { (S.lib[name]||S.lib.play)(); } catch(e) {} }, i * 260));
    };
  }
})();
"""

# Visualização ampliada das cartas: passar o mouse (PC) ou segurar ~350 ms (celular).
# O clone é o próprio SVG vetorial da carta, desenhado grande (nítido), com os textos
# da carta em HTML ao lado. O toque longo NÃO joga a carta (o clique seguinte é engolido).
PREVIEW_ENGINE = r"""
(function(){
  const W = window, D = W.document;
  if (W.__unoPreview) return; W.__unoPreview = true;
  let box = null, bg = null, cur = null, hoverTimer = null, lpTimer = null, lpOn = false, swallowUntil = 0, start = null;
  function cardFrom(t){
    if (!t || !t.closest) return null;
    const c = t.closest('.uno-card[data-name]'); if (c) return c;
    const hc = t.closest('[class*="st-key-hc_"]'); if (hc) return hc.querySelector('.uno-card[data-name]');
    return null;
  }
  function build(){
    if (box && box.isConnected) return;
    bg = D.createElement('div'); bg.id = 'uno-pv-bg'; D.body.appendChild(bg);
    box = D.createElement('div'); box.id = 'uno-pv'; box.setAttribute('role', 'dialog');
    box.innerHTML = '<div class="pv-card uno-card live"></div><div class="pv-info"><div class="pv-name"></div>' +
      '<div class="pv-sub"></div><div class="pv-effect"></div><div class="pv-blurb"></div></div>';
    D.body.appendChild(box);
    bg.addEventListener('click', hide);
  }
  function hide(){
    cur = null; clearTimeout(hoverTimer);
    if (box) { box.classList.remove('show', 'mobile'); }
    if (bg) { bg.classList.remove('show'); }
  }
  function show(c, mobile){
    build();
    const svg = c.querySelector('svg'); if (!svg) return;
    cur = c;
    box.querySelector('.pv-card').innerHTML = svg.outerHTML;
    box.querySelector('.pv-name').textContent = c.dataset.name || '';
    box.querySelector('.pv-sub').textContent = c.dataset.sub || '';
    box.querySelector('.pv-effect').textContent = c.dataset.effect || '';
    box.querySelector('.pv-blurb').textContent = c.dataset.blurb || '';
    box.classList.toggle('mobile', !!mobile);
    bg.classList.toggle('show', !!mobile);
    box.style.left = '0px'; box.style.top = '0px';
    box.classList.add('show');
    if (mobile) { box.style.left = ''; box.style.top = ''; return; }
    const r = c.getBoundingClientRect(), vw = W.innerWidth, vh = W.innerHeight;
    const bw = box.offsetWidth, bh = box.offsetHeight, m = 10;
    let left = r.right + 14, top = r.top + r.height / 2 - bh / 2;
    if (left + bw > vw - m) left = r.left - bw - 14;
    if (left < m) { left = Math.max(m, Math.min(vw - bw - m, r.left + r.width / 2 - bw / 2)); top = r.top - bh - 12; if (top < m) top = r.bottom + 12; }
    top = Math.max(m, Math.min(vh - bh - m, top));
    box.style.left = left + 'px'; box.style.top = top + 'px';
  }
  D.addEventListener('pointermove', function(e){
    if (e.pointerType !== 'mouse') return;
    const c = cardFrom(e.target);
    if (c === cur) return;
    clearTimeout(hoverTimer);
    if (!c) { hide(); return; }
    hoverTimer = W.setTimeout(function(){ show(c, false); }, 120);
  }, {passive: true});
  D.addEventListener('pointerdown', function(e){ if (e.pointerType === 'mouse') hide(); }, true);
  W.addEventListener('scroll', function(){ if (box && !box.classList.contains('mobile')) hide(); }, true);
  D.addEventListener('touchstart', function(e){
    const c = cardFrom(e.target); if (!c) return;
    const t = e.touches[0]; start = {x: t.clientX, y: t.clientY};
    clearTimeout(lpTimer);
    lpTimer = W.setTimeout(function(){ lpOn = true; show(c, true); try { W.navigator.vibrate && W.navigator.vibrate(12); } catch (err) {} }, 350);
  }, {passive: true, capture: true});
  D.addEventListener('touchmove', function(e){
    if (!start || lpOn) return;
    const t = e.touches[0];
    if (Math.abs(t.clientX - start.x) > 10 || Math.abs(t.clientY - start.y) > 10) { clearTimeout(lpTimer); start = null; }
  }, {passive: true, capture: true});
  function endTouch(e){
    clearTimeout(lpTimer); start = null;
    if (lpOn) { lpOn = false; swallowUntil = Date.now() + 700; if (e.cancelable) e.preventDefault(); hide(); }
  }
  D.addEventListener('touchend', endTouch, {passive: false, capture: true});
  D.addEventListener('touchcancel', endTouch, {passive: false, capture: true});
  D.addEventListener('click', function(e){
    if (Date.now() < swallowUntil) { e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); }
  }, true);
  D.addEventListener('contextmenu', function(e){ if (cardFrom(e.target)) e.preventDefault(); }, true);
  // ---- copiar / colar (código e convite da sala)
  function fallbackCopy(text){
    const ta = D.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', '');
    ta.style.position = 'fixed'; ta.style.top = '-1000px'; ta.style.opacity = '0'; D.body.appendChild(ta);
    ta.select(); ta.setSelectionRange(0, text.length); let ok = false;
    try { ok = D.execCommand('copy'); } catch (err) {}
    D.body.removeChild(ta); return ok;
  }
  function flashDone(btn){ btn.classList.add('done'); W.setTimeout(function(){ btn.classList.remove('done'); }, 1600); }
  const canRead = !!(W.isSecureContext && W.navigator.clipboard && W.navigator.clipboard.readText);
  if (!canRead) D.documentElement.classList.add('no-clip-read');
  D.addEventListener('click', function(e){
    const c = e.target.closest && e.target.closest('[data-copy]');
    if (c) {
      e.preventDefault(); const text = c.getAttribute('data-copy');
      if (W.isSecureContext && W.navigator.clipboard && W.navigator.clipboard.writeText) {
        W.navigator.clipboard.writeText(text).then(function(){ flashDone(c); }, function(){ if (fallbackCopy(text)) flashDone(c); });
      } else if (fallbackCopy(text)) { flashDone(c); }
      return;
    }
    const pb = e.target.closest && e.target.closest('[data-paste]');
    if (pb && canRead) {
      e.preventDefault();
      W.navigator.clipboard.readText().then(function(t){
        const inp = D.querySelector(pb.getAttribute('data-paste')); if (!inp) return;
        const setter = Object.getOwnPropertyDescriptor(W.HTMLInputElement.prototype, 'value').set;
        setter.call(inp, (t || '').trim()); inp.dispatchEvent(new Event('input', {bubbles: true})); inp.focus();
      }, function(){ D.documentElement.classList.add('no-clip-read'); });
    }
  });
  // seletor de personagem em faixa rolável (celular): mostra o escolhido sem o usuário procurar
  function revealAvatar(){
    D.querySelectorAll('[class*="st-key-avpick_"] [role="radiogroup"]').forEach(function(g){
      if (g.scrollWidth <= g.clientWidth + 4) return;
      const sel = g.querySelector('[data-selected="true"]'); if (!sel) return;
      const k = sel.textContent; if (g.dataset.revealed === k) return;
      g.dataset.revealed = k;
      const item = sel.parentElement || sel;
      const ir = item.getBoundingClientRect(), gr = g.getBoundingClientRect();
      g.scrollLeft = Math.max(0, g.scrollLeft + ir.left - gr.left - (g.clientWidth - ir.width) / 2);
    });
  }
  W.setInterval(function(){ if (cur && !cur.isConnected) hide(); revealAvatar(); }, 400);
})();
"""

# Script do iframe (st.iframe / components.html): instala os motores de som e de
# visualização na página PAI (mesma origem), para que sobrevivam às trocas do
# iframe; o áudio é desbloqueado pelo primeiro clique em qualquer lugar do app.
LOADER = r"""<!doctype html><html><body><script>
(function(){
  var W = window;
  try { if (window.parent && window.parent !== window && window.parent.document) W = window.parent; } catch (e) { W = window; }
  function install(code, flag){
    if (W[flag]) return;
    try { var tag = W.document.createElement('script'); tag.textContent = code; W.document.head.appendChild(tag); } catch (e) {}
  }
  install(__ENGINE__, '__unoSfx');
  install(__PREVIEW__, '__unoPreview');
  if (!W.__unoSfx) { W = window; (new Function(__ENGINE__))(); }
  W.__unoSfx.muted = __MUTED__;
  W.__unoSfx.play(__LIST__, __SEQ__);
  try { if (W.__unoMusic && W.__unoMusic.duck) W.__unoMusic.duck(__LIST__, __SEQ__); } catch (e) {}  // música abaixa
})();
</script></body></html>"""

SOUND_NAMES = ["play", "draw", "pass", "skip", "reverse", "draw2", "wild4", "alarm", "wild", "uno",
               "denounce", "ding", "turn", "shuffle", "deal", "win", "fanfare", "defeat", "portal",
               "arrive", "depart", "b_red", "b_green", "b_blue", "b_yellow"]


def sound_script(names: list[str], seq: int, muted: bool = False) -> str:
    """Documento HTML que toca ``names`` uma única vez por ``seq`` (crescente)."""
    names = [n for n in names if n in SOUND_NAMES]
    return (LOADER.replace("__ENGINE__", json.dumps(SOUND_ENGINE))
            .replace("__PREVIEW__", json.dumps(PREVIEW_ENGINE))
            .replace("__MUTED__", "true" if muted else "false")
            .replace("__LIST__", json.dumps(names))
            .replace("__SEQ__", str(int(seq))))


def sounds_for(events: list[dict], my_turn_started: bool, me: str | None = None) -> list[str]:
    out = []
    for ev in events:
        s = SOUND_FOR.get(ev["type"])
        if me is not None and ev["type"] in ("round_over", "game_over") and ev.get("player") != me:
            s = "defeat"
        if s and (not out or out[-1] != s):
            out.append(s)
    if my_turn_started:
        out.append("turn")
    return out[-4:]


__all__ = ["fx_push", "fx_current", "fx_seen", "fx_forget", "sfx_queue", "roster", "roster_diff",
           "arrival_html", "departure_html", "portal_html", "pick_fx", "fx_html", "fx_seconds_for",
           "sound_script", "sounds_for", "SOUND_NAMES", "SOUND_ENGINE", "PREVIEW_ENGINE"]
