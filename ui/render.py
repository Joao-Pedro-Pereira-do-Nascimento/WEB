"""Construção de HTML (assentos, montes, cartas, bestiário, ranking, regras)."""

from __future__ import annotations

import html

from game import engine as E
from game.cards import BIOMES, CHARACTERS, back_svg, card_info, card_svg, card_tooltip, gallery

from .icons import avatar_svg, icon
from .logo import logo_html  # noqa: F401  (reexportado: V.logo_html)

esc = html.escape


def card_data_attrs(card: dict) -> str:
    """Textos da carta em data-* (lidos pela visualização ampliada)."""
    info = card_info(card)
    return " ".join(f'data-{k}="{esc(v, quote=True)}"' for k, v in info.items())


def card_html(card: dict, cls: str = "", style: str = "", pill: str = "") -> str:
    label = esc(card_tooltip(card).replace("\n", " — "), quote=True)
    pill_html = f'<span class="pill">{pill}</span>' if pill else ""
    live = " live" if card["kind"] != "number" else ""
    return (f'<div class="uno-card{live} {cls}" style="{style}" aria-label="{label}" {card_data_attrs(card)}>'
            f'{card_svg(card)}{pill_html}</div>')


def avatar(player: dict, dot: str = "", size: int = 38) -> str:
    dot_html = f'<span class="dot {dot}"></span>' if dot else ""
    return f'<div class="avatar">{avatar_svg(player.get("avatar", ""), player.get("name", ""), size)}{dot_html}</div>'


def seat_html(player: dict, game: dict, online: bool, is_turn: bool, is_host: bool, is_me: bool) -> str:
    pid = player["id"]
    n = len(game["hands"].get(pid, []))
    shown = min(n, 9)
    # versos em CSS puro (bem mais leve que SVG: a mesa é redesenhada a cada ~1 s)
    fan = "".join(
        f'<div class="mini" style="transform:rotate({(i - shown / 2) * 6:.0f}deg)"></div>'
        for i in range(shown))
    more = f'<span class="more">+{n - shown}</span>' if n > shown else ""
    if player["bot"]:
        dot, status = "bot", "bot"
    elif player.get("autopilot"):
        dot, status = "bot", "bot no lugar" if not player.get("left") else "saiu (bot)"
    else:
        dot, status = ("on", "online") if online else ("off", "offline")
        if player.get("auto_play"):
            status += " · automático"
    crown = f' <span class="badge-host" title="Anfitrião">{icon("crown", 15)}</span>' if is_host else ""
    uno = '<span class="badge-uno">UNO!</span>' if n == 1 else ""
    you = " (você)" if is_me else ""
    score = game["scores"].get(pid, 0)
    return f"""<div class="seat {'turn' if is_turn else ''}">{uno}
<div class="top">{avatar(player, dot)}
<div><div class="nm">{esc(player['name'])}{you}{crown}</div>
<div class="sub">{n} carta{'s' if n != 1 else ''} · {score} pts · {status}</div></div></div>
<div class="fan">{fan}{more}</div></div>"""


def seats_html(room: dict, me_id: str, presence_online: set[str]) -> str:
    game = room["game"]
    order = game["players"]
    # começa por mim e segue na ordem da mesa
    k = order.index(me_id) if me_id in order else 0
    seq = order[k:] + order[:k]
    actor = E.whose_action(game)
    by_id = {p["id"]: p for p in room["players"]}
    out = []
    for pid in seq:
        if pid == me_id:
            continue
        p = by_id[pid]
        out.append(seat_html(p, game, pid in presence_online, pid == actor, pid == room["host"], False))
    return f'<div class="seats">{"".join(out)}</div>'


def deck_html(game: dict) -> str:
    n = len(game["deck"])
    stacks = "".join(f'<div class="stack">{back_svg()}</div>' for _ in range(3 if n > 2 else max(n, 1)))
    return f'<div class="pile deck">{stacks}<div class="count">monte: {n}</div></div>'


