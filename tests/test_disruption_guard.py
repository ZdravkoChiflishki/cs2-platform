from cs2_tools.disruption_guard import evaluate_disruption_guard, main
from cs2_tools.query_server import ServerInfo


def server_info(players: int, bots: int = 0) -> ServerInfo:
    return ServerInfo(
        name="ZIZO.GG Staging All Weapons DM",
        map="de_mirage",
        folder="csgo",
        game="Counter-Strike 2",
        appid=730,
        players=players,
        max_players=24,
        bots=bots,
        version="1.41.8.4",
    )


def test_disruption_guard_allows_empty_server():
    check = evaluate_disruption_guard(server_info(players=0, bots=0))

    assert check.ok is True
    assert check.human_players == 0
    assert check.detail == "safe: no human players connected"


def test_disruption_guard_blocks_human_players():
    check = evaluate_disruption_guard(server_info(players=3, bots=1))

    assert check.ok is False
    assert check.human_players == 2
    assert check.detail == "blocked: 2 human players connected"


def test_disruption_guard_override_allows_human_players():
    check = evaluate_disruption_guard(server_info(players=2, bots=0), allow_active_players=True)

    assert check.ok is True
    assert check.human_players == 2
    assert check.detail == "override: 2 human players connected"


def test_disruption_guard_main_returns_nonzero_when_players_connected(monkeypatch, capsys):
    monkeypatch.setattr("cs2_tools.disruption_guard.query_a2s_info", lambda host, port, timeout=3.0: server_info(players=1))

    exit_code = main(["--host", "192.168.0.8", "--port", "26001"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert '"ok": false' in output
    assert '"human_players": 1' in output


def test_disruption_guard_main_override_returns_zero_when_players_connected(monkeypatch, capsys):
    monkeypatch.setattr("cs2_tools.disruption_guard.query_a2s_info", lambda host, port, timeout=3.0: server_info(players=1))

    exit_code = main(["--host", "192.168.0.8", "--port", "26001", "--allow-active-players"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"ok": true' in output
    assert '"detail": "override: 1 human players connected"' in output
