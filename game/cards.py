"""Personagens do folclore brasileiro e a arte SVG (gerada em código) de cada carta.

Nenhum arquivo de imagem externo: cada carta é um SVG inline com gradientes,
padrões do bioma (cor) e uma ilustração estilizada do personagem.
"""

from __future__ import annotations

import html
import math
from functools import lru_cache

# --------------------------------------------------------------------------- dados

BIOMES = {
    "red": {"name": "Fogo", "icon": "fire", "hex": "#e8392b",
            "desc": "Fogueiras, queimadas e as criaturas que brilham na noite."},
    "green": {"name": "Mata", "icon": "leaf", "hex": "#1fa65a",
              "desc": "A floresta fechada e seus guardiões encantados."},
    "blue": {"name": "Rios", "icon": "wave", "hex": "#1f7be0",
             "desc": "Rios, igarapés e os seres que moram nas águas."},
    "yellow": {"name": "Cerrado", "icon": "sun", "hex": "#f2b311",
               "desc": "Campos dourados, estradas de terra e festas do interior."},
}

PAL = {
    "red": {"a": "#ff8a3d", "b": "#c0162a", "dark": "#5c0710", "light": "#ffe7cf", "accent": "#ffd23f"},
    "green": {"a": "#63e08f", "b": "#0f6e3c", "dark": "#06331c", "light": "#e2ffdc", "accent": "#c4ff5c"},
    "blue": {"a": "#55c8ff", "b": "#0b47a8", "dark": "#041f4f", "light": "#dff5ff", "accent": "#7ff0ff"},
    "yellow": {"a": "#ffe45e", "b": "#e5850a", "dark": "#6b3a00", "light": "#fff8d6", "accent": "#ff9d2e"},
    "wild": {"a": "#3b2b70", "b": "#120c26", "dark": "#08051a", "light": "#f4ecff", "accent": "#ffd23f"},
}

CHARACTERS = {
    "saci": {
        "name": "Saci-Pererê", "short": "Saci",
        "blurb": "Menino travesso de uma perna só, com gorro vermelho mágico e cachimbo. "
                 "Some dentro de redemoinhos de vento, esconde objetos e trança a crina dos cavalos.",
        "power": "PULAR — o Saci some no redemoinho e o próximo jogador perde a vez.",
    },
    "curupira": {
        "name": "Curupira", "short": "Curupira",
        "blurb": "Guardião das matas, de cabelos de fogo e pés virados para trás: suas pegadas "
                 "enganam os caçadores, que andam em círculos sem nunca encontrá-lo.",
        "power": "INVERTER — como as pegadas dele, o sentido do jogo vira ao contrário "
                 "(com 2 jogadores, vale como Pular).",
    },
    "cuca": {
        "name": "Cuca", "short": "Cuca",
        "blurb": "Bruxa com cabeça de jacaré que mexe poções no caldeirão e assusta quem não quer dormir. "
                 "Ficou famosa no Sítio do Picapau Amarelo, de Monteiro Lobato.",
        "power": "+2 — a poção da Cuca faz o próximo jogador comprar 2 cartas e perder a vez.",
    },
    "iara": {
        "name": "Iara", "short": "Iara",
        "blurb": "A Mãe-d'Água: sereia dos rios amazônicos que encanta pescadores com seu canto "
                 "e os leva para o fundo das águas.",
        "power": "CORINGA — seu canto muda a cor da mesa para a que você escolher.",
    },
    "mula": {
        "name": "Mula sem Cabeça", "short": "Mula",
        "blurb": "Mula que solta fogo pelo pescoço, no lugar da cabeça, e galopa nas noites de "
                 "quinta para sexta-feira, relinchando e soltando faíscas pelos cascos.",
        "power": "+4 — o próximo compra 4 e perde a vez; você escolhe a cor. Ele pode desafiar "
                 "se achar que você tinha a cor da mesa!",
    },
    "vitoria_regia": {
        "name": "Vitória-régia", "short": "Vitória-régia",
        "blurb": "Lenda tupi da jovem Naiá, que se apaixonou pela Lua (Jaci) e foi transformada "
                 "na grande flor das águas que só se abre à noite.",
    },
    "boto": {
        "name": "Boto-cor-de-rosa", "short": "Boto",
        "blurb": "Nas festas da Amazônia, o boto vira um rapaz elegante de chapéu branco "
                 "(para esconder o furo na cabeça) e encanta as moças nos bailes.",
    },
    "boitata": {
        "name": "Boitatá", "short": "Boitatá",
        "blurb": "Cobra de fogo de olhos enormes que protege os campos de quem os incendeia. "
                 "O nome vem do tupi: mboi (cobra) + tatá (fogo).",
    },
    "lobisomem": {
        "name": "Lobisomem", "short": "Lobisomem",
        "blurb": "Em noite de lua cheia, o sétimo filho homem vira lobo e corre pelas "
                 "encruzilhadas até o galo cantar.",
    },
    "caipora": {
        "name": "Caipora", "short": "Caipora",
        "blurb": "Protetora dos bichos da floresta, montada num porco-do-mato. Faz os caçadores "
                 "se perderem — mas pode ser agradada com um presente de fumo.",
    },
    "mapinguari": {
        "name": "Mapinguari", "short": "Mapinguari",
        "blurb": "Gigante peludo da Amazônia, com um olho só na testa e uma boca enorme na "
                 "barriga. Seu grito faz a mata inteira silenciar.",
    },
    "negrinho": {
        "name": "Negrinho do Pastoreio", "short": "Negrinho",
        "blurb": "Menino escravizado dos pampas que, depois de injustiçado, reapareceu montado "
                 "no cavalo baio. Acenda uma vela e ele ajuda a encontrar o que se perdeu.",
    },
    "matinta": {
        "name": "Matinta Pereira", "short": "Matinta",
        "blurb": "Velha que vira pássaro agourento e assobia \"fiiiu\" na noite. Para o assobio "
                 "parar, prometa fumo ou café — no dia seguinte ela vem buscar.",
    },
    "boi_bumba": {
        "name": "Boi-bumbá", "short": "Boi-bumbá",
        "blurb": "O boi enfeitado de fitas e bordados, estrela de Parintins e do Bumba-meu-boi: "
                 "morre e ressuscita ao som dos tambores.",
    },
    "cobra_grande": {
        "name": "Cobra-Grande", "short": "Boiúna",
        "blurb": "A Boiúna, serpente gigante dos rios amazônicos, com olhos que brilham como "
                 "faróis de barco. Dizem que formou os igarapés ao rastejar.",
    },
}

NUMBER_CHARS = ["vitoria_regia", "boto", "boitata", "lobisomem", "caipora",
                "mapinguari", "negrinho", "matinta", "boi_bumba", "cobra_grande"]
KIND_CHARS = {"skip": "saci", "reverse": "curupira", "draw2": "cuca", "wild": "iara", "wild4": "mula"}
KIND_LABEL = {"skip": "Pular", "reverse": "Inverter", "draw2": "+2", "wild": "Coringa", "wild4": "+4"}


def character_of(card: dict) -> str:
    if card["kind"] == "number":
        return NUMBER_CHARS[int(card["value"])]
    return KIND_CHARS[card["kind"]]


def card_tooltip(card: dict) -> str:
    ch = CHARACTERS[character_of(card)]
    head = ch["name"]
    if card["kind"] == "number":
        head += f" — {BIOMES[card['color']]['name']} {card['value']}"
    elif card["color"] in BIOMES:
        head += f" — {BIOMES[card['color']]['name']}"
    text = f"{head}\n{ch['blurb']}"
    if ch.get("power"):
        text += f"\n{ch['power']}"
    return text


