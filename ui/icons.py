"""Ícones e avatares originais em SVG (desenhados à mão, sem pacotes de ícones).

- ``icon(nome)``      -> SVG inline (traço em ``currentColor``) para usar no HTML;
- ``icon_mask_css()`` -> CSS que coloca os ícones nos botões/abas nativos do
  Streamlit (``mask-image`` com o SVG em data URI, pintado com a cor do texto);
- ``avatar_svg(chave)`` -> medalhão redondo com um personagem do folclore.
"""

from __future__ import annotations

import html
from urllib.parse import quote

from game import avatars as AV

# Traços pensados para 24x24, estilo "entalhado": linhas grossas, pontas redondas.
ICONS: dict[str, str] = {
    "fire": '<path d="M12 22c-4 0-7-2.6-7-6.6 0-3 1.8-5 3.4-6.6.3 2 1.2 3 2.2 3.4-.4-3.6 1.2-7 4.4-9.2-.4 3 1 5 2.6 6.8 1.4 1.6 2.4 3.4 2.4 5.6 0 4-3.6 6.6-8 6.6z"/><path d="M12 22c-1.8 0-3-1.2-3-3 0-1.6 1.2-2.8 2.2-3.8.2 1 .8 1.6 1.4 1.8.4-.8.6-1.8.4-2.8 1.4 1 2 2.4 2 3.8 0 2.4-1.4 4-3 4z"/>',
    "leaf": '<path d="M4 20C4 10 10 4 20 4c0 10-6 16-16 16z"/><path d="M4 20 15 9"/><path d="M9 15h4M11.5 12.5V9"/>',
    "wave": '<path d="M2 8c2.5-2.5 5-2.5 7.5 0s5 2.5 7.5 0 3.5-2 5-1"/><path d="M2 13c2.5-2.5 5-2.5 7.5 0s5 2.5 7.5 0 3.5-2 5-1"/><path d="M2 18c2.5-2.5 5-2.5 7.5 0s5 2.5 7.5 0 3.5-2 5-1"/>',
    "sun": '<circle cx="12" cy="12" r="4.2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
    "crown": '<path d="M3 18 2 7l5.5 4L12 4l4.5 7L22 7l-1 11z"/><path d="M3 21h18"/><circle cx="12" cy="13.5" r="1.4"/>',
    "spirit": '<path d="M6 21v-9a6 6 0 0 1 12 0v9l-2-1.6-2 1.6-2-1.6-2 1.6-2-1.6z"/><circle cx="9.6" cy="11.5" r="1.3"/><circle cx="14.4" cy="11.5" r="1.3"/><path d="M10 15.5q2 1.4 4 0"/>',
    "door": '<path d="M5 21V4.5L14 3v18"/><path d="M14 5h5v16"/><path d="M3 21h18"/><circle cx="11.5" cy="12.5" r=".9"/>',
    "scroll": '<path d="M7 3h11a2 2 0 0 1 0 4h-2v12a2 2 0 0 1-2 2H5a2 2 0 0 1 0-4h2z"/><path d="M7 17V3M10 8h4M10 11h4M10 14h3"/>',
    "trophy": '<path d="M7 3h10v6a5 5 0 0 1-10 0z"/><path d="M7 5H3.5c0 3 1.5 5 4 5.2M17 5h3.5c0 3-1.5 5-4 5.2"/><path d="M12 14v4M8 21h8M9.5 18h5"/>',
    "book": '<path d="M12 6.5C10 4.8 7 4.3 3 4.5v14c4-.2 7 .3 9 2 2-1.7 5-2.2 9-2v-14c-4-.2-7 .3-9 2z"/><path d="M12 6.5v14"/>',
    "cards": '<rect x="3" y="6" width="11" height="15" rx="2" transform="rotate(-10 8.5 13.5)"/><rect x="10" y="3" width="11" height="15" rx="2" transform="rotate(8 15.5 10.5)"/><path d="M15.6 7.6l.9 2.2 2.2.4-1.7 1.5.5 2.3-2-1.2-2 1"/>',
    "speaker": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>',
    "mute": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="m16.5 9.5 5 5M21.5 9.5l-5 5"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3.5-3.5a4 4 0 0 0-5.7-5.7L12 6.3"/><path d="M14 10a4 4 0 0 0-5.7 0l-3.5 3.5a4 4 0 0 0 5.7 5.7l1.5-1.5"/>',
    "swords": '<path d="M4 3l9 9M3 4l1-1M4 3 3 4l9 9"/><path d="M20 3l-9 9"/><path d="M14 15l-4 4M10 15l4 4M6 18l-2.5 2.5M18 18l2.5 2.5"/><path d="M3 4V3h1M21 4V3h-1"/><path d="M8 13l3 3M16 13l-3 3"/>',
    "skip": '<path d="M5 5l9 7-9 7z"/><path d="M18 5v14"/>',
    "loop": '<path d="M4 12a8 8 0 0 1 14-5.3L20 9"/><path d="M20 4v5h-5"/><path d="M20 12a8 8 0 0 1-14 5.3L4 15"/><path d="M4 20v-5h5"/>',
    "play": '<path d="M7 4l13 8-13 8z"/>',
    "horn": '<path d="M3 10v4l3 .5L18 20V4L6 9.5z"/><path d="M6 14.5 7.5 20h2.5L9 15"/><path d="M21 9v6"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "cw": '<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 3.5v5h-5"/>',
    "ccw": '<path d="M4 12a8 8 0 1 0 2.3-5.6"/><path d="M4 3.5v5h5"/>',
    "eye": '<path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.4 0 2-1 1.4-2.2-.8-1.6.2-3.3 2-3.3H18a3.5 3.5 0 0 0 3.5-3.5C21.5 7 17.2 3 12 3z"/><circle cx="7.5" cy="11" r="1.3"/><circle cx="10.5" cy="7" r="1.3"/><circle cx="15" cy="7.5" r="1.3"/>',
    "torch": '<path d="M9 11h6l-1.5 11h-3z"/><path d="M12 2c2.6 2.3 3.6 4.4 2.8 6.3-.4 1-1.4 1.7-2.8 1.7s-2.4-.7-2.8-1.7C8.4 6.4 9.4 4.3 12 2z"/>',
    "medal": '<circle cx="12" cy="15" r="6"/><path d="M8.5 10 6 3h4l2 5 2-5h4l-2.5 7"/>',
    "clawbook": '<path d="M4 4.5h10.5a3 3 0 0 1 3 3V21H7a3 3 0 0 1-3-3z"/><path d="M4 18a3 3 0 0 1 3-3h10.5"/><path d="M17.5 4.5H20V18"/><path d="M8 7.5l2.5 5M10.5 6.8l2.5 5M13 6.5l2 4.2"/>',
    "sealscroll": '<path d="M6 3h12v14a3 3 0 0 1-3 3H6"/><path d="M6 3a2.5 2.5 0 0 0 0 5h2"/><path d="M6 20a2.5 2.5 0 0 1 0-5h3"/><path d="M10 7h5M10 10h5"/><circle cx="14.5" cy="15" r="2.6"/><path d="M13.4 17.3 12.6 21M15.6 17.3l.8 3.7"/>',
    "dice": '<rect x="3.5" y="3.5" width="17" height="17" rx="3.5" transform="rotate(8 12 12)"/><circle cx="8.6" cy="8.6" r="1.3" fill="currentColor"/><circle cx="15.4" cy="15.4" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="15.4" cy="8.6" r="1.3" fill="currentColor"/><circle cx="8.6" cy="15.4" r="1.3" fill="currentColor"/>',
    "ember": '<path d="M12 3l2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-2.2z"/>',
}