def discard_html(game: dict, animate: bool, from_me: bool, seq: int) -> str:
    top = game["discard"][-1]
    under = game["discard"][-2] if len(game["discard"]) > 1 else None
    cur = BIOMES.get(game["color"] or "", {"hex": "#ffffff"})["hex"]
    r = ((seq * 37) % 17) - 8
    under_html = f'<div class="under">{card_svg(under)}</div>' if under else ""
    cls = "topc fly-in" + (" from-me" if from_me else "") if animate else "topc"
    fx = f"--fx:{((seq * 53) % 120) - 60}px;" if animate else ""
    return (f'<div class="pile discard" style="--cur:{cur}" data-seq="{seq}"><div class="ring"></div>{under_html}'
            f'<div class="{cls}" style="--r:{r}deg;{fx}">{card_html(top, "topcard")}</div>'
            f'<div class="count">descarte: {len(game["discard"])}</div></div>')


def status_html(room: dict, me_id: str) -> str:
    game = room["game"]
    by_id = {p["id"]: p for p in room["players"]}
    actor = E.whose_action(game)
    cur = game["color"]
    color_txt = (f'{icon(BIOMES[cur]["icon"], 15)} {BIOMES[cur]["name"]}' if cur else "a escolher")
    sw = (f'<span class="swatch" style="background:{BIOMES[cur]["hex"]};color:{BIOMES[cur]["hex"]};width:18px;height:18px"></span> '
          if cur else "")
    arrow = (f'<span class="direction" title="sentido horário">{icon("cw", 44)}</span>' if game["direction"] == 1
             else f'<span class="direction ccw" title="sentido anti-horário">{icon("ccw", 44)}</span>')
    if game["status"] != "playing":
        big = '<div class="big">Rodada encerrada</div>'
    elif actor == me_id:
        pend = game.get("pending")
        msg = "SUA VEZ!"
        if pend and pend["type"] == "wild4":
            msg = "+4 em você! Aceita ou desafia?"
        elif pend and pend["type"] == "choose_color":
            msg = "Escolha a cor inicial"
        elif pend and pend["type"] == "drawn":
            msg = "Jogue a carta comprada ou passe"
        big = f'<div class="big me">{msg}</div>'
    else:
        big = f'<div class="big">Vez de {esc(by_id[actor]["name"])}</div>'
    return (f'<div class="status">{arrow}{big}<div class="small">{sw}cor da mesa: {color_txt}</div>'
            f'<div class="small">rodada {game["round"]} · '
            f'{"meta " + str(game["target"]) + " pts" if game["target"] else "rodada única"}</div></div>')


def log_html(events: list[dict], limit: int = 16) -> str:
    rows = [f"<div>{esc(ev['text'])}</div>" for ev in reversed(events[-limit:]) if ev.get("text")]
    return f'<div class="log">{"".join(rows)}</div>'


def code_tiles(code: str) -> str:
    return '<div class="code-tiles">' + "".join(f"<span>{c}</span>" for c in code) + "</div>"


def copy_button(text: str, label: str, ico: str = "link") -> str:
    """Botão (HTML) que copia ``text``; o clique é tratado pelo script injetado na página
    (clipboard API, com plano B via textarea + execCommand em http://IP-da-rede)."""
    return (f'<button type="button" class="share-btn" data-copy="{esc(text, quote=True)}">'
            f'{icon(ico, 16)}<span class="lbl">{esc(label)}</span><span class="ok">Copiado</span></button>')


def paste_button(target_selector: str) -> str:
    """Botão "Colar" (lê a área de transferência). Onde o navegador não deixa (http fora do
    localhost), o botão some e aparece a dica de colar com o teclado / segurando o dedo."""
    return (f'<button type="button" class="share-btn paste-btn" data-paste="{esc(target_selector, quote=True)}">'
            f'{icon("scroll", 16)}<span class="lbl">Colar</span></button>'
            f'<span class="paste-hint">Ctrl+V ou segure e cole</span>')