EFFECT_TEXT = {
    "skip": "Pular: o próximo jogador perde a vez.",
    "reverse": "Inverter: o sentido do jogo vira ao contrário (com 2 jogadores, vale como Pular).",
    "draw2": "+2: o próximo jogador compra 2 cartas e perde a vez.",
    "wild": "Coringa: você escolhe a nova cor da mesa. Pode ser jogado sobre qualquer carta.",
    "wild4": "Coringa +4: escolha a cor; o próximo compra 4 e perde a vez — mas pode desafiar se achar que você tinha a cor da mesa.",
}


def card_info(card: dict) -> dict:
    """Textos legíveis da carta (para a visualização ampliada)."""
    ch = CHARACTERS[character_of(card)]
    kind = card["kind"]
    biome = BIOMES.get(card["color"])
    if kind == "number":
        v = card["value"]
        sub = f"{biome['name']} · {v}"
        effect = (f"Carta {v} do bioma {biome['name']}: jogue sobre a mesma cor ou o mesmo número. "
                  f"Vale {v} ponto{'s' if v != 1 else ''}.")
    else:
        sub = KIND_LABEL[kind] + (f" · {biome['name']}" if biome else " · todas as cores")
        pts = 50 if kind in ("wild", "wild4") else 20
        effect = f"{EFFECT_TEXT[kind]} Vale {pts} pontos."
    return {"name": ch["name"], "sub": sub, "effect": effect, "blurb": ch["blurb"]}


# --------------------------------------------------------------------------- peças SVG

SKIN_DARK = "#6b3e26"
SKIN = "#b9773f"
SKIN_LIGHT = "#e5ad73"


def _defs(color: str) -> str:
    p = PAL[color]
    return f"""
<defs>
 <linearGradient id="bg-{color}" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{p['a']}"/><stop offset="1" stop-color="{p['b']}"/>
 </linearGradient>
 <radialGradient id="ov-{color}" cx=".5" cy=".42" r=".65">
  <stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="{p['light']}"/>
  <stop offset="1" stop-color="{p['a']}" stop-opacity=".85"/>
 </radialGradient>
 <linearGradient id="fire-{color}" x1="0" y1="1" x2="0" y2="0">
  <stop offset="0" stop-color="#d62000"/><stop offset=".5" stop-color="#ff8c1a"/>
  <stop offset="1" stop-color="#fff07a"/>
 </linearGradient>
 <radialGradient id="glow-{color}">
  <stop offset="0" stop-color="#fffbe0" stop-opacity="1"/><stop offset=".45" stop-color="#ffd86b" stop-opacity=".7"/>
  <stop offset="1" stop-color="#ffb000" stop-opacity="0"/>
 </radialGradient>
 <clipPath id="clip-in"><rect x="6" y="6" width="108" height="168" rx="9"/></clipPath>
</defs>"""


def _biome_pattern(color: str) -> str:
    """Decoração de fundo de acordo com o bioma da cor."""
    if color == "red":  # chamas
        out = []
        for i, x in enumerate(range(0, 130, 18)):
            h = 22 + (i % 3) * 8
            out.append(f'<path d="M{x} 176 Q{x + 3} {176 - h} {x + 9} {176 - h - 8} '
                       f'Q{x + 11} {176 - h + 6} {x + 18} 176 Z" fill="#ffd23f" opacity=".28"/>')
            out.append(f'<path d="M{x + 4} 4 Q{x + 7} {4 + h * .6} {x + 12} {4 + h * .8} '
                       f'Q{x + 13} {4 + h * .4} {x + 18} 4 Z" fill="#5c0710" opacity=".25"/>')
        for x, y in [(18, 60), (100, 40), (95, 120), (22, 130), (60, 22)]:
            out.append(f'<circle cx="{x}" cy="{y}" r="1.6" fill="#fff07a" opacity=".8"/>')
        return "".join(out)
    if color == "green":  # folhas
        out = []
        spots = [(14, 20, 30), (104, 26, -40), (12, 92, 70), (108, 88, -60), (20, 158, 20),
                 (102, 156, -20), (60, 14, 90), (60, 170, 80), (34, 46, -30), (88, 136, 40)]
        for x, y, a in spots:
            out.append(f'<g transform="rotate({a} {x} {y})"><ellipse cx="{x}" cy="{y}" rx="9" ry="4" '
                       f'fill="#06331c" opacity=".3"/><line x1="{x - 8}" y1="{y}" x2="{x + 8}" y2="{y}" '
                       f'stroke="#c4ff5c" stroke-width=".6" opacity=".5"/></g>')
        return "".join(out)
    if color == "blue":  # ondas
        out = []
        for y in range(16, 180, 22):
            d = f"M0 {y} " + " ".join(f"q7.5 -6 15 0 t15 0" for _ in range(4))
            out.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="1.6" opacity=".22"/>')
        for x, y, r in [(18, 40, 3), (100, 70, 2.4), (24, 120, 2), (96, 150, 3.2), (70, 20, 2)]:
            out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="#dff5ff" stroke-width=".8" opacity=".6"/>')
        return "".join(out)
    if color == "yellow":  # sol e capim do cerrado
        out = ['<g opacity=".3">']
        for i in range(14):
            ang = math.radians(i * 360 / 14)
            x2, y2 = 104 + 70 * math.cos(ang), 16 + 70 * math.sin(ang)
            out.append(f'<line x1="104" y1="16" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#fff8d6" stroke-width="3"/>')
        out.append('</g><circle cx="104" cy="16" r="14" fill="#fff8d6" opacity=".55"/>')
        for x in range(4, 120, 10):
            out.append(f'<path d="M{x} 176 l3 -16 l2 16 l3 -12 l2 12 Z" fill="#6b3a00" opacity=".3"/>')
        return "".join(out)
    # coringa: quatro biomas em quadrantes
    q = [("red", 0, 0), ("blue", 60, 0), ("yellow", 0, 90), ("green", 60, 90)]
    out = [f'<rect x="{x}" y="{y}" width="60" height="90" fill="{BIOMES[c]["hex"]}" opacity=".55"/>'
           for c, x, y in q]
    for x, y in [(16, 24), (100, 30), (14, 150), (104, 156), (60, 12), (24, 88), (98, 92)]:
        out.append(f'<path d="M{x} {y - 4} l1.2 2.8 l3 .2 l-2.3 2 l.8 3 l-2.7 -1.6 l-2.7 1.6 l.8 -3 '
                   f'l-2.3 -2 l3 -.2 Z" fill="#fff" opacity=".85"/>')
    return "".join(out)