def icon(name: str, size: int = 18, cls: str = "", title: str = "") -> str:
    """SVG inline (stroke = currentColor)."""
    body = ICONS[name]
    t = f"<title>{html.escape(title)}</title>" if title else ""
    return (f'<svg class="ico ico-{name} {cls}" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="{"false" if title else "true"}" xmlns="http://www.w3.org/2000/svg">{t}{body}</svg>')


def icon_data_uri(name: str) -> str:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" '
           f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')
    return "data:image/svg+xml;utf8," + quote(svg)


# chave do widget (ou seletor) -> ícone. Botões nativos não aceitam HTML no rótulo,
# então o ícone entra por CSS (::before com máscara).
BUTTON_ICONS = {
    "create_submit": "fire", "join_submit": "torch", "add_bot": "spirit", "start": "play",
    "leave_lobby": "door", "leave_game": "door", "btn_draw": "cards", "btn_pass": "skip",
    "btn_challenge": "swords", "btn_accept": "cards", "resume": "torch", "host_skip": "skip",
    "host_bot": "spirit", "to_lobby": "loop", "next_round": "play", "test_sound": "speaker",
    "gone_home": "door", "draw_room": "dice", "gone_home2": "door", "cancel_wild": "x",
    "login_submit": "door", "signup_submit": "scroll", "reset_submit": "loop", "google_login": "link",
    "logout_btn": "door", "back_room": "play", "to_login": "door", "auto_btn": "spirit", "auto_yes": "spirit",
}
TAB_ICONS = ["cards", "clawbook", "crown", "sealscroll"]