def room_header(room: dict, invite_link: str) -> str:
    """Nome da sala em destaque; código e botões de compartilhar como informação secundária."""
    code = room["code"]
    title = room.get("name") or code
    return (f'<div class="room-head"><div class="room-name">{esc(title)}</div>'
            f'<div class="room-eyebrow">código da sala — passe para os amigos</div>{code_tiles(code)}'
            f'<div class="share-row">{copy_button(code, "Copiar código", "cards")}'
            f'{copy_button(invite_link, "Copiar convite", "link")}</div></div>')


def bestiary_html() -> str:
    biomes = "".join(
        f'<div class="biome" style="background:linear-gradient(135deg,{b["hex"]},#1b1030)">'
        f'<b>{icon(b["icon"], 18)} {b["name"]}</b><br>{b["desc"]}</div>' for b in BIOMES.values())
    items = []
    for it in gallery():
        ch = CHARACTERS[it["char"]]
        power = f'<p class="power">{esc(ch["power"])}</p>' if ch.get("power") else ""
        items.append(
            f'<div class="beast"><div class="art">{card_html(it["card"])}</div><div>'
            f'<div class="role">{esc(it["role"])}</div><h4>{esc(ch["name"])}</h4>'
            f'<p>{esc(ch["blurb"])}</p>{power}</div></div>')
    return f'<div class="biomes">{biomes}</div><div class="bestiary">{"".join(items)}</div>'


def _medal(rank: int) -> str:
    colors = {1: ("#fff3bf", "#e9c46a", "#8a5a12"), 2: ("#ffffff", "#c9ced6", "#6b7280"), 3: ("#ffd9b0", "#cd7f32", "#6b3a12")}
    a, b, c = colors[rank]
    return (f'<svg class="medal" viewBox="0 0 40 48" width="40" height="48" aria-hidden="true">'
            f'<path d="M10 2h8l4 14h-8zM30 2h-8l-4 14h8z" fill="#7a1420" stroke="#2a0a0a" stroke-width="1.5"/>'
            f'<defs><radialGradient id="md{rank}" cx=".35" cy=".3"><stop offset="0" stop-color="{a}"/><stop offset=".6" stop-color="{b}"/>'
            f'<stop offset="1" stop-color="{c}"/></radialGradient></defs>'
            f'<circle cx="20" cy="31" r="14" fill="url(#md{rank})" stroke="#2a1804" stroke-width="2.5"/>'
            f'<circle cx="20" cy="31" r="9.5" fill="none" stroke="{c}" stroke-width="1.2" stroke-dasharray="2 2"/>'
            f'<text x="20" y="36" text-anchor="middle" font-family="Cinzel, serif" font-weight="700" font-size="14" fill="#2a1804">{rank}</text></svg>')