def _corner_symbol(card: dict, size: float = 1.0) -> str:
    """Símbolo do canto (número ou ícone desenhado), centrado em (0,0)."""
    kind = card["kind"]
    stroke = 'stroke="#1b1030" stroke-width="2.6" paint-order="stroke"'
    if kind == "number":
        return (f'<text x="0" y="7" text-anchor="middle" font-family="Bungee, Impact, sans-serif" '
                f'font-size="{19 * size}" fill="#fff" {stroke}>{card["value"]}</text>')
    if kind in ("draw2", "wild4"):
        label = "+2" if kind == "draw2" else "+4"
        return (f'<text x="0" y="6" text-anchor="middle" font-family="Bungee, Impact, sans-serif" '
                f'font-size="{14 * size}" fill="#fff" {stroke}>{label}</text>')
    if kind == "skip":
        return ('<g><circle r="7.5" fill="none" stroke="#1b1030" stroke-width="5"/>'
                '<circle r="7.5" fill="none" stroke="#fff" stroke-width="2.6"/>'
                '<line x1="-5.2" y1="5.2" x2="5.2" y2="-5.2" stroke="#1b1030" stroke-width="5"/>'
                '<line x1="-5.2" y1="5.2" x2="5.2" y2="-5.2" stroke="#fff" stroke-width="2.6"/></g>')
    if kind == "reverse":
        arrow = ('<path d="M-7 -2 A7 7 0 0 1 5 -5" fill="none" stroke="{s}" stroke-width="{w}"/>'
                 '<path d="M7 2 A7 7 0 0 1 -5 5" fill="none" stroke="{s}" stroke-width="{w}"/>'
                 '<path d="M3 -9 L8 -4 L1 -3 Z" fill="{s}"/><path d="M-3 9 L-8 4 L-1 3 Z" fill="{s}"/>')
        return "<g>" + arrow.format(s="#1b1030", w=5) + arrow.format(s="#fff", w=2.6) + "</g>"
    # coringa: mini roda de cores
    parts = []
    for i, c in enumerate(["red", "blue", "green", "yellow"]):
        a0, a1 = math.radians(i * 90 - 90), math.radians(i * 90)
        parts.append(f'<path d="M0 0 L{8 * math.cos(a0):.2f} {8 * math.sin(a0):.2f} '
                     f'A8 8 0 0 1 {8 * math.cos(a1):.2f} {8 * math.sin(a1):.2f} Z" fill="{BIOMES[c]["hex"]}"/>')
    return '<g><circle r="9" fill="#1b1030"/>' + "".join(parts) + '<circle r="8" fill="none" stroke="#fff" stroke-width="1.4"/></g>'


# --------------------------------------------------------------------------- personagens
# Cada função desenha o emblema dentro da área do oval central (~x 22..98, y 30..145).

def _eyes(x1, x2, y, look=0.6, r=2.6):
    return (f'<circle cx="{x1}" cy="{y}" r="{r}" fill="#fff"/><circle cx="{x2}" cy="{y}" r="{r}" fill="#fff"/>'
            f'<circle cx="{x1 + look}" cy="{y}" r="{r * .48}" fill="#1b1030"/>'
            f'<circle cx="{x2 + look}" cy="{y}" r="{r * .48}" fill="#1b1030"/>')


def draw_saci(p, c):
    whirl = "".join(
        f'<ellipse cx="{60 + (i % 2) * 4 - 2}" cy="{136 - i * 7}" rx="{7 + i * 5}" ry="{2.6 + i * .9}" '
        f'fill="none" stroke="{p["dark"]}" stroke-width="2" stroke-dasharray="{10 + i * 4} 6" opacity="{.75 - i * .08:.2f}"/>'
        for i in range(6))
    return f"""
<g class="fx-spin">{whirl}</g>
<g class="fx-hop">
 <rect x="57" y="104" width="6" height="24" rx="3" fill="{SKIN_DARK}"/>
 <ellipse cx="63" cy="127" rx="7" ry="3.2" fill="{SKIN_DARK}"/>
 <path d="M47 90 h26 l-3 18 h-20 z" fill="#d62828" stroke="#7a0f0f" stroke-width="1"/>
 <rect x="48" y="72" width="24" height="22" rx="9" fill="{SKIN_DARK}"/>
 <path d="M50 78 q-11 4 -14 16" stroke="{SKIN_DARK}" stroke-width="5.5" fill="none" stroke-linecap="round"/>
 <path d="M70 78 q9 0 11 -8" stroke="{SKIN_DARK}" stroke-width="5.5" fill="none" stroke-linecap="round"/>
 <circle cx="60" cy="60" r="13" fill="{SKIN_DARK}"/>
 {_eyes(55, 65, 58, .8, 3)}
 <path d="M53 65 q7 6 14 0" stroke="#fff" stroke-width="1.8" fill="#fff" stroke-linejoin="round"/>
 <g class="fx-cap"><path d="M46 55 C45 40 62 36 84 26 C77 37 74 47 75 56 Q60 50 46 55 Z" fill="#e01e37" stroke="#8a0a1c" stroke-width="1.2"/>
 <circle cx="84" cy="26" r="3.4" fill="#ff5d73"/></g>
 <rect x="66" y="64" width="16" height="2.6" rx="1.3" fill="#5d3a1a"/>
 <rect x="80" y="57" width="7" height="9" rx="2" fill="#8b5a2b" stroke="#4a2c0f" stroke-width=".8"/>
 <path class="fx-float" d="M84 54 q-5 -5 0 -10 q5 -5 0 -10" stroke="#fff" stroke-width="2" fill="none" opacity=".85" stroke-linecap="round"/>
</g>"""


def _footprint(x, y, angle, fill):
    return (f'<g transform="rotate({angle} {x} {y})"><ellipse cx="{x}" cy="{y}" rx="3.2" ry="5.5" fill="{fill}"/>'
            + "".join(f'<circle cx="{x - 3 + i * 1.5}" cy="{y + 7.2 + (i % 2) * .6}" r="1.1" fill="{fill}"/>' for i in range(5))
            + "</g>")


def draw_curupira(p, c):
    prints = "".join(f'<g class="fx-steps" style="animation-delay:{i * .5:.1f}s">{_footprint(x, y, a, p["dark"])}</g>'
                     for i, (x, y, a) in enumerate([(30, 136, -70), (44, 128, -100), (84, 138, -80)]))
    return f"""
<g class="fx-spin" opacity=".6">
 <path d="M24 92 A36 36 0 0 1 84 58" fill="none" stroke="{p['dark']}" stroke-width="4" stroke-linecap="round"/>
 <path d="M80 50 L90 60 L77 63 Z" fill="{p['dark']}"/>
 <path d="M96 88 A36 36 0 0 1 36 122" fill="none" stroke="{p['dark']}" stroke-width="4" stroke-linecap="round"/>
 <path d="M40 130 L30 120 L43 117 Z" fill="{p['dark']}"/>
</g>
{prints}
<g>
 <path d="M55 104 l-2 20" stroke="{SKIN}" stroke-width="5" stroke-linecap="round"/>
 <path d="M65 104 l2 20" stroke="{SKIN}" stroke-width="5" stroke-linecap="round"/>
 <ellipse cx="48" cy="125" rx="7" ry="3" fill="{SKIN}"/>
 <ellipse cx="62" cy="125" rx="7" ry="3" fill="{SKIN}"/>
 <path d="M44 82 L76 82 L80 108 L74 103 L70 109 L64 103 L60 110 L56 103 L50 109 L46 103 L40 108 Z" fill="#2d8f3c" stroke="#145a22" stroke-width="1.2"/>
 <path d="M47 84 q-10 6 -10 16" stroke="{SKIN}" stroke-width="5" fill="none" stroke-linecap="round"/>
 <path d="M73 84 q10 6 10 16" stroke="{SKIN}" stroke-width="5" fill="none" stroke-linecap="round"/>
 <g class="fx-flicker">
  <path d="M45 66 Q38 44 50 48 Q48 28 60 40 Q66 22 70 42 Q82 32 76 52 Q86 54 75 68 Z" fill="#ff4d1a"/>
  <path d="M50 62 Q47 48 55 50 Q56 38 62 46 Q68 36 68 50 Q76 48 70 62 Z" fill="#ffc23d"/>
 </g>
 <circle cx="60" cy="66" r="11.5" fill="{SKIN}"/>
 {_eyes(56, 65, 65, 1, 2.6)}
 <path d="M56 72 q4 3 9 0" stroke="#5d2a12" stroke-width="1.4" fill="none"/>
 <path d="M40 98 l-6 -4 M80 98 l6 -4" stroke="#145a22" stroke-width="2"/>
</g>"""