def icon_mask_css() -> str:
    rules = []
    base = ("content:'';display:inline-block;width:1.15em;height:1.15em;margin-right:.45em;vertical-align:-.2em;"
            "background:currentColor;-webkit-mask:var(--ico) center/contain no-repeat;mask:var(--ico) center/contain no-repeat;")
    for key, name in BUTTON_ICONS.items():
        rules.append(f".st-key-{key} button p::before{{{base}--ico:url(\"{icon_data_uri(name)}\");}}")
    for prefix, name in (("den_", "horn"), ("rm_", "x")):
        rules.append(f'[class*="st-key-{prefix}"] button p::before{{{base}--ico:url("{icon_data_uri(name)}");}}')
    for i, name in enumerate(TAB_ICONS, 1):
        rules.append(f'[data-testid="stTabs"] [role="tab"][data-key="{i - 1}"] p::before'
                     f'{{{base}--ico:url("{icon_data_uri(name)}");}}')
    for color, name in (("red", "fire"), ("green", "leaf"), ("blue", "wave"), ("yellow", "sun")):
        rules.append(f'[class*="st-key-pick_{color}"] button p::before{{{base}--ico:url("{icon_data_uri(name)}");}}')
    rules.append(f'[class*="st-key-avpop_"] button p::before{{{base}--ico:url("{icon_data_uri("loop")}");}}')
    rules.append(f".st-key-muted label p::before{{{base}--ico:url(\"{icon_data_uri('mute')}\");}}")
    rules.append(f'[data-testid="stExpander"] summary p::before{{{base}--ico:url("{icon_data_uri("link")}");}}')
    # o botão de remover jogador é só ícone
    rules.append('[class*="st-key-rm_"] button p::before{margin-right:0}')
    return "\n".join(rules)


# --------------------------------------------------------------------------- avatares
# Retratos-medalhão dos personagens do folclore (viewBox 32x32), na paleta das cartas:
# silhueta forte e poucos detalhes, para ler bem de 26 a 46 px. Partes com classe
# ``av-*`` ganham uma animação sutil pelo CSS (desligada com prefers-reduced-motion).

_SKIN_DARK, _SKIN, _SKIN_LIGHT = "#6b3e26", "#b9773f", "#e5ad73"


def _eyes(x1: float, x2: float, y: float, r: float = 1.6, look: float = .3) -> str:
    return (f'<circle cx="{x1}" cy="{y}" r="{r}" fill="#fff"/><circle cx="{x2}" cy="{y}" r="{r}" fill="#fff"/>'
            f'<circle cx="{x1 + look}" cy="{y}" r="{r * .5:.2f}" fill="#1b1030"/>'
            f'<circle cx="{x2 + look}" cy="{y}" r="{r * .5:.2f}" fill="#1b1030"/>')


def _bust(fill: str, y: float = 26.5, neck: float = 4.5, extra: str = "") -> str:
    """Ombros que terminam exatamente na borda do medalhão (arco do círculo)."""
    import math

    dx = math.sqrt(15.5 ** 2 - (y - 16) ** 2)
    x0, x1 = 16 - dx, 16 + dx
    return (f'<path d="M{x0:.2f} {y} Q{x0 + 1:.2f} {y - 5:.2f} {16 - neck - 1.5:.2f} {y - 5.5:.2f} H{16 + neck + 1.5:.2f} '
            f'Q{x1 - 1:.2f} {y - 5:.2f} {x1:.2f} {y} A15.5 15.5 0 0 1 {x0:.2f} {y}Z" fill="{fill}"{extra}/>')


def _waves(fill: str, y: float = 26, light: str = "#bff6ff") -> str:
    import math

    dx = math.sqrt(15.5 ** 2 - (y - 16) ** 2)
    x0, x1 = 16 - dx, 16 + dx
    step = (x1 - x0) / 4
    q = "".join(f" q{step / 2:.2f} -1.8 {step:.2f} 0" for _ in range(4))
    return (f'<path d="M{x0:.2f} {y}{q} A15.5 15.5 0 0 1 {x0:.2f} {y}Z" fill="{fill}"/>'
            f'<path d="M{x0 + 2:.2f} {y + 2.4}q2 -1.2 4 0t4 0t4 0t4 0" stroke="{light}" stroke-width=".9" fill="none" opacity=".7"/>')


_FLAME = "#ff6a1a"
_FLAME_IN = "#ffd23f"