def ranking_html(rows: list[dict], me_key: str = "", online: bool = False) -> str:
    badge = (f'<span class="rank-badge {"on" if online else "off"}">{icon("eye" if online else "book", 14)} '
             f'{"Ranking online" if online else "Ranking local"}</span>')
    if not rows:
        return (f'<div class="panel">{badge}<p>Ninguém terminou uma partida ainda. '
                f'Jogue a primeira e entre para a história!</p></div>')
    podium = []
    for pos in (2, 1, 3):
        if len(rows) < pos:
            continue
        r = rows[pos - 1]
        mine = " me" if me_key and r.get("key") == me_key else ""
        crown = f'<div class="podium-crown">{icon("crown", 34)}</div>' if pos == 1 else ""
        podium.append(
            f'<div class="podium-step p{pos}{mine}">{crown}{_medal(pos)}'
            f'<div class="podium-name">{esc(str(r.get("name", "?")))}</div>'
            f'<div class="podium-wins">{r.get("wins", 0)} vitória{"s" if r.get("wins", 0) != 1 else ""}</div>'
            f'<div class="podium-base">{pos}º</div></div>')
    body = []
    for i, r in enumerate(rows[:50]):
        games = r.get("games", 0) or 0
        rate = f"{100 * r.get('wins', 0) / games:.0f}%" if games else "–"
        mine = ' class="me"' if me_key and r.get("key") == me_key else ""
        you = ' <span class="you-tag">você</span>' if mine else ""
        body.append(
            f"<tr{mine}><td>{i + 1}</td><td><b>{esc(str(r.get('name', '?')))}</b>{you}</td>"
            f"<td>{r.get('wins', 0)}</td><td>{games}</td><td>{rate}</td><td>{r.get('points', 0)}</td>"
            f"<td>{r.get('cards_played', 0)}</td><td>{r.get('uno_shouts', 0)}</td><td>{r.get('denounces', 0)}</td>"
            f"<td>{r.get('penalties', 0)}</td></tr>")
    return (f'<div class="panel rank-panel">{badge}<div class="podium">{"".join(podium)}</div>'
            '<div class="table-scroll"><table class="rank"><tr><th>#</th><th>Jogador</th><th>Vitórias</th>'
            '<th>Partidas</th><th>Aprov.</th><th>Pontos</th><th>Cartas jogadas</th><th>UNO!</th><th>Denúncias</th>'
            '<th>Punições</th></tr>' + "".join(body) + "</table></div></div>")


RULES_MD = """
### Objetivo
Ser o primeiro a **ficar sem cartas**. Quem esvazia a mão ganha a rodada e soma os pontos das cartas que sobraram com os adversários. Na *rodada única* quem bater primeiro vence; com meta (100/200/500), joga-se rodadas até alguém atingir a pontuação.

### O baralho (108 cartas)
- **4 cores = 4 biomas:** Fogo (vermelho) · Mata (verde) · Rios (azul) · Cerrado (amarelo).
- Por cor: um **0**, dois de cada **1–9**, dois **Pular** (Saci), dois **Inverter** (Curupira), dois **+2** (Cuca).
- **4 Coringas** (Iara) e **4 Coringas +4** (Mula sem Cabeça).

### Na sua vez
1. Jogue uma carta que combine com a do topo do descarte na **cor**, no **número** ou no **símbolo** — ou um coringa.
2. Se não puder (ou não quiser), **compre 1 carta**. Se ela servir, você pode jogá-la na hora; se não, a vez passa.
3. Quando o monte acaba, o descarte (menos a carta do topo) é embaralhado e vira o novo monte.

### Cartas especiais
| Carta | Personagem | Efeito |
|---|---|---|
| Pular | Saci | o próximo perde a vez |
| Inverter | Curupira | inverte o sentido (com 2 jogadores, vale como Pular) |
| +2 | Cuca | o próximo compra 2 e perde a vez |
| Coringa | Iara | você escolhe a nova cor |
| +4 | Mula sem Cabeça | escolhe a cor; o próximo compra 4 e perde a vez — **mas pode desafiar**: se você tinha carta da cor da mesa, *você* compra 4; se não tinha, o desafiante compra 6 |

### UNO!
Ao ficar com **1 carta**, aperte **UNO!** (antes de jogar a penúltima ou logo depois). Se esquecer, qualquer adversário pode **denunciar** antes do próximo jogador agir — e você compra **+2**.

### Pontuação
Números valem o próprio valor · Pular/Inverter/+2 valem 20 · Coringas valem 50.

### Dicas
- **Ver uma carta de perto:** passe o mouse sobre ela (computador) ou segure o dedo (celular).
- **Reconexão:** se a página fechar, abra o *link de reconexão* da sala para voltar ao mesmo lugar, com as mesmas cartas.
- **Sons:** os navegadores só liberam o áudio depois do primeiro clique na página.
- **Meta da partida:** o anfitrião escolhe na sala (rodada única ou 100/200/500 pontos).

### Primeira carta virada
Se for +4, volta ao monte. Coringa: o primeiro jogador escolhe a cor. Pular, Inverter e +2 valem normalmente para o primeiro jogador.
"""