def draw_cuca(p, c):
    bubbles = "".join(f'<circle class="fx-float" cx="{x}" cy="{y}" r="{r}" fill="#9dff6a" stroke="#2f7d12" stroke-width=".8" opacity=".9"/>'
                      for x, y, r in [(50, 104, 3), (62, 100, 4), (72, 105, 2.5), (57, 94, 2)])
    teeth = "".join(f'<path d="M{x} 66 l1.6 3 l1.6 -3 Z" fill="#fff"/>' for x in range(73, 92, 3))
    return f"""
<path d="M46 50 Q30 62 34 96 Q40 82 42 74 Q42 92 48 100 Q48 80 52 68 Z" fill="#ffd23f" stroke="#c99a00" stroke-width="1"/>
<path d="M40 112 L46 80 Q60 70 74 80 L80 112 Z" fill="#6a2c91" stroke="#3b1356" stroke-width="1.2"/>
<path d="M46 86 q-8 10 -4 20 M74 86 q8 10 4 20" stroke="#4caf50" stroke-width="4.5" fill="none" stroke-linecap="round"/>
<path d="M44 60 Q44 44 60 44 Q70 44 74 50 L95 55 Q100 60 95 65 L72 69 Q60 76 49 70 Q44 66 44 60 Z" fill="#4caf50" stroke="#1b5e20" stroke-width="1.4"/>
{teeth}
<circle cx="52" cy="47" r="2.2" fill="#2e7d32"/><circle cx="58" cy="45" r="2.2" fill="#2e7d32"/><circle cx="64" cy="46" r="2.2" fill="#2e7d32"/>
<circle class="fx-eyeglow" cx="62" cy="54" r="5" fill="#ffeb3b" stroke="#1b5e20" stroke-width="1"/>
<ellipse cx="62.5" cy="54" rx="1.2" ry="3.6" fill="#111"/>
<circle cx="93" cy="58" r="1.2" fill="#1b5e20"/>
<path d="M50 40 L60 18 L70 40 Z" fill="#3b1356"/><ellipse cx="60" cy="40" rx="16" ry="3.5" fill="#3b1356"/>
<rect x="56" y="34" width="8" height="3" fill="#ffd23f"/>
<path d="M36 112 Q36 136 60 136 Q84 136 84 112 Z" fill="#26263a" stroke="#0e0e18" stroke-width="1.2"/>
<ellipse cx="60" cy="112" rx="24" ry="5" fill="#7CFC00" stroke="#44445a" stroke-width="3"/>
{bubbles}
<path d="M44 132 l-4 8 M76 132 l4 8" stroke="#26263a" stroke-width="3"/>
<path class="fx-flicker" d="M48 142 q4 -8 8 0 q4 -9 8 0 q4 -8 8 0 Z" fill="url(#fire-{c})"/>"""


def draw_iara(p, c):
    wedges = []
    for i, col in enumerate(["red", "blue", "green", "yellow"]):
        a0, a1 = math.radians(i * 90 - 90), math.radians(i * 90)
        wedges.append(f'<path d="M60 78 L{60 + 38 * math.cos(a0):.1f} {78 + 38 * math.sin(a0):.1f} '
                      f'A38 38 0 0 1 {60 + 38 * math.cos(a1):.1f} {78 + 38 * math.sin(a1):.1f} Z" fill="{BIOMES[col]["hex"]}"/>')
    scales = "".join(f'<path class="fx-shimmer" style="animation-delay:{i * .18:.2f}s" d="M{x} {y} q3 3 6 0" stroke="#bffaf0" stroke-width="1.1" fill="none"/>'
                     for i, (x, y) in enumerate([(56, 104), (62, 106), (52, 112), (58, 114), (48, 120), (54, 122)]))
    return f"""
<g class="fx-spin-slow" opacity=".9">{"".join(wedges)}<circle cx="60" cy="78" r="38" fill="none" stroke="#fff" stroke-width="2"/></g>
<circle cx="60" cy="78" r="26" fill="#fff" opacity=".35"/>
<g clip-path="url(#clip-in)"><path class="fx-ripple" d="M-8 134 q8 -6 17 0 t17 0 t17 0 t17 0 t17 0 t17 0 t17 0 t17 0 L128 150 L-8 150 Z" fill="#1f7be0" opacity=".85"/>
<path class="fx-ripple r2" d="M-8 140 q8 -5 17 0 t17 0 t17 0 t17 0 t17 0 t17 0 t17 0 t17 0" fill="none" stroke="#bff6ff" stroke-width="1.2" opacity=".8"/></g>
<g class="fx-sway">
 <path d="M50 52 Q36 70 42 102 Q46 90 48 84 Q46 104 52 112 L68 112 Q74 104 72 84 Q74 90 78 102 Q84 70 70 52 Z" fill="#1a1530"/>
</g>
<path d="M50 96 Q54 118 44 128 Q38 134 28 130 Q38 128 40 120 Q46 108 50 96 Z" fill="#14b8a6"/>
<path d="M50 96 Q66 98 66 110 Q64 122 46 126 Q58 116 50 96 Z" fill="#14b8a6" stroke="#0b6b61" stroke-width="1"/>
{scales}
<path d="M30 130 Q20 122 22 112 Q30 122 36 124 Q34 132 30 130 Z M30 130 Q24 140 14 142 Q22 132 32 128 Z" fill="#2dd4bf" stroke="#0b6b61" stroke-width="1"/>
<path d="M50 78 Q60 72 70 78 L68 98 Q60 102 52 98 Z" fill="{SKIN}"/>
<path d="M50 84 Q55 80 60 86 Q65 80 70 84 L69 90 Q60 94 51 90 Z" fill="#ff8fab" stroke="#d6336c" stroke-width=".8"/>
<circle cx="60" cy="64" r="11" fill="{SKIN}"/>
<path d="M49 62 Q50 48 60 49 Q72 48 72 64 Q66 54 58 55 Q52 56 49 62 Z" fill="#1a1530"/>
<path d="M54 65 q2 2 4 0 M62 65 q2 2 4 0" stroke="#1a1530" stroke-width="1.3" fill="none"/>
<ellipse cx="60" cy="70" rx="2" ry="1.6" fill="#b5172f"/>
<circle cx="70" cy="54" r="3" fill="#ff6fa3"/><circle cx="73" cy="57" r="2.4" fill="#ffc2d9"/><circle cx="70" cy="54" r="1" fill="#ffd23f"/>
<g class="fx-float" fill="#fff" stroke="#1b1030" stroke-width=".6"><ellipse cx="82" cy="65" rx="2.6" ry="2" transform="rotate(-20 82 65)"/><path d="M84.2 64.4 V55 l4 2" fill="none" stroke="#fff" stroke-width="1.2"/></g>
<g class="fx-float" style="animation-delay:.5s" fill="#fff" stroke="#1b1030" stroke-width=".5"><ellipse cx="88" cy="56" rx="2" ry="1.5"/><ellipse cx="94" cy="54" rx="2" ry="1.5"/><path d="M89.7 55.6 V48.5 L95.7 46.5 V53.6" fill="none" stroke="#fff" stroke-width="1"/></g>"""


