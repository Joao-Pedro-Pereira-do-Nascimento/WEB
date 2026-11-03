"""Tema "Uno Folclóuno": nome, ausência de emojis, favicon, logo, ícones, efeitos que
tocam uma vez só, chegada/saída de jogadores e visualização ampliada das cartas."""

import re
import xml.etree.ElementTree as ET

import pytest

from conftest import ROOT
from game import engine as E
from game import rooms as R
from game.cards import card_info
from ui import effects as FX
from ui import icons as I
from ui import render as V
from ui.logo import logo_html, logo_svg
from ui.styles import CSS, ambient_html

# faixas de emoji / pictogramas proibidas em todo o projeto
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\uFE0F\u200D]")
SKIP_DIRS = {".venv", ".git", ".pytest_cache", "__pycache__", ".data", "node_modules"}


def project_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in {".py", ".md", ".toml", ".example", ".txt", ".svg"} \
                and not SKIP_DIRS & set(p.relative_to(ROOT).parts):
            yield p


def test_no_emoji_anywhere_in_project():
    bad = []
    for p in project_files():
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if EMOJI.search(line):
                bad.append(f"{p.relative_to(ROOT)}:{n}")
    assert not bad, f"emoji/pictograma encontrado em: {bad}"


def test_no_emoji_in_generated_html():
    import random

    room, host = R.new_room("ABCDE", "Pantanal")
    R.add_bot(room, host["id"])
    R.start_game(room, host["id"], rng=random.Random(2))
    html = (CSS + ambient_html() + logo_html() + V.bestiary_html() + V.seats_html(room, host["id"], set())
            + V.status_html(room, host["id"]) + V.ranking_html([{"name": "Ana", "wins": 1, "games": 1, "key": "ana"}])
            + V.RULES_MD + FX.portal_html("ABCDE", "k") + FX.arrival_html("Bia", "k") + FX.departure_html("Bia", "k"))
    for etype in FX.FX_PRIORITY:
        html += FX.fx_html({"type": etype, "seq": 1, "player": "a", "target": "b", "color": "red"}, {"a": "A", "b": "B"}, "a")
    assert not EMOJI.search(html)
    assert all(not EMOJI.search(a) for a in R.AVATARS)
    from game.bots import BOT_NAMES
    assert all(not EMOJI.search(n) for n in BOT_NAMES)


def test_new_name_everywhere():
    old = "Folcl" + "órico"  # nome antigo não pode sobrar
    for p in project_files():
        text = p.read_text(encoding="utf-8")
        assert old.lower() not in text.lower(), p
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'page_title="Uno Folclóuno"' in app
    assert (ROOT / "README.md").read_text(encoding="utf-8").startswith("# UNO FOLCLÓUNO")


def test_favicon_svg_and_png_are_valid():
    from PIL import Image

    svg = ROOT / "assets" / "favicon.svg"
    png = ROOT / "assets" / "favicon.png"
    root = ET.fromstring(svg.read_text(encoding="utf-8"))
    assert root.tag.endswith("svg") and root.get("viewBox")
    with Image.open(png) as im:
        assert im.format == "PNG" and im.size[0] == im.size[1] >= 64
    assert 'FAVICON = ROOT / "assets" / "favicon.png"' in (ROOT / "app.py").read_text(encoding="utf-8")


def test_logo_is_valid_xml_and_readable():
    svg = logo_svg()
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    ns = "{http://www.w3.org/2000/svg}"
    assert root.find(f"{ns}title").text == "UNO FOLCLÓUNO"
    for part in ("lg-eye", "lg-saci", "lg-cuca", "lg-curupira", "lg-iara", "lg-mula", "lg-snake"):
        assert part in svg  # criaturas nas letras
    assert "<animate" in svg and "prefers-reduced-motion" in svg
    assert "UNO FOLCLÓUNO" in logo_html()
    assert "Saci · Iara" not in logo_html()  # sem a legenda de nomes


