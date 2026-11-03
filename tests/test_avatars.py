"""Personagens escolhíveis (avatares): chaves, desenho, escolha ao criar/entrar,
conflito, troca no lobby e compatibilidade com salas antigas."""

import random
import re
import xml.etree.ElementTree as ET

import pytest

from game import avatars as AV
from game import rooms as R
from storage import LocalBackend
from ui import icons as I
from ui.styles import CSS

EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\uFE0F\u200D]")


def test_avatar_keys_are_folklore_characters():
    assert len(AV.KEYS) >= 12 and len(set(AV.KEYS)) == len(AV.KEYS)
    assert R.AVATARS == AV.KEYS == I.AVATAR_KEYS
    for must in ("saci", "curupira", "iara", "cuca", "mula", "boitata", "boto", "caipora", "negrinho",
                 "lobisomem", "mapinguari", "boi_bumba"):
        assert must in AV.KEYS
    for k in AV.KEYS:
        assert re.fullmatch(r"[a-z_]+", k)
        assert AV.short_name(k) and AV.full_name(k) and not EMOJI.search(AV.full_name(k))


@pytest.mark.parametrize("key", AV.KEYS + list(AV.LEGACY) + ["desconhecido", ""])
def test_avatar_svg_is_valid_xml_without_emoji(key):
    for size in (26, 46):
        svg = I.avatar_svg(key, "Zé", size, title=True)
        root = ET.fromstring(svg)
        assert root.tag.endswith("svg") and root.get("width") == str(size)
        assert not EMOJI.search(svg)


def test_picker_css_has_one_portrait_per_option():
    css = I.avatar_picker_css()
    assert css.count("data:image/svg+xml") == len(AV.KEYS)
    assert f"nth-of-type({len(AV.KEYS)})" in css
    assert "st-key-avpick_" in CSS and "prefers-reduced-motion" in CSS


def test_legacy_keys_map_to_characters():
    assert set(AV.LEGACY.values()) <= set(AV.KEYS)
    for old, new in AV.LEGACY.items():
        assert AV.normalize(old) == new
        assert f"av-{new}" in I.avatar_svg(old)
    assert AV.normalize("xyz") is None and "av-x" in I.avatar_svg("xyz", "Ana")


def test_create_and_join_respect_choice():
    room, host = R.new_room("ABCDE", "Ana", avatar="iara")
    assert host["avatar"] == "iara"
    bia = R.join_room(room, "Bia", "cuca")
    assert bia["avatar"] == "cuca"
    bot = R.add_bot(room, host["id"])
    assert bot["avatar"] in AV.KEYS and bot["avatar"] not in {"iara", "cuca"}


def test_join_with_taken_character_gets_a_free_one():
    room, host = R.new_room("ABCDE", "Ana", avatar="saci")
    bia = R.join_room(room, "Bia", "saci")
    assert bia["avatar"] != "saci" and bia["avatar"] in AV.KEYS   # o app compara e avisa
    with pytest.raises(R.RoomError):
        R.join_room(room, "Caio", "nao-existe")


def test_random_default_is_free():
    room, host = R.new_room("ABCDE", "Ana")
    for i in range(5):
        R.join_room(room, f"P{i}")
    keys = [p["avatar"] for p in room["players"]]
    assert len(set(keys)) == len(keys)


def test_swap_in_lobby_conflict_and_locked_after_start():
    room, host = R.new_room("ABCDE", "Ana", avatar="saci")
    bia = R.join_room(room, "Bia", "iara")
    assert R.set_avatar(room, bia["id"], "boto") is True
    assert R.find_player(room, bia["id"])["avatar"] == "boto"
    assert "Bia agora é Boto-cor-de-rosa." in room["lobby_log"]
    assert R.set_avatar(room, bia["id"], "boto") is False          # nada muda
    with pytest.raises(R.RoomError, match="já foi escolhido"):
        R.set_avatar(room, bia["id"], "saci")
    with pytest.raises(R.RoomError):
        R.set_avatar(room, bia["id"], "dragao")
    with pytest.raises(R.RoomError):
        R.set_avatar(room, "p-ninguem", "cuca")
    R.start_game(room, host["id"], rng=random.Random(1))
    with pytest.raises(R.RoomError, match="já começou"):
        R.set_avatar(room, bia["id"], "cuca")


def test_legacy_room_counts_old_keys_as_used():
    room, host = R.new_room("ABCDE", "Ana")
    host["avatar"] = "fogo"                     # sala gravada antes da mudança
    bia = R.join_room(room, "Bia", "boitata")  # fogo == boitatá
    assert bia["avatar"] != "boitata"
    with pytest.raises(R.RoomError):
        R.set_avatar(room, bia["id"], "boitata")
    assert R.set_avatar(room, host["id"], "boitata") is False  # já é o mesmo personagem


def test_swap_is_persisted_and_races_resolve(tmp_path):
    be = LocalBackend(tmp_path / "data")
    room, host = R.new_room("ABCDE", "Ana", avatar="saci")
    bia = R.join_room(room, "Bia", "iara")
    be.create_room("ABCDE", room)
    be.transact("ABCDE", lambda r: R.set_avatar(r, host["id"], "lobisomem"))
    assert R.find_player(be.get_room("ABCDE"), host["id"])["avatar"] == "lobisomem"
    with pytest.raises(R.RoomError, match="já foi escolhido"):  # o segundo a pedir perde
        be.transact("ABCDE", lambda r: R.set_avatar(r, bia["id"], "lobisomem"))
    assert R.find_player(be.get_room("ABCDE"), bia["id"])["avatar"] == "iara"