_AV: dict[str, tuple[str, str]] = {
    "saci": ("#173a1c",
             _bust(_SKIN_DARK)
             + f'<circle cx="15" cy="18.5" r="6.6" fill="{_SKIN_DARK}"/>'
             + _eyes(12.6, 17.6, 18.6, 1.75, .45)
             + '<path d="M12.4 22.4q3 2.7 6 0" stroke="#fff" stroke-width="1.3" fill="#fff" stroke-linejoin="round"/>'
             + '<g class="av-sway"><path d="M8.3 16.6C7.8 10.4 14 8.6 25.5 4.6 21.6 9.4 20.9 12.8 21.5 16.6 15.4 14 11.5 14.6 8.3 16.6Z" fill="#e01e37" stroke="#8a0a1c" stroke-width=".7"/>'
               '<circle cx="25.4" cy="4.7" r="1.7" fill="#ff5d73"/></g>'
             + '<path d="M18.6 23.2h5" stroke="#5d3a1a" stroke-width="1.3" stroke-linecap="round"/>'
             + '<rect x="22.6" y="19.6" width="3.2" height="4" rx="1" fill="#8b5a2b"/>'
             + '<path class="av-float" d="M24.6 18q-1.8-1.6 0-3.2t0-3.2" stroke="#fff" stroke-width="1.1" fill="none" stroke-linecap="round" opacity=".85"/>'),
    "curupira": ("#0b3a1e",
                 '<g class="av-flick"><path d="M6.8 21C5.8 14 8 9.4 10 6.2c.5 2.8 1.5 4 2.6 4.5 0-3.4 1.5-6 4-8.2 0 3.4 1.5 5.6 3 6.6 1-1.9 2-3 4-4-.5 3.4.6 5.9 1.6 8.9.8 2.6.6 5 .1 7Z" fill="#ff6a1a"/>'
                 '<path d="M9.6 19c-.4-4 .8-6.6 2.4-8.4.4 2 1.4 2.8 2.4 3 .2-2.6 1.4-4.4 3-5.6.2 2.4 1.4 4 2.8 4.8.6-1 1.4-1.6 2.4-2 0 2.6.8 5 .4 8.2Z" fill="#ffd23f"/></g>'
                 + _bust(_SKIN, extra=' stroke="#0b3a1e" stroke-width=".4"')
                 + '<path d="M6 27.6q3-4.2 6.4-2.6-1 3.4-6.4 2.6ZM26 27.6q-3-4.2-6.4-2.6 1 3.4 6.4 2.6Z" fill="#3fbf6a" stroke="#0b3a1e" stroke-width=".5"/>'
                 + f'<circle cx="16" cy="19" r="6.2" fill="{_SKIN}"/>'
                 + _eyes(13.6, 18.4, 18.6, 1.7, -.4)
                 + '<path d="M13.4 22.2q2.6 2 5.2 0" stroke="#5c2a12" stroke-width="1.2" fill="none" stroke-linecap="round"/>'),
    "iara": ("#06304a",
             '<path d="M8.4 28C6 21 7 10.6 16 9.2c9 1.4 10 11.8 7.6 18.8Z" fill="#1a1530"/>'
             + _bust("#c98a52")
             + '<path d="M11.4 26q4.6-2.6 9.2 0l-.6 2.4q-4 1.6-8 0Z" fill="#ff8fab" stroke="#d6336c" stroke-width=".5"/>'
             + '<circle cx="16" cy="17.2" r="5.6" fill="#c98a52"/>'
             + '<path d="M10.3 16.6Q10.8 10.6 16 10.4q5.4.2 5.8 6.2-3-3.6-6.2-3.4-3.4.2-5.3 3.4Z" fill="#1a1530"/>'
             + '<path d="M12.6 17.8q1.3 1.1 2.6 0M16.8 17.8q1.3 1.1 2.6 0" stroke="#1a1530" stroke-width=".9" fill="none"/>'
             + '<ellipse cx="16" cy="20.6" rx="1.2" ry=".8" fill="#b5172f"/>'
             + '<g class="av-bob"><circle cx="21.6" cy="11.6" r="2.2" fill="#ff6fa3"/><circle cx="23.6" cy="13.6" r="1.6" fill="#ffc2d9"/><circle cx="21.6" cy="11.6" r=".8" fill="#ffd23f"/></g>'
             + _waves("#14b8a6", 27)),
    "cuca": ("#1c1030",
             '<path d="M7.6 12.4Q3.6 17 4.8 23.4 6.4 18.6 7.8 17Q7.2 21 9 24 9 19 10 15.6Z" fill="#ffd23f" stroke="#c99a00" stroke-width=".4"/>'
             + _bust("#6a2c91")
             + '<path d="M6.4 18Q6.4 11.8 13 11.8q4 0 6 1.8l8.4 1.4q2.4 1.8 0 3.8l-9 1.6Q13.6 24 9.6 22.2 6.4 21 6.4 18Z" fill="#4caf50" stroke="#1b5e20" stroke-width=".7"/>'
             + "".join(f'<path d="M{x} 18.6l.8 1.4.8-1.4Z" fill="#fff"/>' for x in (19.4, 21.2, 23, 24.8))
             + '<circle class="av-glow" cx="12.6" cy="15.2" r="2.5" fill="#ffeb3b" stroke="#1b5e20" stroke-width=".5"/>'
             + '<ellipse cx="12.8" cy="15.2" rx=".6" ry="1.8" fill="#111"/><circle cx="26.6" cy="16" r=".6" fill="#1b5e20"/>'
             + '<path d="M7.4 11.6 12.2 1.9 16.8 11.2Z" fill="#8a3bbd" stroke="#3b1356" stroke-width=".6"/>'
             + '<ellipse cx="12.1" cy="11.5" rx="7" ry="1.6" fill="#8a3bbd" stroke="#3b1356" stroke-width=".6"/>'
             + '<path d="M9.2 9.4h6.2" stroke="#ffd23f" stroke-width="1.2"/>'),
    "mula": ("#2a0a05",
             '<path d="M6.9 28.5Q7.4 19 13.6 14.2l6.4-2.6 3.4 5.6q-4.2 2.4-4.2 7.8l1.3 5.8A15.5 15.5 0 0 1 6.9 28.5Z" fill="#4a2c1a" stroke="#24130a" stroke-width=".7"/>'
             + '<path d="M8.6 24q.6-6 5-9.6M10.4 26q.4-5 4-8.6" stroke="#24130a" stroke-width="1.1" fill="none" stroke-linecap="round"/>'
             + '<path d="M10 27.4q4-2.4 9.4-1.6l.4 3.2q-5 .4-9.4 0Z" fill="#8b1e1e"/>'
             + '<ellipse cx="21.7" cy="14.4" rx="3.6" ry="1.5" transform="rotate(-30 21.7 14.4)" fill="#ff6a00"/>'
             + '<g class="av-flick"><path d="M17.6 13.6C16 8.6 19 6.4 19.4 2.6c1.6 2.4 3 3 3.6 5.4 1-1.6 1.4-3.2 3-3.6-.4 3.6 1.2 5.6.2 8.6-1.4 2.8-4.6 3.6-8.6.6Z" fill="#ff6a1a"/>'
               '<path d="M19.6 13.2c-.8-2.8.8-4.4 1.2-6.6 1 1.6 2 2.2 2.2 3.6.6-.8 1-1.6 1.8-2 0 2 .6 3.2 0 4.8-1 1.6-3 1.6-5.2.2Z" fill="#ffd23f"/></g>'),
    "boitata": ("#08142e",
                '<circle class="av-glow" cx="23" cy="9" r="6" fill="#ffd23f" opacity=".22"/>'
                + '<path d="M6.4 23.6C9.6 29.4 20.4 28.4 20.4 22.4c0-5-9.2-4.2-9.2-9.4 0-4.6 6.6-6.6 10.6-4.6" stroke="#ff6a1a" stroke-width="4.6" fill="none" stroke-linecap="round"/>'
                + '<path class="av-flick" d="M6.4 23.6C9.6 29.4 20.4 28.4 20.4 22.4c0-5-9.2-4.2-9.2-9.4 0-4.6 6.6-6.6 10.6-4.6" stroke="#ffd23f" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-dasharray="2.4 2"/>'
                + '<ellipse cx="23.4" cy="9.2" rx="4.4" ry="3.6" fill="#ff8a3d" stroke="#c0162a" stroke-width=".6"/>'
                + '<circle cx="24.2" cy="8.4" r="2.2" fill="#fff7c2"/><circle cx="24.6" cy="8.4" r="1" fill="#c0162a"/>'
                + '<path d="M27.6 10.4l2 .6-2 .8" stroke="#ff3b3b" stroke-width=".7" fill="none"/>'
                + '<circle cx="7" cy="12" r=".8" fill="#ffd23f"/><circle cx="27" cy="20" r=".7" fill="#ffd23f"/><circle cx="10" cy="7" r=".6" fill="#ff8a3d"/>'),
    "boto": ("#06233f",
             _waves("#1f7be0", 25.6)
             + '<g class="av-bob"><path d="M4.6 20.4Q4 18 7 17.6l4.6-.6Q13 12.4 19 12q7.2 0 8 6.4.4 6.6-7 8-6.4.6-8.6-5.2l-4.4.6q-2.2 0-2.4-1.4Z" fill="#ff9ec4" stroke="#c2185b" stroke-width=".7"/>'
               '<path d="M13 22q3.6 3.6 9 1.4" stroke="#ffd0e2" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
               '<circle cx="16" cy="17.6" r="1.1" fill="#3a0d24"/><path d="M5.4 20.2l5.8-.4" stroke="#c2185b" stroke-width=".6"/>'
               '<ellipse cx="19.6" cy="12.4" rx="7.2" ry="1.7" fill="#f5f5f5" stroke="#9aa0a6" stroke-width=".4"/>'
               '<path d="M14.6 12.4Q14.6 6.4 19.6 6.4t5 6Z" fill="#fff" stroke="#9aa0a6" stroke-width=".4"/>'
               '<rect x="14.7" y="10" width="9.8" height="1.6" fill="#1b1030"/></g>'),
    "caipora": ("#3a2600",
                '<path d="M8.4 27C6.6 20 8 12 16 11.4 24 12 25.4 20 23.6 27Z" fill="#1a1209"/>'
                + _bust(_SKIN_DARK)
                + '<path d="M11 25.6q5 2.6 10 0" stroke="#fff3d6" stroke-width="1.3" fill="none" stroke-dasharray=".2 1.6" stroke-linecap="round"/>'
                + f'<circle cx="16" cy="18" r="5.9" fill="{_SKIN_DARK}"/>'
                + '<path d="M10.2 17Q10.6 12 16 11.8q5.4.2 5.8 5.2-2.8-2.6-5.8-2.6t-5.8 2.6Z" fill="#1a1209"/>'
                + _eyes(13.7, 18.3, 18.4, 1.5)
                + '<path d="M11.6 20.6l1.8-.4M11.8 21.8l1.8-.4M20.4 20.6l-1.8-.4M20.2 21.8l-1.8-.4" stroke="#e8392b" stroke-width=".8" stroke-linecap="round"/>'
                + '<g class="av-sway"><path d="M10.6 12.6C8.4 9 9.4 5.6 11 4.2c1 2.6 1.4 5.2.8 8.2Z" fill="#3fbf6a" stroke="#0b3a1c" stroke-width=".5"/>'
                  '<path d="M14.6 11.6C14 7.4 15.4 4 16.4 2.6c1.2 2.8 1.2 5.8 0 9Z" fill="#63e08f" stroke="#0b3a1c" stroke-width=".5"/>'
                  '<path d="M20.4 12.4c-.8-3.6.6-6.6 2.4-8 .6 2.8.2 5.4-1.2 8.2Z" fill="#3fbf6a" stroke="#0b3a1c" stroke-width=".5"/>'
                  '<path d="M10 13.4q6-3.2 12 0" stroke="#e8392b" stroke-width="1.4" fill="none"/></g>'),
    "negrinho": ("#1e1630",
                 _bust("#e9dcc0")
                 + '<circle cx="14.4" cy="18" r="6.2" fill="#4a2818"/>'
                 + '<path d="M8.4 16.4q.4-5.6 6-5.8 5.4.2 6 5-2-2.6-6-2.6-3.6 0-6 3.4Z" fill="#1a0f08"/>'
                 + _eyes(12.2, 16.8, 18.2, 1.55, .35)
                 + '<path d="M12.4 21.4q2 1.4 4 0" stroke="#e9dcc0" stroke-width="1" fill="none" stroke-linecap="round"/>'
                 + '<circle class="av-glow" cx="24.4" cy="13.4" r="4.4" fill="#ffd23f" opacity=".3"/>'
                 + '<rect x="22.8" y="15.4" width="3.2" height="9" rx=".8" fill="#fff3d6" stroke="#c9a24a" stroke-width=".4"/>'
                 + '<path class="av-flick" d="M24.4 9.6c1.6 1.8 1.8 3.4 1 4.6-.5.8-1.5.8-2 0-.8-1.2-.6-2.8 1-4.6Z" fill="#ffb02e"/>'
                 + '<path d="M19.6 24.4q2-2.2 4.6-1.6" stroke="#4a2818" stroke-width="2" fill="none" stroke-linecap="round"/>'),
    "lobisomem": ("#0c0b24",
                  '<circle cx="22.6" cy="9.4" r="6.4" fill="#fff1b8" opacity=".9"/>'
                  + '<path d="M7.6 11.4 9 3.8l4.2 5Q16 8 18.8 8.8L23 3.8l1.4 7.6q2.2 5.2-.6 10Q20.2 26.8 16 27.2 11.8 26.8 8.2 21.4q-2.8-4.8-.6-10Z" fill="#5a5560" stroke="#1b1030" stroke-width=".7"/>'
                  + '<path d="M9.4 6.4l2 3M22.6 6.4l-2 3" stroke="#2a2630" stroke-width="1.4" stroke-linecap="round"/>'
                  + '<path d="M7.8 18.4l-2 1.4 2.4.4M24.2 18.4l2 1.4-2.4.4" fill="#5a5560" stroke="#5a5560" stroke-width="1"/>'
                  + '<path d="M12.2 19.2Q16 17 19.8 19.2 19.4 24.6 16 25 12.6 24.6 12.2 19.2Z" fill="#b9b4bf"/>'
                  + '<ellipse cx="16" cy="19.6" rx="1.8" ry="1.2" fill="#14101c"/>'
                  + '<path d="M13.6 23.2l.6 1.6.6-1.4M18.4 23.2l-.6 1.6-.6-1.4" fill="#fff" stroke="#fff" stroke-width=".4"/>'
                  + '<g class="av-glow"><path d="M10 14.4l4 1-3.4 1.4Z" fill="#ffd23f"/><path d="M22 14.4l-4 1 3.4 1.4Z" fill="#ffd23f"/></g>'),
    "mapinguari": ("#0f2a14",
                   '<path d="M5.4 27.2Q4.8 19 6.8 13.4 7 8 11 6.2l1.4 1.4L14 4.8l1.8 2 1.8-2.4 1.6 2.6 1.8-1.6.8 2.2Q26 9 25.6 14.6q1.8 6 .6 12.6A15.5 15.5 0 0 1 5.4 27.2Z" fill="#7a4a2a" stroke="#3b2210" stroke-width=".7"/>'
                   + '<path d="M8 16l1.6 1.2M8.6 21l1.6 1M23.6 16l-1.6 1.2M23 21l-1.6 1M12 9.4l.8 1.4M20 9.4l-.8 1.4" stroke="#3b2210" stroke-width="1" stroke-linecap="round"/>'
                   + '<circle cx="16" cy="12.6" r="3.4" fill="#fff6dc" stroke="#3b2210" stroke-width=".6"/>'
                   + '<circle class="av-glow" cx="16.3" cy="12.8" r="1.6" fill="#d61f1f"/><circle cx="16.3" cy="12.8" r=".6" fill="#14101c"/>'
                   + '<ellipse cx="16" cy="21.8" rx="5.6" ry="3.2" fill="#2a0a0a" stroke="#3b2210" stroke-width=".6"/>'
                   + '<path d="M10.8 20.8l1.2 1.6 1.2-1.8 1.2 1.8 1.2-1.9 1.2 1.9 1.2-1.8 1.2 1.8 1.2-1.6" fill="none" stroke="#fff" stroke-width=".8" stroke-linejoin="round"/>'),
    "boi_bumba": ("#5a1020",
                  '<path d="M10.6 10.6Q4.4 10 3.4 4.6q3.2 3.4 7.6 3.2ZM21.4 10.6q6.2-.6 7.2-6-3.2 3.4-7.6 3.2Z" fill="#efe1b0" stroke="#8a6a3a" stroke-width=".5"/>'
                  + '<g class="av-sway"><path d="M5.6 9.4q-1.6 4 .4 8M7.4 10.2q-.8 4.6 1.4 8.4" stroke="#ffd23f" stroke-width="1.1" fill="none" stroke-linecap="round"/>'
                    '<path d="M26.4 9.4q1.6 4-.4 8M24.6 10.2q.8 4.6-1.4 8.4" stroke="#1f7be0" stroke-width="1.1" fill="none" stroke-linecap="round"/>'
                    '<path d="M6.6 9.8q-2 4.4.2 9" stroke="#1fa65a" stroke-width="1.1" fill="none" stroke-linecap="round"/>'
                    '<path d="M25.4 9.8q2 4.4-.2 9" stroke="#e8392b" stroke-width="1.1" fill="none" stroke-linecap="round"/></g>'
                  + '<path d="M9.8 8.6h12.4l-1.6 14Q16 28 11.4 22.6Z" fill="#1d1d1d" stroke="#e9c46a" stroke-width=".8"/>'
                  + '<path d="M16 9.8l1 2.2 2.4.3-1.8 1.6.5 2.4-2.1-1.2-2.1 1.2.5-2.4-1.8-1.6 2.4-.3Z" fill="#ffd23f"/>'
                  + '<ellipse cx="16" cy="22.6" rx="3.8" ry="2.5" fill="#f2a7b8"/><circle cx="14.6" cy="22.6" r=".6" fill="#5a1020"/><circle cx="17.4" cy="22.6" r=".6" fill="#5a1020"/>'
                  + '<circle cx="12.4" cy="15.8" r="1.2" fill="#fff"/><circle cx="19.6" cy="15.8" r="1.2" fill="#fff"/>'
                  + '<circle cx="12.6" cy="15.8" r=".55" fill="#111"/><circle cx="19.4" cy="15.8" r=".55" fill="#111"/>'),
    "matinta": ("#1c2a24",
                '<path d="M5.6 28.4Q6 12 14.6 7.6q8.6 1.4 10 13l1 7.6A15.5 15.5 0 0 1 5.6 28.4Z" fill="#14101c" stroke="#5b4a7a" stroke-width=".7"/>'
                + '<circle cx="14.6" cy="18.4" r="5.2" fill="#c99b6d"/>'
                + '<path d="M9.6 17.6q.6-5.2 5-5.4 4.4.2 5 5.2-1.6-2.8-5-2.8t-5 3Z" fill="#b8b8c0"/>'
                + '<path d="M11.8 18.6h2M15.4 18.6h2" stroke="#1b1030" stroke-width="1" stroke-linecap="round"/>'
                + '<path d="M14.6 18.8l-1.2 3h1.4" stroke="#8a5a35" stroke-width=".7" fill="none"/>'
                + '<path d="M12.6 23q2 .8 4 0" stroke="#5c2a12" stroke-width=".7" fill="none"/>'
                + '<g class="av-bob"><ellipse cx="23.8" cy="12.4" rx="3.6" ry="4.4" fill="#c9a46a" stroke="#6b4a2a" stroke-width=".5"/>'
                  '<path d="M23.8 9.2q3 0 3 2.6-.2 3.6-3 4.6-2.8-1-3-4.6 0-2.6 3-2.6Z" fill="#fff6e6"/>'
                  '<circle cx="22.7" cy="11.8" r=".7" fill="#14101c"/><circle cx="24.9" cy="11.8" r=".7" fill="#14101c"/>'
                  '<path d="M23.8 13.2l-.4 1h.8Z" fill="#c98a2e"/></g>'),
    "boiuna": ("#04203d",
               '<path d="M10.4 30Q12 24 11 20.6 7.6 16.4 9.6 10.6 16 4.6 22.4 10.6q2 5.8-1.4 10-1 3.4.6 9.4" fill="#123a2a" stroke="#06150e" stroke-width=".7"/>'
               + '<path d="M13.8 30q.8-5 .4-8.4h3.6q-.4 3.4.4 8.4" fill="#2f6b45"/>'
               + '<path d="M14.6 23.6h2.8M14.4 26h3.2M14.5 28.4h3" stroke="#123a2a" stroke-width=".5"/>'
               + '<g class="av-glow"><ellipse cx="13.2" cy="12.8" rx="1.7" ry="1.2" fill="#c4ff5c"/><ellipse cx="18.8" cy="12.8" rx="1.7" ry="1.2" fill="#c4ff5c"/></g>'
               + '<ellipse cx="13.2" cy="12.8" rx=".4" ry="1" fill="#06150e"/><ellipse cx="18.8" cy="12.8" rx=".4" ry="1" fill="#06150e"/>'
               + '<path class="av-float" d="M16 17.6v2.6l-1 1.2M16 20.2l1 1.2" stroke="#ff3b3b" stroke-width=".7" fill="none" stroke-linecap="round"/>'
               + _waves("#1f7be0", 26.6)),
}
AVATAR_KEYS = list(_AV)