def test_icons_and_avatars_are_valid_svg():
    for name in I.ICONS:
        ET.fromstring(I.icon(name))
    for key in I.AVATAR_KEYS + ["desconhecido"]:
        ET.fromstring(I.avatar_svg(key, "Zé"))
    assert set(R.AVATARS) <= set(I.AVATAR_KEYS)
    css = I.icon_mask_css()
    assert "st-key-add_bot" in css and 'role="tab"' in css and "data:image/svg+xml" in css


def test_habitat_room_name_suggestions():
    assert len(R.HABITATS) == 10 and len(set(R.HABITATS)) == 10
    assert all(not EMOJI.search(h) and R.clean_name(h) == h for h in R.HABITATS)
    assert R.suggest_name() in R.HABITATS


# --------------------------------------------------------------------------- efeitos: uma vez só

def test_fx_push_plays_each_event_only_once():
    store = {}
    assert FX.fx_push(store, "ev:1", "<b>x</b>", now=100.0, seconds=3, sounds=["uno"])
    assert FX.fx_current(store, "fx", 101.0) == "<b>x</b>"
    sfx_id = store["sfx"]["id"]
    # reruns do Streamlit: o mesmo evento não dispara de novo nem reinicia o som
    for t in (101.5, 102.0, 102.5):
        assert not FX.fx_push(store, "ev:1", "<b>x</b>", now=t, sounds=["uno"])
    assert store["sfx"]["id"] == sfx_id
    assert FX.fx_current(store, "fx", 103.5) == ""   # expirou
    assert FX.fx_push(store, "ev:2", "<i>y</i>", now=104.0, sounds=["skip"])
    assert store["sfx"]["id"] > sfx_id
    FX.fx_forget(store, "ev:1")
    assert not FX.fx_seen(store, "ev:1") and FX.fx_seen(store, "ev:2")


def test_sfx_queue_merges_sounds_until_played():
    store = {}
    FX.sfx_queue(store, ["portal"], 1.0)
    FX.sfx_queue(store, ["arrive"], 1.0)
    assert store["sfx"]["names"] == ["portal", "arrive"]
    store["sfx"]["played"] = True
    FX.sfx_queue(store, ["depart"], 1.0)
    assert store["sfx"]["names"] == ["depart"]


def test_roster_diff_detects_join_and_leave():
    room, host = R.new_room("ROSTR", "Ana")
    me = host["id"]
    first = FX.roster(room)
    assert FX.roster_diff(None, first, me) == ([], [])          # primeira visão: nada
    bia = R.join_room(room, "Bia")
    joined, left = FX.roster_diff(first, FX.roster(room), me)
    assert joined == [(bia["id"], "Bia")] and left == []
    prev = FX.roster(room)
    R.leave_room(room, bia["id"])
    joined, left = FX.roster_diff(prev, FX.roster(room), me)
    assert joined == [] and left == [(bia["id"], "Bia")]
    # quem sai no meio da partida vira bot (flag "left"): conta como saída
    p = R.join_room(room, "Caio")
    prev = FX.roster(room)
    R.start_game(room, me)
    R.leave_room(room, p["id"])
    assert FX.roster_diff(prev, FX.roster(room), me)[1] == [(p["id"], "Caio")]


def test_arrival_departure_and_portal_html():
    a = FX.arrival_html("<Bia>", "arrive:X:p1")
    assert "&lt;Bia&gt;" in a and "entrou na sala" in a and "herald-fire" in a
    assert "saiu da sala" in FX.departure_html("Caio", "k")
    portal = FX.portal_html("KXPTZ", "portal:KXPTZ")
    assert portal.count("portal-card") >= 8 and "KXPTZ" in portal