def draw_mula(p, c):
    sparks = "".join(f'<path class="fx-float" d="M{x} {y} l1 -3 l1 3 l3 1 l-3 1 l-1 3 l-1 -3 l-3 -1 Z" fill="#ffd23f"/>'
                     for x, y in [(36, 134), (78, 136), (100, 96), (102, 24), (84, 30)])
    return f"""
<path d="M28 92 Q14 96 18 116 Q22 106 28 104" fill="none" stroke="#2b170b" stroke-width="4" stroke-linecap="round"/>
<g class="fx-gallop">
 <path d="M38 100 L30 122 L34 124 L44 104 M48 102 L46 128 L51 128 L54 104 M74 102 L84 124 L88 122 L80 100 M84 98 L94 120 L98 118 L90 96"
   stroke="#3a2214" stroke-width="5" fill="none" stroke-linecap="round"/>
 <rect x="28" y="121" width="7" height="4" rx="1" fill="#9e9e9e"/><rect x="44" y="127" width="8" height="4" rx="1" fill="#9e9e9e"/>
 <rect x="83" y="122" width="7" height="4" rx="1" fill="#9e9e9e"/><rect x="94" y="117" width="7" height="4" rx="1" fill="#9e9e9e"/>
 <path d="M28 94 Q30 78 48 78 L80 78 Q92 78 93 90 Q92 104 80 106 L40 106 Q28 104 28 94 Z" fill="#4a2c1a" stroke="#24130a" stroke-width="1.2"/>
 <path d="M80 82 L88 58 L100 62 L94 90 Z" fill="#4a2c1a" stroke="#24130a" stroke-width="1.2"/>
 <ellipse cx="94" cy="60" rx="7" ry="3" fill="#ff6a00"/>
 <path d="M46 78 Q58 72 70 78 L68 90 L48 90 Z" fill="#8b1e1e" opacity=".9"/>
 <path d="M56 78 v10 M62 78 v10" stroke="#ffd23f" stroke-width="1"/>
</g>
<g class="fx-flicker">
 <path d="M84 62 Q80 40 92 44 Q88 26 98 18 Q102 34 108 30 Q112 48 104 64 Z" fill="url(#fire-{c})"/>
 <path d="M89 62 Q88 48 95 50 Q94 38 100 34 Q102 46 105 46 Q106 56 100 64 Z" fill="#fff07a" opacity=".9"/>
</g>
{sparks}"""


def draw_vitoria_regia(p, c):
    petals = []
    for a in range(-80, 81, 20):
        petals.append(f'<ellipse cx="60" cy="88" rx="5" ry="15" transform="rotate({a} 60 102)" fill="#ffc2d9" stroke="#ff6fa3" stroke-width=".8"/>')
    for a in range(-50, 51, 25):
        petals.append(f'<ellipse cx="60" cy="92" rx="4" ry="11" transform="rotate({a} 60 102)" fill="#fff" stroke="#ffb3cf" stroke-width=".6"/>')
    veins = "".join(f'<line x1="60" y1="116" x2="{60 + 34 * math.cos(math.radians(a)):.1f}" y2="{116 + 11 * math.sin(math.radians(a)):.1f}" stroke="#1e6b36" stroke-width=".8"/>'
                    for a in range(0, 360, 30))
    stars = "".join(f'<circle class="fx-twinkle" cx="{x}" cy="{y}" r="{r}" fill="#fff"/>' for x, y, r in [(36, 46, 1.4), (46, 34, 1), (84, 76, 1.2), (30, 70, 1)])
    return f"""
<circle cx="76" cy="50" r="18" fill="url(#glow-{c})"/>
<circle cx="76" cy="50" r="10" fill="#fff7c2"/>
<circle cx="73" cy="47" r="2" fill="#efe2a0"/><circle cx="79" cy="53" r="1.4" fill="#efe2a0"/>
{stars}
<path d="M30 128 q6 -4 12 0 t12 0 t12 0 t12 0 t12 0" stroke="#fff" stroke-width="1.2" fill="none" opacity=".6"/>
<ellipse cx="60" cy="118" rx="36" ry="13" fill="#2e9e4f" stroke="#1e6b36" stroke-width="3"/>
<path d="M60 118 L94 112 L92 120 Z" fill="{p['light']}"/>
{veins}
<g class="fx-bloom">{"".join(petals)}<circle cx="60" cy="102" r="5" fill="#ffd23f" stroke="#e5850a"/></g>"""


def draw_boto(p, c):
    return f"""
<path d="M24 124 q6 -5 12 0 t12 0 t12 0 t12 0 t12 0 t12 0" stroke="{p['dark']}" stroke-width="2" fill="none" opacity=".6"/>
<path d="M26 134 q6 -5 12 0 t12 0 t12 0 t12 0 t12 0 t12 0" stroke="{p['dark']}" stroke-width="2" fill="none" opacity=".4"/>
<g class="fx-leap">
 <path d="M30 120 Q34 84 64 72 Q80 66 90 70 L104 66 Q103 72 96 76 Q90 82 80 84 Q60 90 46 112 Q40 120 34 126 Z" fill="#ff9ec4" stroke="#d6578f" stroke-width="1.4"/>
 <path d="M34 124 Q24 128 20 120 Q28 120 32 116 Z M34 124 Q34 134 28 138 Q30 128 30 122 Z" fill="#ff9ec4" stroke="#d6578f" stroke-width="1.2"/>
 <path d="M58 86 Q60 98 52 102 Q54 94 52 88 Z" fill="#f77fb0" stroke="#d6578f"/>
 <path d="M60 74 Q66 64 72 74" fill="#f77fb0"/>
 <circle cx="84" cy="73" r="1.8" fill="#3a0d24"/>
 <path d="M90 76 q4 1 7 -1" stroke="#d6578f" stroke-width="1" fill="none"/>
 <ellipse cx="74" cy="64" rx="15" ry="3.6" fill="#fff" stroke="#c9c9c9"/>
 <path d="M65 64 Q65 50 74 50 Q83 50 83 64 Z" fill="#fff" stroke="#c9c9c9"/>
 <rect x="65" y="58" width="18" height="3.5" fill="{p['b']}"/>
</g>
<circle class="fx-float" cx="40" cy="96" r="2.4" fill="none" stroke="#fff"/>
<circle class="fx-float" cx="34" cy="86" r="1.6" fill="none" stroke="#fff"/>"""


def draw_boitata(p, c):
    body = "M28 132 C48 146 82 132 70 110 C58 88 32 100 38 80 C44 60 72 64 76 54"
    flames = "".join(f'<path d="M{x} {y} q-3 -8 2 -14 q1 6 4 6 q2 -4 1 -9 q6 6 2 17 Z" fill="url(#fire-{c})"/>'
                     for x, y in [(30, 128), (52, 134), (72, 116), (56, 98), (36, 92), (50, 70)])
    return f"""
<g class="fx-flicker">{flames}</g>
<path d="{body}" fill="none" stroke="#b31b00" stroke-width="14" stroke-linecap="round"/>
<path d="{body}" fill="none" stroke="url(#fire-{c})" stroke-width="10" stroke-linecap="round"/>
<path d="{body}" fill="none" stroke="#fff07a" stroke-width="3" stroke-linecap="round" stroke-dasharray="3 5"/>
<ellipse cx="80" cy="50" rx="14" ry="10" fill="#ff7a1a" stroke="#b31b00" stroke-width="1.5"/>
<circle cx="74" cy="44" r="10" fill="url(#glow-{c})"/><circle cx="88" cy="44" r="10" fill="url(#glow-{c})"/>
<circle cx="74" cy="45" r="4.6" fill="#fffbe0"/><circle cx="87" cy="45" r="4.6" fill="#fffbe0"/>
<circle cx="75" cy="45" r="2" fill="#ff3d00"/><circle cx="88" cy="45" r="2" fill="#ff3d00"/>
<path d="M92 54 l8 2 l-3 2 l4 2 l-9 -1 Z" fill="#ff2d55"/>"""