def avatar_svg(key: str, name: str = "", size: int = 38, title: bool = False) -> str:
    """Medalhão com o personagem do jogador. Chaves antigas (fogo, folha...) viram o
    personagem equivalente; desconhecidas mostram a inicial do nome."""
    k = AV.normalize(key)
    t = ""
    if k in _AV:
        bg, body = _AV[k]
        if title:
            t = f"<title>{html.escape(AV.full_name(k))}</title>"
    else:
        initial = html.escape((name or "?").strip()[:1].upper() or "?")
        bg, body = "#1d140a", (f'<text x="16" y="21.5" text-anchor="middle" font-family="Cinzel, serif" '
                               f'font-size="15" font-weight="700" fill="#e9c46a">{initial}</text>')
    return (f'<svg class="av-svg av-{k or "x"}" viewBox="0 0 32 32" width="{size}" height="{size}" '
            f'xmlns="http://www.w3.org/2000/svg" aria-hidden="{"false" if t else "true"}">{t}'
            f'<circle cx="16" cy="16" r="15.5" fill="{bg}"/><circle cx="13" cy="11" r="11" fill="#fff" opacity=".05"/>'
            f'<g style="clip-path:circle(15.2px at 16px 16px) view-box">{body}</g>'
            f'<circle cx="16" cy="16" r="15" fill="none" stroke="#c9a24a" stroke-width="1.2" opacity=".85"/></svg>')


def avatar_data_uri(key: str) -> str:
    return "data:image/svg+xml;utf8," + quote(avatar_svg(key))


def avatar_picker_css(scope: str = '[class*="st-key-avpick_"]') -> str:
    """Põe o retrato de cada personagem nas opções do seletor (st.radio): a ordem das
    opções é sempre ``AVATAR_KEYS``."""
    rules = []
    for i, key in enumerate(AVATAR_KEYS, 1):
        rules.append(f'{scope} [role="radiogroup"] > div:nth-of-type({i}) > label::before'
                     f'{{background-image:url("{avatar_data_uri(key)}");}}')
    return "\n".join(rules)