def test_app_plays_arrival_once_per_player(data_dir, monkeypatch):
    from streamlit.testing.v1 import AppTest

    from storage import LocalBackend

    monkeypatch.setattr(R, "BOT_DELAY", 0.0)
    be = LocalBackend(data_dir)
    room, host = R.new_room("ARRIV", "Ana")
    be.create_room("ARRIV", room)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.query_params["room"] = "ARRIV"
    at.query_params["token"] = host["token"]
    at.run()
    html = "".join(m.value for m in at.markdown)
    assert "portal" in html and "herald arrive" not in html      # entrou: portal, sem anúncio
    be.transact("ARRIV", lambda r: R.join_room(r, "Bia"))
    at.run()
    html = "".join(m.value for m in at.markdown)
    assert "herald arrive" in html and "Bia" in html
    seen = list(at.session_state["_fx_seen"])
    at.run()
    assert [k for k in at.session_state["_fx_seen"] if k.startswith("arrive:")] == \
           [k for k in seen if k.startswith("arrive:")]                # não repete
    bia = next(p for p in be.get_room("ARRIV")["players"] if p["name"] == "Bia")
    be.transact("ARRIV", lambda r: R.leave_room(r, bia["id"]))
    at.run()
    assert "herald depart" in "".join(m.value for m in at.markdown)


def test_special_cards_are_alive_and_preview_has_texts():
    skip = {"id": "x", "color": "yellow", "kind": "skip", "value": None}
    html = V.card_html(skip)
    assert "live" in html and "special kind-skip" in html and "fx-cap" in html
    assert 'data-effect="Pular: o próximo jogador perde a vez.' in html
    num = {"id": "y", "color": "red", "kind": "number", "value": 7}
    assert " live" not in V.card_html(num).split(">")[0]
    for c in E.build_deck()[:108:7]:
        info = card_info(c)
        assert info["name"] and info["effect"] and info["blurb"]
    css = CSS
    for cls in (".fx-cap", ".fx-eyeglow", ".fx-ripple", ".fx-shimmer", ".fx-steps", "#uno-pv", "touch-callout"):
        assert cls in css
    doc = FX.sound_script([], 1)
    assert "__unoPreview" in doc and "touchstart" in doc and "contextmenu" in doc and "swallowUntil" in doc


def test_victory_and_defeat_are_different():
    ev = {"type": "game_over", "seq": 9, "player": "a", "points": 30}
    win = FX.fx_html(ev, {"a": "Ana", "b": "Bia"}, "a")
    lose = FX.fx_html(ev, {"a": "Ana", "b": "Bia"}, "b")
    assert "VITÓRIA" in win and "fx-crown" in win
    assert "DERROTA" in lose and "fx-ash" in lose
    assert FX.sounds_for([ev], False, "b") == ["defeat"]
    assert FX.sounds_for([ev], False, "a") == ["fanfare"]


@pytest.mark.parametrize("etype,needle", [("skip", "fx-whirlwind"), ("reverse", "fx-footprints"), ("draw2", "fx-cauldron"),
                                          ("wild4", "fx-flamewall"), ("wild", "fx-waterwave"), ("color", "fx-colorwave"),
                                          ("uno", "fx-shout"), ("denounce", "fx-horn")])
def test_creature_specific_effects(etype, needle):
    ev = {"type": etype, "seq": 3, "player": "a", "target": "b", "color": "green"}
    assert needle in FX.fx_html(ev, {"a": "Ana", "b": "Bia"}, "a")


def test_ranking_html_podium_and_highlight():
    rows = [{"name": "Ana", "key": "ana", "wins": 3, "games": 4}, {"name": "Bia", "key": "bia", "wins": 1, "games": 2},
            {"name": "Caio", "key": "caio", "wins": 0, "games": 1}, {"name": "Duda", "key": "duda", "wins": 0, "games": 1}]
    html = V.ranking_html(rows, me_key="bia", online=True)
    assert "Ranking online" in html and html.count("podium-step") == 3 and 'class="me"' in html
    assert "Ranking local" in V.ranking_html(rows, online=False)
    ET.fromstring("<div>" + html.replace("&", "&amp;").replace("&amp;amp;", "&amp;") + "</div>")
