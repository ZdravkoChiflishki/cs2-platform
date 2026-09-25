import json
import struct

from cs2_tools.query_server import parse_a2s_info, ServerInfo, parse_address


def packet(**overrides):
    values = {
        "protocol": 17,
        "name": "ZIZO.GG Staging Multi-CFG",
        "map": "de_mirage",
        "folder": "csgo",
        "game": "Counter-Strike 2",
        "appid": 730,
        "players": 1,
        "max_players": 24,
        "bots": 0,
        "server_type": "d",
        "environment": "l",
        "visibility": 0,
        "vac": 1,
        "version": "1.41.8.4",
    }
    values.update(overrides)
    return (
        b"\xff\xff\xff\xffI"
        + bytes([values["protocol"]])
        + values["name"].encode()
        + b"\x00"
        + values["map"].encode()
        + b"\x00"
        + values["folder"].encode()
        + b"\x00"
        + values["game"].encode()
        + b"\x00"
        + struct.pack("<H", values["appid"])
        + bytes([values["players"], values["max_players"], values["bots"]])
        + values["server_type"].encode()
        + values["environment"].encode()
        + bytes([values["visibility"], values["vac"]])
        + values["version"].encode()
        + b"\x00"
    )


def test_parse_a2s_info_extracts_browser_capacity():
    info = parse_a2s_info(packet())

    assert info == ServerInfo(
        name="ZIZO.GG Staging Multi-CFG",
        map="de_mirage",
        folder="csgo",
        game="Counter-Strike 2",
        appid=730,
        players=1,
        max_players=24,
        bots=0,
        version="1.41.8.4",
    )


def test_server_info_json_has_stable_keys():
    payload = json.loads(parse_a2s_info(packet()).to_json())

    assert payload["online"] is True
    assert payload["players"] == 1
    assert payload["max_players"] == 24
    assert payload["bots"] == 0


def test_parse_address_defaults_and_explicit_ports():
    assert parse_address("192.168.0.8") == ("192.168.0.8", 27015)
    assert parse_address("192.168.0.8:26001") == ("192.168.0.8", 26001)