def draw_lobisomem(p, c):
    stars = "".join(f'<circle class="fx-twinkle" cx="{x}" cy="{y}" r="1.1" fill="#fff"/>' for x, y in [(30, 50), (92, 40), (88, 100), (34, 92)])
    return f"""
<circle cx="62" cy="66" r="36" fill="url(#glow-{c})" opacity=".6"/>
<circle cx="62" cy="66" r="27" fill="#fff4c4"/>
<circle cx="52" cy="58" r="5" fill="#ece0a6"/><circle cx="70" cy="76" r="4" fill="#ece0a6"/><circle cx="72" cy="56" r="2.5" fill="#ece0a6"/>
{stars}
<path d="M38 140 Q36 118 46 104 Q50 96 50 88 L44 74 L54 82 L56 68 L62 82 Q68 76 74 68 L92 46 Q94 50 90 56 L82 70 L96 60 Q96 66 86 76 Q82 84 84 94 Q90 110 88 140 Z"
  fill="#2a2238" stroke="#120d1c" stroke-width="1.2"/>
<path d="M44 108 l-6 4 M46 118 l-7 2 M84 104 l6 2 M86 116 l6 1" stroke="#2a2238" stroke-width="3" stroke-linecap="round"/>
<circle cx="66" cy="80" r="2.2" fill="#ff2d2d"/><circle cx="66" cy="80" r="4.5" fill="#ff2d2d" opacity=".3"/>
<path d="M84 64 l2 4 l3 -3 M86 74 l2 -3 l2 2" stroke="#fff" stroke-width="1.1" fill="none"/>
<path d="M22 140 L30 116 L38 140 Z M88 140 L96 112 L104 140 Z" fill="#120d1c"/>"""


def draw_caipora(p, c):
    bristles = "".join(f'<path d="M{x} 102 l2 -6 l2 6" stroke="#1d130c" stroke-width="1.5" fill="none"/>' for x in range(36, 80, 5))
    return f"""
<path d="M24 136 Q60 126 96 136" stroke="#145a22" stroke-width="3" fill="none"/>
<path d="M30 136 l2 -10 l2 10 M90 136 l2 -12 l2 12 M60 136 l2 -8 l2 8" stroke="#2d8f3c" stroke-width="2"/>
<g class="fx-hop">
 <path d="M40 116 v14 M50 118 v14 M72 118 v14 M80 116 v14" stroke="#2a1d14" stroke-width="5" stroke-linecap="round"/>
 <ellipse cx="60" cy="112" rx="28" ry="14" fill="#3d2b1f" stroke="#1d130c" stroke-width="1.2"/>
 {bristles}
 <path d="M82 104 Q96 104 100 114 L100 120 Q92 124 82 120 Z" fill="#3d2b1f" stroke="#1d130c" stroke-width="1.2"/>
 <ellipse cx="100" cy="117" rx="3" ry="4" fill="#d48a8a"/>
 <path d="M94 120 q2 6 -3 8" stroke="#fff" stroke-width="2" fill="none"/>
 <circle cx="90" cy="109" r="1.6" fill="#ffd23f"/>
 <path d="M84 100 l-1 -6 l5 4 Z" fill="#3d2b1f"/>
 <path d="M32 106 q-6 2 -6 8" stroke="#3d2b1f" stroke-width="2" fill="none"/>
 <path d="M52 100 L54 76 Q60 70 66 76 L68 100 Z" fill="#a0522d"/>
 <path d="M50 96 L70 96 L68 104 L52 104 Z" fill="#2d8f3c"/>
 <path d="M54 80 q-10 4 -12 12 M66 80 q8 -2 12 -8" stroke="#a0522d" stroke-width="4.5" fill="none" stroke-linecap="round"/>
 <circle cx="60" cy="64" r="10" fill="#a0522d"/>
 {_eyes(56, 64, 63, .8, 2.2)}
 <path d="M49 58 Q48 44 60 46 Q72 44 71 58 Q66 52 60 54 Q54 52 49 58 Z" fill="#d9480f"/>
 <path d="M52 52 L48 36 L55 48 M58 49 L58 30 L62 48 M66 50 L72 36 L68 50" stroke="{p['b']}" stroke-width="3" fill="none" stroke-linecap="round"/>
 <rect x="76" y="70" width="10" height="2.4" fill="#5d3a1a" transform="rotate(-30 76 72)"/>
 <path class="fx-float" d="M86 64 q-4 -4 0 -8 q4 -4 0 -8" stroke="#fff" stroke-width="1.6" fill="none"/>
</g>"""


def draw_mapinguari(p, c):
    pts = []
    for i in range(48):
        ang = math.pi + i * math.pi / 47
        r = 36 if i % 2 == 0 else 31
        pts.append(f"{60 + r * math.cos(ang) * .95:.1f},{110 + r * math.sin(ang) * 1.6:.1f}")
    fur = " ".join(pts)
    return f"""
<polygon points="{fur} 92,140 28,140" fill="#5a3e2b" stroke="#2e1d12" stroke-width="1.2" stroke-linejoin="round"/>
<path d="M28 98 Q14 108 18 124 M92 98 Q106 108 102 124" stroke="#5a3e2b" stroke-width="9" fill="none" stroke-linecap="round"/>
<path d="M14 124 l2 6 M18 126 l1 6 M22 124 l0 6 M98 124 l0 6 M102 126 l-1 6 M106 124 l-2 6" stroke="#f5f0e1" stroke-width="2" stroke-linecap="round"/>
<circle cx="60" cy="70" r="11" fill="url(#glow-{c})"/>
<circle cx="60" cy="70" r="7" fill="#fff"/>
<circle class="fx-look" cx="60" cy="70" r="3.6" fill="#d00000"/><circle cx="60" cy="70" r="1.4" fill="#111"/>
<path d="M52 62 Q60 58 68 62" stroke="#2e1d12" stroke-width="2.4" fill="none"/>
<ellipse cx="60" cy="110" rx="15" ry="11" fill="#3a0a0a" stroke="#2e1d12" stroke-width="1.5"/>
{"".join(f'<path d="M{x} 100 l2.5 5 l2.5 -5 Z" fill="#fff"/>' for x in range(48, 72, 5))}
{"".join(f'<path d="M{x} 120 l2.5 -5 l2.5 5 Z" fill="#fff"/>' for x in range(50, 70, 5))}
<path d="M40 140 v4 M50 140 v4 M70 140 v4 M80 140 v4" stroke="#2e1d12" stroke-width="3"/>"""


