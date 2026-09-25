from __future__ import annotations

import argparse
import json
import socket
import struct
from dataclasses import asdict, dataclass

A2S_INFO_REQUEST = b"\xff\xff\xff\xffTSource Engine Query\x00"
DEFAULT_PORT = 27015


class QueryError(RuntimeError):
    pass


@dataclass(frozen=True)
class ServerInfo:
    name: str
    map: str
    folder: str
    game: str
    appid: int
    players: int
    max_players: int
    bots: int
    version: str

    def to_dict(self) -> dict[str, object]:
        return {"online": True, **asdict(self)}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


def parse_address(value: str) -> tuple[str, int]:
    if ":" not in value:
        return value, DEFAULT_PORT
    host, port_text = value.rsplit(":", 1)
    try:
        port = int(port_text)
    except ValueError as exc:
        raise QueryError(f"invalid port in address {value!r}") from exc
    return host, port


def query_a2s_info(host: str, port: int, timeout: float = 3.0) -> ServerInfo:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        address = (host, port)
        sock.sendto(A2S_INFO_REQUEST, address)
        data, _ = sock.recvfrom(4096)
        if data.startswith(b"\xff\xff\xff\xffA"):
            sock.sendto(A2S_INFO_REQUEST + data[5:], address)
            data, _ = sock.recvfrom(4096)
    return parse_a2s_info(data)


def parse_a2s_info(data: bytes) -> ServerInfo:
    if not data.startswith(b"\xff\xff\xff\xffI"):
        raise QueryError(f"unexpected A2S_INFO response prefix: {data[:8].hex()}")
    index = 5
    _protocol = data[index]
    index += 1
    name, index = _read_cstring(data, index)
    map_name, index = _read_cstring(data, index)
    folder, index = _read_cstring(data, index)
    game, index = _read_cstring(data, index)
    appid = struct.unpack_from("<H", data, index)[0]
    index += 2
    players = data[index]
    max_players = data[index + 1]
    bots = data[index + 2]
    index += 3
    index += 4  # server type, environment, visibility, VAC
    version, index = _read_cstring(data, index)
    return ServerInfo(
        name=name,
        map=map_name,
        folder=folder,
        game=game,
        appid=appid,
        players=players,
        max_players=max_players,
        bots=bots,
        version=version,
    )


def _read_cstring(data: bytes, index: int) -> tuple[str, int]:
    try:
        end = data.index(b"\x00", index)
    except ValueError as exc:
        raise QueryError("unterminated string in A2S_INFO response") from exc
    return data[index:end].decode("utf-8", "replace"), end + 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query a CS2 server using A2S_INFO.")
    parser.add_argument("address", help="host[:port], e.g. 192.168.0.8:26001")
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args(argv)
    host, port = parse_address(args.address)
    print(query_a2s_info(host, port, args.timeout).to_json())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QueryError as exc:
        print(json.dumps({"online": False, "error": str(exc)}, sort_keys=True))
        raise SystemExit(1)
