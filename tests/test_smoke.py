from cs2_tools.smoke import SmokeCheck, evaluate_server_info, evaluate_logs
from cs2_tools.query_server import ServerInfo


def test_evaluate_server_info_accepts_expected_capacity_and_bots():
    info = ServerInfo(
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

    checks = evaluate_server_info(info, expected_max_players=24, expected_bots=0)

    assert all(check.ok for check in checks)
    assert [check.name for check in checks] == ["a2s_online", "max_players", "bots"]


def test_evaluate_server_info_reports_mismatch():
    info = ServerInfo(
        name="ZIZO.GG Staging Multi-CFG",
        map="de_mirage",
        folder="csgo",
        game="Counter-Strike 2",
        appid=730,
        players=1,
        max_players=20,
        bots=3,
        version="1.41.8.4",
    )

    checks = evaluate_server_info(info, expected_max_players=24, expected_bots=0)

    assert SmokeCheck("max_players", False, "expected 24, got 20") in checks
    assert SmokeCheck("bots", False, "expected 0, got 3") in checks


def test_evaluate_logs_flags_counterstrikesharp_callback_spam():
    logs = """
23:19:51 [EROR] (cssharp:Core) Error invoking callback
System.ArgumentNullException: Schema target points to null. (Parameter 'pointer')
   at MenuManagerAPI.Core.PlayerInfo.OnTick()
"""

    check = evaluate_logs(logs)

    assert check == SmokeCheck(
        "no_fatal_logs",
        False,
        "Error invoking callback, Schema target points to null",
    )