def draw_negrinho(p, c):
    stars = "".join(f'<path class="fx-twinkle" d="M{x} {y - 3} l.9 2.1 l2.1 .9 l-2.1 .9 l-.9 2.1 l-.9 -2.1 l-2.1 -.9 l2.1 -.9 Z" fill="#fff"/>'
                    for x, y in [(30, 50), (40, 34), (30, 100), (84, 40)])
    return f"""
<path d="M80 140 L82 112 Q80 98 86 90 Q90 78 100 74 L106 80 Q102 84 102 92 L96 98 L98 140 Z" fill="#c8892f" stroke="#6b3a00" stroke-width="1"/>
<path d="M86 90 Q88 78 98 74 L92 72 Q84 76 82 88 Z" fill="#5d3a1a"/>
<circle cx="99" cy="82" r="1.2" fill="#2b170b"/>
<circle class="fx-glow" cx="56" cy="86" r="30" fill="url(#glow-{c})"/>
<path d="M36 140 L38 100 Q38 86 50 84 L58 84 Q70 86 70 100 L72 140 Z" fill="#f2f2f2" stroke="#9e9e9e" stroke-width="1"/>
<path d="M40 140 L40 124 L68 124 L68 140 Z" fill="#7a5230"/>
<circle cx="54" cy="70" r="11" fill="{SKIN_DARK}"/>
<path d="M43 67 Q44 56 54 57 Q64 56 65 67 Q60 62 54 62 Q48 62 43 67 Z" fill="#1b1030"/>
<circle cx="50" cy="71" r="1.4" fill="#1b1030"/><circle cx="58" cy="71" r="1.4" fill="#1b1030"/>
<path d="M50 76 q4 3 8 0" stroke="#3a1d0e" stroke-width="1.2" fill="none"/>
<path d="M42 96 q6 14 16 14 M68 96 q-2 14 -8 14" stroke="{SKIN_DARK}" stroke-width="4.5" fill="none" stroke-linecap="round"/>
<rect x="56" y="92" width="7" height="20" rx="2" fill="#fff3d6" stroke="#d9c49a" stroke-width=".8"/>
<ellipse cx="59.5" cy="112" rx="7" ry="2.2" fill="#b08d57"/>
<g class="fx-flicker"><path d="M59.5 76 Q65 85 62.5 90 Q59.5 93 56.5 90 Q54 85 59.5 76 Z" fill="url(#fire-{c})"/>
<path d="M59.5 82 Q61 87 59.5 90 Q58 87 59.5 82 Z" fill="#fff"/></g>
{stars}"""


def draw_matinta(p, c):
    return f"""
<path d="M86 34 a12 12 0 1 0 8 20 a9 9 0 1 1 -8 -20 Z" fill="#fff7c2" class="fx-glow"/>
<path d="M20 124 Q60 116 100 128" stroke="#4a2c1a" stroke-width="5" fill="none" stroke-linecap="round"/>
<ellipse cx="28" cy="118" rx="6" ry="3" fill="#2d8f3c" transform="rotate(-30 28 118)"/>
<ellipse cx="94" cy="122" rx="6" ry="3" fill="#2d8f3c" transform="rotate(30 94 122)"/>
<g class="fx-sway">
 <path d="M40 88 Q38 118 58 124 L62 124 Q82 118 80 88 Q78 66 60 64 Q42 66 40 88 Z" fill="#3b2f2f" stroke="#1a1414" stroke-width="1.2"/>
 <path d="M40 90 Q30 104 36 118 Q42 108 46 96 Z M80 90 Q90 104 84 118 Q78 108 74 96 Z" fill="#2a2020"/>
 <path d="M42 72 Q60 54 78 72 Q72 66 60 68 Q48 66 42 72 Z" fill="#1a1414"/>
 <path d="M46 80 Q60 66 74 80 Q74 96 60 100 Q46 96 46 80 Z" fill="#efe6d8" stroke="#bfa98c" stroke-width="1"/>
 <circle cx="54" cy="83" r="4.5" fill="#111"/><circle cx="66" cy="83" r="4.5" fill="#111"/>
 <circle cx="55.2" cy="81.8" r="1.4" fill="#fff"/><circle cx="67.2" cy="81.8" r="1.4" fill="#fff"/>
 <path d="M58 88 L60 94 L62 88 Z" fill="#d4a017"/>
 {"".join(f'<path d="M{x} {y} q2 2 4 0" stroke="#6d5a4a" stroke-width="1" fill="none"/>' for x, y in [(50, 106), (56, 110), (62, 110), (68, 106), (59, 116)])}
 <path d="M54 124 v4 M58 124 v4 M62 124 v4 M66 124 v4" stroke="#d4a017" stroke-width="1.6"/>
 <path d="M36 70 Q60 40 84 70 Q76 52 60 50 Q44 52 36 70 Z" fill="#4b0f3a" opacity=".95"/>
</g>
<text class="fx-float" x="70" y="58" font-family="Bungee, Impact, sans-serif" font-size="8" fill="#fff" stroke="#1b1030" stroke-width=".6" transform="rotate(-12 70 58)">fiiiu!</text>"""


def draw_boi_bumba(p, c):
    ribbons = "".join(f'<path class="fx-sway" d="M{x} 128 q{(-1) ** i * 3} 8 0 16" stroke="{col}" stroke-width="3" fill="none" stroke-linecap="round"/>'
                      for i, (x, col) in enumerate(zip(range(30, 92, 6), ["#e8392b", "#1fa65a", "#1f7be0", "#f2b311", "#c13cff", "#fff", "#e8392b", "#1fa65a", "#1f7be0", "#f2b311", "#c13cff"])))
    sequins = "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="{col}" stroke="#fff" stroke-width=".5"/>'
                      for (x, y), col in zip([(40, 104), (50, 112), (60, 104), (70, 112), (80, 104), (45, 122), (60, 120), (75, 122), (55, 96), (65, 96)],
                                             ["#ffd23f", "#e8392b", "#7ff0ff", "#ffd23f", "#e8392b", "#7ff0ff", "#ffd23f", "#c13cff", "#fff", "#fff"]))
    return f"""
<path d="M32 92 L88 92 L96 130 L24 130 Z" fill="{p['b']}" stroke="{p['dark']}" stroke-width="1.4"/>
<path d="M28 112 Q60 120 92 112" stroke="#ffd23f" stroke-width="2" fill="none"/>
{sequins}
{ribbons}
<g class="fx-hop">
 <path d="M46 52 Q30 50 26 36 Q36 44 46 46 Z" fill="#efe1b0" stroke="#a8915a"/>
 <path d="M74 52 Q90 50 94 36 Q84 44 74 46 Z" fill="#efe1b0" stroke="#a8915a"/>
 <path d="M28 38 q-4 8 -2 16 M92 38 q4 8 2 16" stroke="#e8392b" stroke-width="2.2" fill="none"/>
 <path d="M30 38 q0 10 4 16 M90 38 q0 10 -4 16" stroke="#1f7be0" stroke-width="2.2" fill="none"/>
 <path d="M44 50 Q60 40 76 50 L72 82 Q60 92 48 82 Z" fill="#1b1b1b" stroke="#000" stroke-width="1"/>
 <path d="M52 52 Q60 48 68 52 L66 70 Q60 74 54 70 Z" fill="#f5f5f5"/>
 <path d="M60 52 l2 4.5 l5 .5 l-3.8 3.2 l1.2 4.8 l-4.4 -2.6 l-4.4 2.6 l1.2 -4.8 l-3.8 -3.2 l5 -.5 Z" fill="#ffd23f" stroke="#e5850a" stroke-width=".6" class="fx-twinkle"/>
 <circle cx="50" cy="66" r="2.6" fill="#fff"/><circle cx="70" cy="66" r="2.6" fill="#fff"/>
 <circle cx="50.5" cy="66.5" r="1.3" fill="#111"/><circle cx="70.5" cy="66.5" r="1.3" fill="#111"/>
 <ellipse cx="60" cy="82" rx="9" ry="6" fill="#f2a7b8"/>
 <circle cx="57" cy="82" r="1.3" fill="#7a2a3a"/><circle cx="63" cy="82" r="1.3" fill="#7a2a3a"/>
</g>"""


def draw_cobra_grande(p, c):
    return f"""
<path d="M64 52 L100 30 L104 46 Z" fill="#fff7a8" opacity=".35" class="fx-glow"/>
<path d="M64 56 L104 52 L100 68 Z" fill="#fff7a8" opacity=".3" class="fx-glow"/>
<path d="M22 122 Q32 92 44 122" stroke="#16162a" stroke-width="12" fill="none" stroke-linecap="round"/>
<path d="M50 122 Q62 86 74 122" stroke="#16162a" stroke-width="12" fill="none" stroke-linecap="round"/>
<path d="M80 122 Q88 84 70 66 Q62 58 56 58" stroke="#16162a" stroke-width="12" fill="none" stroke-linecap="round"/>
<path d="M50 122 Q62 86 74 122 M80 122 Q88 84 70 66" stroke="#3d3d66" stroke-width="2" fill="none" stroke-dasharray="2 4"/>
<path d="M44 58 Q46 48 58 48 Q68 50 68 58 Q66 66 56 66 Q46 66 44 58 Z" fill="#16162a" stroke="#000"/>
<circle cx="56" cy="54" r="7" fill="url(#glow-{c})"/><circle cx="64" cy="56" r="6" fill="url(#glow-{c})"/>
<circle cx="56" cy="54" r="2.6" fill="#fffbe0"/><circle cx="64" cy="56" r="2.3" fill="#fffbe0"/>
<path d="M44 62 l-7 1 l3 2 l-4 2 l8 -1" fill="#ff2d55"/>
<path d="M14 124 q7 -6 14 0 t14 0 t14 0 t14 0 t14 0 t14 0 t14 0 L106 150 L14 150 Z" fill="{p['dark']}" opacity=".55"/>
<path d="M14 128 q7 -6 14 0 t14 0 t14 0 t14 0 t14 0 t14 0 t14 0" stroke="#fff" stroke-width="1.4" fill="none" opacity=".7"/>"""


DRAWERS = {
    "saci": draw_saci, "curupira": draw_curupira, "cuca": draw_cuca, "iara": draw_iara,
    "mula": draw_mula, "vitoria_regia": draw_vitoria_regia, "boto": draw_boto,
    "boitata": draw_boitata, "lobisomem": draw_lobisomem, "caipora": draw_caipora,
    "mapinguari": draw_mapinguari, "negrinho": draw_negrinho, "matinta": draw_matinta,
    "boi_bumba": draw_boi_bumba, "cobra_grande": draw_cobra_grande,
}


# --------------------------------------------------------------------------- cartas completas

@lru_cache(maxsize=256)
def _card_svg(color: str, kind: str, value) -> str:
    card = {"color": color, "kind": kind, "value": value}
    char = character_of(card)
    p = PAL[color]
    if kind == "number":
        banner = CHARACTERS[char]["name"]
    else:
        banner = f"{CHARACTERS[char]['short']} · {KIND_LABEL[kind]}"
    fit = ' textLength="60" lengthAdjust="spacingAndGlyphs"' if len(banner) > 10 else ""
    fs = 7.2 if len(banner) > 14 else 8
    corner = _corner_symbol(card)
    oval_fill = f"url(#ov-{color})"
    live = f" special kind-{kind}" if kind != "number" else ""
    return f"""<svg class="card-svg{live}" viewBox="0 0 120 180" xmlns="http://www.w3.org/2000/svg" role="img">
{_defs(color)}
<rect x="0.5" y="0.5" width="119" height="179" rx="12" fill="#fffaf0" stroke="#1b1030" stroke-width="1"/>
<rect x="6" y="6" width="108" height="168" rx="9" fill="url(#bg-{color})"/>
<g clip-path="url(#clip-in)">{_biome_pattern(color)}</g>
<ellipse cx="60" cy="88" rx="45" ry="68" transform="rotate(14 60 88)" fill="{oval_fill}" stroke="#fffaf0" stroke-width="3"/>
<g clip-path="url(#clip-in)">{DRAWERS[char](p, color)}</g>
<g transform="translate(17 19)">{corner}</g>
<g transform="translate(103 161) rotate(180)">{corner}</g>
<rect x="27" y="151" width="66" height="16" rx="8" fill="{p['dark']}" opacity=".9" stroke="#fffaf0" stroke-width="1"/>
<text x="60" y="162" text-anchor="middle" font-family="Bungee, Impact, sans-serif" font-size="{fs}" fill="#fffaf0"{fit}>{html.escape(banner)}</text>
</svg>"""


def card_svg(card: dict) -> str:
    return _card_svg(card["color"], card["kind"], card.get("value"))


@lru_cache(maxsize=1)
def back_svg() -> str:
    flames = "".join(f'<path d="M{x} 176 q4 -18 9 -24 q2 10 9 24 Z" fill="#ff8c1a" opacity=".35"/>' for x in range(0, 120, 18))
    ring_pts = []
    for i in range(0, 361, 10):
        a = math.radians(i)
        ring_pts.append(f"{60 + 34 * math.cos(a):.1f},{90 + 50 * math.sin(a):.1f}")
    return f"""<svg class="card-svg" viewBox="0 0 120 180" xmlns="http://www.w3.org/2000/svg" role="img">
<defs><linearGradient id="back-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b1d6e"/><stop offset="1" stop-color="#12082b"/></linearGradient>
<linearGradient id="back-fire" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffd23f"/><stop offset=".5" stop-color="#ff5a1f"/><stop offset="1" stop-color="#c0162a"/></linearGradient></defs>
<rect x="0.5" y="0.5" width="119" height="179" rx="12" fill="#fffaf0" stroke="#1b1030"/>
<rect x="6" y="6" width="108" height="168" rx="9" fill="url(#back-bg)"/>
{flames}
{"".join(f'<circle cx="{x}" cy="{y}" r="1.2" fill="#fff" opacity=".8"/>' for x, y in [(16, 18), (100, 24), (24, 60), (98, 110), (18, 140), (92, 160), (60, 14)])}
<ellipse cx="60" cy="90" rx="42" ry="64" transform="rotate(14 60 90)" fill="url(#back-fire)" stroke="#fffaf0" stroke-width="3"/>
<polyline points="{" ".join(ring_pts)}" fill="none" stroke="#3b1d6e" stroke-width="5" stroke-dasharray="8 4" transform="rotate(14 60 90)"/>
<circle cx="88" cy="44" r="4" fill="#fffbe0"/><circle cx="88" cy="44" r="1.8" fill="#c0162a"/>
<text x="60" y="88" text-anchor="middle" font-family="Bungee, Impact, sans-serif" font-size="17" fill="#fffaf0" stroke="#3b1d6e" stroke-width="3" paint-order="stroke" transform="rotate(-14 60 90)">UNO</text>
<text x="60" y="104" text-anchor="middle" font-family="Bungee, Impact, sans-serif" font-size="9.5" fill="#3b1d6e" transform="rotate(-14 60 90)" textLength="70" lengthAdjust="spacingAndGlyphs">FOLCLÓUNO</text>
</svg>"""


def color_swatch(color: str, size: int = 22) -> str:
    b = BIOMES[color]
    return (f'<span class="swatch" style="background:{b["hex"]};width:{size}px;height:{size}px" '
            f'title="{b["name"]}"></span>')


def gallery() -> list[dict]:
    """Uma carta representativa de cada personagem (para o Bestiário)."""
    items = []
    colors = ["red", "green", "blue", "yellow"]
    for value, char in enumerate(NUMBER_CHARS):
        items.append({"char": char, "card": {"color": colors[value % 4], "kind": "number", "value": value},
                      "role": f"Carta numérica {value} (2 por cor; o 0 só 1)"})
    roles = {"skip": ("yellow", "Ação Pular (2 por cor)"), "reverse": ("green", "Ação Inverter (2 por cor)"),
             "draw2": ("red", "Ação +2 (2 por cor)"), "wild": ("wild", "Coringa (4 no baralho)"),
             "wild4": ("wild", "Coringa +4 (4 no baralho)")}
    for kind, (color, role) in roles.items():
        items.insert(0, {"char": KIND_CHARS[kind], "card": {"color": color, "kind": kind, "value": None}, "role": role})
    return items
